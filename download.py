from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urljoin, parse_qs
from bs4 import BeautifulSoup
import requests
import time

import config
from utils import is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi

_LIBGEN_MIN_DELAY_SECONDS = 3.1
_LIBGEN_RATE_LIMIT_BACKOFF = 2.0
_LIBGEN_MAX_ATTEMPTS = 5
_LIBGEN_RATE_LIMIT_MAX_DELAY = 60.0

_libgen_last_attempt_completed_at: float | None = None


def _wait_for_libgen_window(delay: float) -> None:
    """Ensure at least ``delay`` seconds have elapsed since the last LibGen attempt."""

    global _libgen_last_attempt_completed_at

    if _libgen_last_attempt_completed_at is None:
        return

    elapsed = time.monotonic() - _libgen_last_attempt_completed_at
    if elapsed < delay:
        time.sleep(delay - elapsed)


def _is_libgen_rate_limit_message(message: str | None) -> bool:
    if not message:
        return False
    return "you have downloaded too much files" in message.lower()


def _next_rate_limit_delay(previous_delay: float) -> float:
    next_delay = max(previous_delay * _LIBGEN_RATE_LIMIT_BACKOFF, previous_delay + _LIBGEN_MIN_DELAY_SECONDS)
    return min(next_delay, _LIBGEN_RATE_LIMIT_MAX_DELAY)


@dataclass
class AttemptOutcome:
    attempted: bool = False
    success: bool = False
    message: str | None = None


@dataclass
class PDFDownloadResult:
    success: bool = False
    direct: AttemptOutcome = field(default_factory=AttemptOutcome)
    libgen: AttemptOutcome = field(default_factory=AttemptOutcome)


def _is_elsevier_content_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return False
    return hostname.endswith("elsevier.com") or hostname.endswith("sciencedirect.com")


def _elsevier_headers(accept: str) -> dict[str, str]:
    headers = {"Accept": accept}
    api_key = config.ELSEVIER_DOWNLOAD_API_KEY or config.ELSEVIER_SEARCH_API_KEY
    if api_key:
        headers["X-ELS-APIKey"] = api_key
    return headers

def append_line(path: Path, doi: str):
    with path.open("a", encoding="utf-8") as f:
        f.write((norm_doi(doi) or "") + "\n")

def _request_with_error(url: str, *, stream: bool, headers: dict[str, str] | None = None):
    time.sleep(config.RATE_LIMIT_SLEEP)
    try:
        response = requests.get(
            url,
            timeout=config.REQUESTS_TIMEOUT,
            stream=stream,
            allow_redirects=True,
            headers=headers,
        )
        response.raise_for_status()
        return response, None
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        reason = e.response.reason if e.response is not None else ""
        message = f"HTTP {status}{f' {reason}' if reason else ''}".strip()
        if e.response is not None:
            try:
                body_text = (e.response.text or "").strip()
            except Exception:
                body_text = ""
            if body_text:
                first_line = body_text.splitlines()[0]
                message = f"{message}: {first_line}"
        return None, message
    except Exception as e:
        return None, str(e)


def download_file(
    url: str, target_path: Path, headers: dict[str, str] | None = None
) -> tuple[bool, str | None]:
    response, error = _request_with_error(url, stream=True, headers=headers)
    if not response:
        return False, error
    try:
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        response.close()

def find_md5(data: dict):
    if isinstance(data, dict):
        for k, v in data.items():
            if k == "md5":
                return v
            result = find_md5(v)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_md5(item)
            if result is not None:
                return result
    return None

def download_via_libgen_stub(
    doi: str, pdf_path: Path, libgen_domain: str
) -> tuple[bool, str | None]:
    global _libgen_last_attempt_completed_at

    delay = _LIBGEN_MIN_DELAY_SECONDS
    last_error: str | None = None

    for _ in range(_LIBGEN_MAX_ATTEMPTS):
        _wait_for_libgen_window(delay)
        try:
            response, error = _request_with_error(
                f"https://libgen.{libgen_domain}/json.php?object=e&doi={doi}&fields=md5",
                stream=False,
            )
            if not response:
                if _is_libgen_rate_limit_message(error):
                    last_error = error
                    delay = _next_rate_limit_delay(delay)
                    continue
                return False, error or "LibGen lookup failed"

            try:
                try:
                    lookup_data = response.json()
                except Exception as json_error:
                    return False, f"Failed to parse LibGen lookup response: {json_error}"
                md5 = find_md5(lookup_data)
            finally:
                response.close()

            if not md5:
                return False, "LibGen lookup did not return md5"

            mirror_url = f"http://libgen.{libgen_domain}/ads.php?md5={md5}&downloadname={doi}"

            response, error = _request_with_error(
                mirror_url,
                stream=False,
            )
            if not response:
                if _is_libgen_rate_limit_message(error):
                    last_error = error
                    delay = _next_rate_limit_delay(delay)
                    continue
                return False, error or "LibGen mirror request failed"

            try:
                soup = BeautifulSoup(response.text, "html.parser")
            finally:
                response.close()

            links = soup.find_all("a", string=lambda s: s and s.strip().upper() == "GET")
            if not links:
                return False, "No GET links found on the mirror page"

            resolved_download_link = None
            for link in links:
                href = link.get("href")
                if not href:
                    continue
                full_url = urljoin(mirror_url, href)
                params = parse_qs(urlparse(full_url).query)
                key_vals = params.get("key")
                if key_vals and key_vals[0]:
                    key = key_vals[0]
                    cdn_base = "https://cdn4.booksdl.lc/get.php"
                    resolved_download_link = f"{cdn_base}?md5={md5}&key={key}"
                    break
            if not resolved_download_link:
                return False, "Could not extract 'key' parameter from any GET link"

            success, download_error = download_file(resolved_download_link, pdf_path)
            if success:
                return True, download_error

            if _is_libgen_rate_limit_message(download_error):
                last_error = download_error
                delay = _next_rate_limit_delay(delay)
                continue

            return False, download_error or "libgen download failed"
        finally:
            _libgen_last_attempt_completed_at = time.monotonic()

    return False, last_error or "libgen download failed"

def try_download_pdf_with_validation(
    doi: str,
    title: str,
    primary_url: str | None,
    oa_only: bool = False,
    libgen_domain: str = "bz",
) -> PDFDownloadResult:
    """Cascade: try primary_url, then LibGen (if allowed). Validate PDF signature after each attempt."""
    result = PDFDownloadResult()
    pdf_path = config.PDF_DIR / f"{doi_to_fname(doi)}.pdf"

    if primary_url:
        result.direct.attempted = True
        headers = (
            _elsevier_headers("application/pdf")
            if _is_elsevier_content_url(primary_url)
            else None
        )
        direct_ok, direct_error = download_file(primary_url, pdf_path, headers=headers)
        if direct_ok:
            if is_valid_pdf(pdf_path):
                append_line(config.LOG_PDF_DOI, doi)
                result.success = True
                result.direct.success = True
                result.direct.message = "downloaded from direct link"
                result.libgen.message = "libgen download not attempted (direct download succeeded)"
                return result
            delete_if_exists(pdf_path)
            result.direct.message = "is_valid_pdf returned False"
        else:
            delete_if_exists(pdf_path)
            result.direct.message = direct_error or "direct download failed"
    else:
        result.direct.message = "no direct link provided"

    if oa_only:
        result.libgen.message = "libgen download skipped (oa_only=True)"
    else:
        result.libgen.attempted = True
        libgen_ok, libgen_error = download_via_libgen_stub(doi, pdf_path, libgen_domain)
        if libgen_ok:
            if is_valid_pdf(pdf_path):
                append_line(config.LOG_PDF_DOI, doi)
                result.success = True
                result.libgen.success = True
                result.libgen.message = "downloaded from libgen"
                if result.direct.message is None:
                    result.direct.message = "direct download not attempted"
                return result
            delete_if_exists(pdf_path)
            result.libgen.message = "is_valid_pdf returned False"
        else:
            delete_if_exists(pdf_path)
            result.libgen.message = libgen_error or "libgen download failed"

    append_line(config.LOG_DOI_NOT_DOWNL, doi)
    if result.direct.message is None:
        result.direct.message = "direct download not attempted"
    if result.libgen.message is None:
        result.libgen.message = "libgen download failed"
    return result

def try_download_xml(doi: str, xml_url: str | None) -> bool:
    if not xml_url:
        return False
    xml_path = config.XML_DIR / f"{doi_to_fname(doi)}.xml"
    headers = _elsevier_headers("application/xml") if _is_elsevier_content_url(xml_url) else None
    ok, _ = download_file(xml_url, xml_path, headers=headers)
    if ok:
        append_line(config.LOG_XML_DOI, doi)
    else:
        delete_if_exists(xml_path)
    return ok
