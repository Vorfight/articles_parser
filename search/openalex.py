from tqdm import tqdm
from bs4 import BeautifulSoup
from config import KEY_TERMS
from utils import safe_request_json, norm_doi

def _restore_openalex_abstract(inv_idx: dict | None) -> str:
    if not inv_idx:
        return ""
    try:
        max_pos = max(pos for positions in inv_idx.values() for pos in positions)
        arr = [""] * (max_pos + 1)
        for term, positions in inv_idx.items():
            for pos in positions:
                if 0 <= pos < len(arr):
                    arr[pos] = term
        return " ".join(arr)
    except Exception:
        return ""

def search_openalex(max_records=200):
    base = "https://api.openalex.org/works"
    results = {}
    cursor = "*"
    per_page = 200
    collected = 0
    search_query = " OR ".join([f'"{t}"' for t in KEY_TERMS])
    params = {"search": search_query, "per_page": per_page, "cursor": cursor}

    pbar = tqdm(total=max_records, desc="OpenAlex search", unit="rec")
    while collected < max_records:
        params["cursor"] = cursor
        data = safe_request_json(base, params=params)
        if not data or "results" not in data:
            break
        for item in data["results"]:
            doi = norm_doi(item.get("doi") or (item.get("ids") or {}).get("doi"))
            if not doi or doi in results:
                continue
            title = item.get("title") or ""
            abstr = _restore_openalex_abstract(item.get("abstract_inverted_index"))

            pdf_url = None
            xml_url = None
            for key in ["primary_location", "best_oa_location"]:
                loc = item.get(key) or {}
                if isinstance(loc, dict):
                    pdf_url = pdf_url or loc.get("pdf_url")

            results[doi] = {
                "source": "openalex",
                "title": title,
                "abstract": abstr or "",
                "pdf_url": pdf_url,
                "xml_url": xml_url,
                "raw": item
            }
            collected += 1
            pbar.update(1)
            if collected >= max_records:
                break
        meta = data.get("meta") or {}
        cursor = meta.get("next_cursor")
        if not cursor:
            break
    pbar.close()
    return results