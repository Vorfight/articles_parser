from pathlib import Path
import config
from utils import safe_get, is_valid_pdf, delete_if_exists, doi_to_fname, norm_doi

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
        md5_req = requests.get(f"https://libgen.bz/json.php?object=e&doi={doi}&fields=md5")
        md5 = find_md5(md5_req.json())
        mirror_url = f"http://libgen.bz/ads.php?md5={md5}&downloadname={doi}"

        resp = requests.get(mirror_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        a = soup.find_all("a", string=lambda s: s and s.strip().upper() == "GET")
        if not a:
            raise ValueError("No GET links found on the mirror page")

        for link in a:
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
            raise ValueError("Could not extract 'key' parameter from any GET link")
        return download_file(resolved_download_link, pdf_path)
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
        if download_via_libgen_stub(title, pdf_path) and is_valid_pdf(pdf_path):
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
