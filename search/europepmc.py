from tqdm import tqdm
from ..config import KEY_TERMS
from ..utils import safe_request_json, norm_doi

def search_europe_pmc(max_records=200):
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    clauses = []
    for t in KEY_TERMS:
        tq = f'"{t}"'
        clauses.append(f'TITLE:{tq}')
        clauses.append(f'ABSTRACT:{tq}')
    query = "(" + " OR ".join(clauses) + ")"

    page_size = 100
    cursor_mark = "*"
    collected = 0
    results = {}
    pbar = tqdm(total=max_records, desc="EuropePMC search", unit="rec")
    while collected < max_records:
        params = {"query": query, "format": "json", "pageSize": str(page_size), "cursorMark": cursor_mark}
        data = safe_request_json(base, params=params)
        if not data:
            break
        hits = data.get("resultList", {}).get("result", []) or []
        next_cursor = data.get("nextCursorMark")
        if not hits:
            break
        for item in hits:
            doi = norm_doi(item.get("doi"))
            if not doi or doi in results:
                continue
            title = item.get("title") or ""
            abstr = item.get("abstractText") or ""
            pdf_url, xml_url = None, None
            ft = item.get("fullTextUrlList", {}) or {}
            urls = ft.get("fullTextUrl", []) or []
            for u in urls:
                doc_style = (u.get("documentStyle") or "").lower()
                link = u.get("url")
                if not link:
                    continue
                if "pdf" in doc_style and not pdf_url:
                    pdf_url = link
                if "xml" in doc_style and not xml_url:
                    xml_url = link
            results[doi] = {
                "source": "europepmc",
                "title": title,
                "abstract": abstr,
                "pdf_url": pdf_url,
                "xml_url": xml_url,
                "raw": item
            }
            collected += 1
            pbar.update(1)
            if collected >= max_records:
                break
        if not next_cursor or next_cursor == cursor_mark:
            break
        cursor_mark = next_cursor
    pbar.close()
    return results