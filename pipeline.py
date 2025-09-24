from __future__ import annotations

from pathlib import Path
import re
from tqdm import tqdm

import config
from utils import ensure_dirs, norm_doi, doi_to_fname, normalize_spaces
from search import (
    search_openalex,
    search_europe_pmc,
    search_arxiv,
    search_sciencedirect,
    search_crossref,
)
from download import try_download_pdf_with_validation, try_download_xml
from extract import extract_text_from_pdf, extract_text_from_xml, extract_tables_text
from inventory import load_seen_inventory, ensure_inventory_file, append_inventory_row


def _merge_sources(*dicts) -> dict[str, dict]:
    db: dict[str, dict] = {}
    for d in dicts:
        for rec_id, rec in d.items():
            if rec_id not in db:
                db[rec_id] = rec
            else:
                for k in ["pdf_url", "xml_url"]:
                    if not db[rec_id].get(k) and rec.get(k):
                        db[rec_id][k] = rec[k]
    return db


def run_pipeline(
    keywords: list[str],
    abstract_filter: bool = False,
    abstract_patterns: list[str] | None = None,
    property_names_units_filter: str | None = None,
    property_names: list[str] | None = None,
    property_units: list[str] | None = None,
    oa_only: bool = False,
    max_per_source: int | None = None,
    output_directory: str | Path = "data",
    sources: list[str] | None = None,
    libgen_domain: str | None = "bz"
):
    """Execute full pipeline of search, download and filtering."""

    # Configure paths and inventory
    config.set_output_dir(output_directory)
    ensure_dirs()
    ensure_inventory_file()

    max_records = max_per_source if max_per_source is not None else 1_000_000

    # --- search by sources ---
    src_funcs = {
        "openalex": search_openalex,
        "europepmc": search_europe_pmc,
        "crossref": search_crossref,
        "arxiv": search_arxiv,
        "sciencedirect": search_sciencedirect,
    }
    selected = [s.lower() for s in (sources or src_funcs.keys()) if s.lower() in src_funcs]

    seen = load_seen_inventory()

    abstract_res = [re.compile(p, re.IGNORECASE) for p in (abstract_patterns or [])]
    names_re = (
        re.compile("|".join(map(re.escape, property_names)), re.IGNORECASE)
        if property_names
        else None
    )
    units_re = (
        re.compile("|".join(map(re.escape, property_units)), re.IGNORECASE)
        if property_units
        else None
    )

    for kw in keywords:
        print(f"\n=== Keyword: {kw} ===")
        config.set_keywords([kw])
        searches = [src_funcs[s]([kw], max_records) for s in selected]
        db = _merge_sources(*searches)
        print(f"Total unique records for '{kw}': {len(db)}")

        for rec_id, rec in db.items():
            nd = norm_doi(rec_id) or rec_id
            if nd in seen:
                continue

            title = (rec.get("title") or "").replace("\n", " ").replace("\r", " ")
            abstr = rec.get("abstract") or ""
            abstract_available = bool(title) and bool(abstr)

            notes: list[str] = []
            abstract_matched = not abstract_filter
            pdf_ok = False
            xml_ok = False
            names_found = False
            units_found = False

            if abstract_filter:
                if abstract_available and all(p.search(title + "\n" + abstr) for p in abstract_res):
                    abstract_matched = True
                else:
                    notes.append("skip:abstract_filter")
                    row = {
                        "doi": nd,
                        "title": title,
                        "source": rec.get("source", ""),
                        "keyword": kw,
                        "abstract_available": abstract_available,
                        "abstract_matched": False,
                        "pdf_downloaded": False,
                        "xml_downloaded": False,
                        "names_found": False,
                        "units_found": False,
                        "notes": ",".join(notes),
                    }
                    append_inventory_row(row)
                    seen.add(nd)
                    continue

            pdf_ok = try_download_pdf_with_validation(rec_id, title, rec.get("pdf_url"), oa_only=oa_only, libgen_domain=libgen_domain)
            xml_ok = try_download_xml(rec_id, rec.get("xml_url"))
            if not pdf_ok and not xml_ok:
                notes.append("download_failed")

            full_text = ""
            if property_names_units_filter is not None:
                if pdf_ok:
                    pdf_path = config.PDF_DIR / f"{doi_to_fname(rec_id)}.pdf"
                    full_text += extract_text_from_pdf(pdf_path)
                    tt = extract_tables_text(pdf_path)
                    if tt:
                        full_text += "\n\n" + tt
                if xml_ok:
                    xml_path = config.XML_DIR / f"{doi_to_fname(rec_id)}.xml"
                    full_text += "\n\n" + extract_text_from_xml(xml_path)

                full_text = normalize_spaces(full_text.strip())
                if full_text:
                    names_found = bool(names_re.search(full_text)) if names_re else False
                    units_found = bool(units_re.search(full_text)) if units_re else False
                    if property_names_units_filter == "names":
                        filter_pass = names_found
                    elif property_names_units_filter == "units":
                        filter_pass = units_found
                    elif property_names_units_filter == "names_units":
                        filter_pass = names_found and units_found
                    else:
                        filter_pass = True
                    (config.TEXT_DIR / f"{doi_to_fname(rec_id)}.txt").write_text(
                        full_text, encoding="utf-8", errors="ignore"
                    )
                    if not filter_pass:
                        notes.append("skip:fulltext_filter")
            # no extraction if property_names_units_filter is None

            row = {
                "doi": nd,
                "title": title,
                "source": rec.get("source", ""),
                "keyword": kw,
                "abstract_available": abstract_available,
                "abstract_matched": abstract_matched,
                "pdf_downloaded": pdf_ok,
                "xml_downloaded": xml_ok,
                "names_found": names_found,
                "units_found": units_found,
                "notes": ",".join(notes) if notes else "",
            }
            append_inventory_row(row)
            seen.add(nd)
    print(f"Done. Summary in {config.LOG_INVENTORY}")

