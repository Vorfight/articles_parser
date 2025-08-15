from pathlib import Path
from urllib.parse import quote_plus
from .config import (UNPAYWALL_EMAIL, LOG_PDF_DOI, LOG_XML_DOI, LOG_DOI_NOT_DOWNL)
from .utils import safe_get, is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi
from .utils import safe_request_json
from scidownl import scihub_download

def append_line(path: Path, doi: str):
    with path.open("a", encoding="utf-8") as f:
        f.write((norm_doi(doi) or "") + "\n")

def download_file(url, target_path: Path) -> bool:
    r = safe_get(url, stream=True)
    if not r:
        return False
    try:
        with open(target_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False

def unpaywall_lookup(doi: str) -> str | None:
    if not UNPAYWALL_EMAIL:
        return None
    url = f"https://api.unpaywall.org/v2/{quote_plus(doi)}"
    params = {"email": UNPAYWALL_EMAIL}
    data = safe_request_json(url, params=params)
    if not data:
        return None
    loc = data.get("best_oa_location") or {}
    if isinstance(loc, dict):
        pdf = loc.get("url_for_pdf") or loc.get("url")
        if pdf:
            return pdf
    for loc in data.get("oa_locations", []) or []:
        pdf = loc.get("url_for_pdf") or loc.get("url")
        if pdf:
            return pdf
    return None

def download_via_scihub_stub(doi: str, pdf_path: Path) -> bool:
    try:
        scihub_download(doi, paper_type='doi', out=pdf_path)
        return True
    except Exception:
        return False

def try_download_pdf_with_validation(doi: str, primary_url: str | None) -> bool:
    """Каскад: primary_url -> Unpaywall -> Sci-Hub(stub). Проверяем %PDF- после каждой попытки."""
    pdf_path = Path("data/pdfs") / f"{doi_to_fname(doi)}.pdf"

    # 1) прямой URL
    if primary_url:
        if download_file(primary_url, pdf_path) and is_valid_pdf(pdf_path):
            append_line(LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    # 2) Unpaywall
    up = unpaywall_lookup(doi)
    if up:
        if download_file(up, pdf_path) and is_valid_pdf(pdf_path):
            append_line(LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    # 3) Sci-Hub
    if download_via_scihub_stub(doi, pdf_path) and is_valid_pdf(pdf_path):
        append_line(LOG_PDF_DOI, doi)
        return True
    delete_if_exists(pdf_path)
    append_line(LOG_DOI_NOT_DOWNL, doi)
    return False

def try_download_xml(doi: str, xml_url: str | None) -> bool:
    if not xml_url:
        return False
    xml_path = Path("data/xmls") / f"{doi_to_fname(doi)}.xml"
    ok = download_file(xml_url, xml_path)
    if ok:
        append_line(LOG_XML_DOI, doi)
    return ok