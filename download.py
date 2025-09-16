from pathlib import Path
import config
from utils import safe_get, is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi
from libgen_api_enhanced import LibgenSearch
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

def download_via_libgen_stub(title: str, pdf_path: Path, doi: str | None = None) -> bool:
    """Try LibGen first, fall back to SciHub via scidownl on failure."""
    try:
        searcher = LibgenSearch(mirror="bz")
        results = searcher.search_default(title)
        if results:
            book = results[0]
            try:
                book.resolve_direct_download_link()
            except Exception:
                book.resolved_download_link = None
            if book.resolved_download_link:
                if download_file(book.resolved_download_link, pdf_path):
                    print('libgen')
                    return True
    except Exception:
        pass
    try:
        scihub_download(
            doi or title,
            paper_type='doi' if doi else 'title',
            out=str(pdf_path)
        )
        print('scidownl')
        return pdf_path.exists()
    except Exception:
        return False

def try_download_pdf_with_validation(doi: str, title: str, primary_url: str | None, oa_only: bool = False) -> bool:
    """Cascade: try primary_url, then LibGen (if allowed). Validate PDF signature after each attempt."""
    pdf_path = config.PDF_DIR / f"{doi_to_fname(doi)}.pdf"

    # 1) direct URL
    if primary_url:
        if download_file(primary_url, pdf_path) and is_valid_pdf(pdf_path):
            append_line(config.LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    # 2) LibGen (if allowed)
    if not oa_only:
        if download_via_libgen_stub(title, pdf_path, doi) and is_valid_pdf(pdf_path):
            append_line(config.LOG_PDF_DOI, doi)
            return True
        delete_if_exists(pdf_path)

    append_line(config.LOG_DOI_NOT_DOWNL, doi)
    return False

def try_download_xml(doi: str, xml_url: str | None) -> bool:
    if not xml_url:
        return False
    xml_path = config.XML_DIR / f"{doi_to_fname(doi)}.xml"
    ok = download_file(xml_url, xml_path)
    if ok:
        append_line(config.LOG_XML_DOI, doi)
    return ok
