from pathlib import Path
from config import (PDF_DIR, XML_DIR, LOG_PDF_DOI, LOG_XML_DOI, LOG_DOI_NOT_DOWNL)
from utils import safe_get, is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi
from libgen_api_enhanced import LibgenSearch

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

def download_via_libgen_stub(doi: str, pdf_path: Path) -> bool:
    try:
        searcher = LibgenSearch()
        results = searcher.search_default(doi)
        if not results:
            return False
        book = results[0]
        book.resolve_direct_download_link()
        if not book.resolved_download_link:
            return False
        return download_file(book.resolved_download_link, pdf_path)
    except Exception:
        return False

def try_download_pdf_with_validation(doi: str, primary_url: str | None, oa_only: bool = False) -> bool:
    """Cascade: try primary_url, then LibGen (if allowed). Validate PDF signature after each attempt."""
    pdf_path = PDF_DIR / f"{doi_to_fname(doi)}.pdf"

    # 1) прямой URL
    if primary_url:
        if download_file(primary_url, pdf_path) and is_valid_pdf(pdf_path):
            append_line(LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    # 2) LibGen (если разрешено)
    if not oa_only:
        if download_via_libgen_stub(doi, pdf_path) and is_valid_pdf(pdf_path):
            append_line(LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    append_line(LOG_DOI_NOT_DOWNL, doi)
    return False

def try_download_xml(doi: str, xml_url: str | None) -> bool:
    if not xml_url:
        return False
    xml_path = XML_DIR / f"{doi_to_fname(doi)}.xml"
    ok = download_file(xml_url, xml_path)
    if ok:
        append_line(LOG_XML_DOI, doi)
    return ok
