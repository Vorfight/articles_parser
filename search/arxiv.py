import math
from xml.etree import ElementTree as ET
from urllib.parse import urlencode
from tqdm import tqdm
from utils import safe_get, norm_doi

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

def _parse_entry(entry_el):
    title = (entry_el.findtext("atom:title", namespaces=NS) or "").strip()
    abstract = (entry_el.findtext("atom:summary", namespaces=NS) or "").strip()
    arxiv_id = (entry_el.findtext("atom:id", namespaces=NS) or "").strip().rsplit("/", 1)[-1]
    doi_el = entry_el.find("arxiv:doi", namespaces=NS)
    doi = norm_doi(doi_el.text) if doi_el is not None and doi_el.text else None
    pdf_url = None
    for link in entry_el.findall("atom:link", namespaces=NS):
        if (link.get("type") == "application/pdf") or (link.get("title") == "pdf"):
            pdf_url = link.get("href")
            break
    rec_id = doi or (f"arxiv:{arxiv_id}" if arxiv_id else None)
    if not rec_id:
        return None
    return rec_id, {
        "source": "arxiv",
        "title": title,
        "abstract": abstract,
        "pdf_url": pdf_url,
        "xml_url": None,
        "raw": {"arxiv_id": arxiv_id, "doi": doi},
    }

def search_arxiv(keywords: list[str], max_records=200):
    base = "https://export.arxiv.org/api/query"
    per_page = 100
    pages = math.ceil(max_records / per_page)
    results = {}
    pbar = tqdm(total=pages * len(keywords), desc="arXiv search pages", unit="page")
    for kw in keywords:
        clauses = [f"ti:\"{kw}\"", f"abs:\"{kw}\""]
        query = "(" + " OR ".join(clauses) + ")"
        for i in range(pages):
            start = i * per_page
            size = min(per_page, max_records - start)
            if size <= 0:
                break
            params = {
                "search_query": query,
                "start": start,
                "max_results": size,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            r = safe_get(f"{base}?{urlencode(params)}", stream=False)
            if not r:
                break
            try:
                root = ET.fromstring(r.text)
            except Exception:
                break
            for entry in root.findall("atom:entry", namespaces=NS):
                parsed = _parse_entry(entry)
                if not parsed:
                    continue
                rec_id, rec = parsed
                if rec_id in results:
                    continue
                results[rec_id] = rec
            pbar.update(1)
    pbar.close()
    return results
