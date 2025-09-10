from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import quote_plus

import config
from utils import safe_request_json, norm_doi

def search_crossref(keywords: list[str], max_records=200):
    base = "https://api.crossref.org/works"
    rows = 100
    results = {}
    pbar = tqdm(total=max_records * len(keywords), desc="Crossref search", unit="rec")
    for kw in keywords:
        cursor = "*"
        collected = 0
        while collected < max_records:
            params = {"query": kw, "rows": rows, "cursor": cursor, "mailto": config.UNPAYWALL_EMAIL or "you@example.com"}
            data = safe_request_json(base, params=params)
            if not data:
                break
            items = data.get("message", {}).get("items", []) or []
            for it in items:
                doi = norm_doi(it.get("DOI"))
                if not doi or doi in results:
                    continue
                title = " ".join(it.get("title") or []) if it.get("title") else ""
                abstr = ""
                if "abstract" in it and isinstance(it["abstract"], str):
                    abstr = BeautifulSoup(it["abstract"], "lxml").get_text(" ", strip=True)

                pdf_url = f"https://api.elsevier.com/content/article/doi/{quote_plus(doi)}?httpAccept=application/pdf&apiKey={config.ELSEVIER_API_KEY}"
                xml_url = f"https://api.elsevier.com/content/article/doi/{quote_plus(doi)}?httpAccept=application/xml&apiKey={config.ELSEVIER_API_KEY}"

                results[doi] = {
                    "source": "crossref",
                    "title": title or "",
                    "abstract": abstr or "",
                    "pdf_url": pdf_url,
                    "xml_url": xml_url,
                    "raw": it
                }
                collected += 1
                pbar.update(1)
                if collected >= max_records:
                    break
            cursor = data.get("message", {}).get("next-cursor")
            if not cursor:
                break
    pbar.close()
    return results
