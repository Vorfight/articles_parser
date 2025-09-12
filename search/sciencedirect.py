# articles_parser /search/sciencedirect.py
from tqdm import tqdm
import time
from urllib.parse import quote_plus
import config
from utils import safe_request_json, norm_doi

MAX_RETRIES = 5
RETRY_BASE_DELAY = 5  # sec

def _is_open_access(entry: dict) -> bool:
    """
    ScienceDirect search returns 'openaccess' in entry for OA items (string 'true'/'false' or bool).
    We'll accept truthy values. If field absent -> treat as non-OA.
    """
    val = entry.get("openaccess")
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"true", "1", "yes"}
    return False

def _safe_request_with_retry(url, params):
    """Retry with exponential backoff when the API returns an error."""
    delay = RETRY_BASE_DELAY
    for attempt in range(MAX_RETRIES):
        data = safe_request_json(url, params=params)  # safe_request_json returns None on any error
        if data is None:
            time.sleep(delay)
        else:
            return data
        delay *= 2

    return None

def search_sciencedirect(keywords: list[str], max_records=200, progress_cb=None):
    """
    ScienceDirect Search API:
      - Open Access filtering
      - PDF URL is built via Content API (OA articles)
    """
    results = {}
    if not config.ELSEVIER_API_KEY:
        return results

    base = "https://api.elsevier.com/content/search/sciencedirect"
    count = 25
    pbar = tqdm(total=max_records * len(keywords), desc="ScienceDirect search", unit="rec")
    for kw in keywords:
        query = f'"{kw}"'
        start = 0
        collected = 0
        while collected < max_records:
            params = {
                "query": query,
                "count": count,
                "start": start,
                "apiKey": config.ELSEVIER_API_KEY,
                'httpAccept': 'application/json',
            }

            data = _safe_request_with_retry(base, params=params)
            if not data:
                break

            sr = data.get("search-results", {})
            items = sr.get("entry") or []
            if not items:
                break

            added_this_page = 0
            for it in items:
                if not _is_open_access(it):
                    continue

                doi = norm_doi(it.get("prism:doi"))
                if not doi or doi in results:
                    continue

                title = it.get("dc:title") or ""
                abstract = it.get("dc:description") or ""

                pdf_url = f"https://api.elsevier.com/content/article/doi/{quote_plus(doi)}?httpAccept=application/pdf&apiKey={config.ELSEVIER_API_KEY}"
                xml_url = f"https://api.elsevier.com/content/article/doi/{quote_plus(doi)}?httpAccept=application/xml&apiKey={config.ELSEVIER_API_KEY}"

                results[doi] = {
                    "source": "sciencedirect",
                    "title": title,
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                    "xml_url": xml_url,
                    "raw": it,
                }

                collected += 1
                added_this_page += 1
                pbar.update(1)
                if progress_cb:
                    progress_cb(1)
                if collected >= max_records:
                    break

            if added_this_page == 0 or len(items) < count:
                break

            start += count
    pbar.close()
    return results
