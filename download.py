from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urljoin, parse_qs
from bs4 import BeautifulSoup
import requests
import time

import config
from utils import is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi


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
    try:
        md5_req = requests.get(
            f"https://libgen.{libgen_domain}/json.php?object=e&doi={doi}&fields=md5",
            timeout=config.REQUESTS_TIMEOUT,
        )
        md5_req.raise_for_status()
        md5 = find_md5(md5_req.json())
        if not md5:
            return False, "LibGen lookup did not return md5"
        mirror_url = f"http://libgen.{libgen_domain}/ads.php?md5={md5}&downloadname={doi}"

        resp = requests.get(
            mirror_url,
            timeout=config.REQUESTS_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

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
        return download_file(resolved_download_link, pdf_path)
    except Exception as e:
        return False, str(e)

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
