from __future__ import annotations

from pathlib import Path
import re
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
import logging
for name in ["pdfminer", "camelot", "tabula"]:
    logging.getLogger(name).setLevel(logging.ERROR)

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


def _extract_abstract_from_text(full_text: str) -> str:
    """Best-effort extraction of abstract section from article text."""

    if not full_text:
        return ""

    normalized = full_text.replace("\r\n", "\n")
    match = re.search(r"\babstract\b[:\s]*", normalized, re.IGNORECASE)
    if not match:
        return ""

    remainder = normalized[match.end() :].lstrip(" \t:-\n")
    if not remainder:
        return ""

    # Split by first empty line which commonly separates abstract from next section.
    parts = re.split(r"\n\s*\n", remainder, maxsplit=1)
    abstract_block = parts[0]

    # Stop before common section headings if they accidentally land in the same block.
    stop_match = re.search(
        r"\b(?:keywords?|index\s+terms?|introduction|background|materials?\s+and\s+methods)\b",
        abstract_block,
        re.IGNORECASE,
    )
    if stop_match:
        abstract_block = abstract_block[: stop_match.start()]

    return normalize_spaces(abstract_block.strip())


def _format_check_result(value: bool | str | None) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "not requested"
    return "passed" if value else "failed"


def run_pipeline(
    keywords: list[str],
    abstract_filter: bool = False,
    abstract_regex: list[str] | None = None,
    fulltext_filter: bool = False,
    fulltext_regex: list[str] | None = None,
    oa_only: bool = False,
    max_per_source: int | None = None,
    output_directory: str | Path = "data",
    sources: list[str] | None = None,
    libgen_domain: str | None = "bz",
    verbose: bool = True,
    save_text: bool = True,
): 
    """Execute full pipeline of search, download and filtering."""

    if not keywords:
        raise ValueError("'keywords' must not be empty")

    abstract_res = [re.compile(p) for p in (abstract_regex or [])]
    fulltext_res = [re.compile(p) for p in (fulltext_regex or [])] if fulltext_filter else []

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

    for kw in keywords:
        print(f"\n=== Keyword: {kw} ===", flush=True)
        config.set_keywords([kw])
        searches = [src_funcs[s]([kw], max_records) for s in selected]
        db = _merge_sources(*searches)
        print(f"Total unique records for '{kw}': {len(db)}", flush=True)

        for rec_id, rec in db.items():
            nd = norm_doi(rec_id) or rec_id
            if nd in seen:
                continue

            title = (rec.get("title") or "").replace("\n", " ").replace("\r", " ")
            abstr = rec.get("abstract") or ""
            abstract_available = bool(title) and bool(abstr)

            notes: list[str] = []
            fulltext_matched = None
            pdf_ok = False
            xml_ok = False

            report_lines = [
                f"- DOI: {nd}",
                f"  Source: {rec.get('source', '') or 'unknown'}",
            ]

            abstract_matched = True
            abstract_status = None
            if abstract_filter:
                combined_text = f"{title}\n{abstr}" if abstract_available else ""
                if abstract_available and any(p.search(combined_text) for p in abstract_res):
                    abstract_status = "patterns in abstract"
                else:
                    abstract_matched = False
                    abstract_status = (
                        "patterns not in abstract"
                        if abstract_available
                        else "patterns not in abstract (abstract unavailable)"
                    )
                    notes.append("skip:abstract_filter")
                report_lines.append(f"  Abstract filter: {abstract_status}")

            direct_status: str | None = None
            libgen_status: str | None = None
            fulltext_message: str | None = None

            if abstract_filter and not abstract_matched:
                direct_status = (
                    "not attempted (abstract filter not matched)"
                    if rec.get("pdf_url")
                    else "no direct link provided"
                )
                libgen_status = "not attempted (abstract filter not matched)"
                if fulltext_filter:
                    fulltext_message = "Fulltext filter: not run (abstract filter not matched)"
                row = {
                    "doi": nd,
                    "title": title,
                    "source": rec.get("source", ""),
                    "keyword": kw,
                    "abstract_available": abstract_available,
                    "abstract_matched": False,
                    "pdf_downloaded": False,
                    "xml_downloaded": False,
                    "fulltext_matched": False if fulltext_filter else None,
                    "notes": ",".join(notes),
                }
                append_inventory_row(row)
                seen.add(nd)
                if verbose:
                    report_lines.append(f"  Direct download: {direct_status}")
                    report_lines.append(f"  Libgen download: {libgen_status}")
                    if fulltext_message:
                        report_lines.append(f"  Fulltext filter: {fulltext_message}")
                    print("\n".join(report_lines), flush=True)
                    print(flush=True)
                continue

            pdf_result = try_download_pdf_with_validation(
                rec_id,
                title,
                rec.get("pdf_url"),
                oa_only=oa_only,
                libgen_domain=libgen_domain,
            )
            pdf_ok = pdf_result.success
            direct_status = pdf_result.direct.message or "not attempted"
            libgen_status = pdf_result.libgen.message or "not attempted"

            xml_ok = try_download_xml(rec_id, rec.get("xml_url"))
            if not pdf_ok and not xml_ok:
                notes.append("download_failed")

            if fulltext_filter:
                full_text = ""
                text_path = config.TEXT_DIR / f"{doi_to_fname(rec_id)}.txt"
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
                    if fulltext_res:
                        filter_pass = any(bool(p.search(full_text)) for p in fulltext_res)
                    else:
                        filter_pass = True
                    if save_text:
                        text_path.write_text(full_text, encoding="utf-8", errors="ignore")
                    if filter_pass:
                        fulltext_matched = True
                        if fulltext_res:
                            fulltext_message = "Fulltext filter: patterns matched in text"
                        else:
                            fulltext_message = "Fulltext filter: no patterns provided"
                    else:
                        fulltext_matched = False
                        notes.append("skip:fulltext_filter")
                        fulltext_message = "Fulltext filter: patterns not in text (article removed)"
                        for path in [
                            config.PDF_DIR / f"{doi_to_fname(rec_id)}.pdf",
                            config.XML_DIR / f"{doi_to_fname(rec_id)}.xml",
                        ]:
                            try:
                                path.unlink()
                            except FileNotFoundError:
                                pass
                        if save_text:
                            try:
                                text_path.unlink()
                            except FileNotFoundError:
                                pass
                        pdf_ok = False
                        xml_ok = False
                else:
                    fulltext_matched = False
                    fulltext_message = "Fulltext filter: patterns not in text (no full text available)"
            # no extraction if fulltext_filter is False

            if verbose:
                report_lines.append(f"  Direct download: {direct_status}")
                report_lines.append(f"  Libgen download: {libgen_status}")
                if fulltext_message:
                    report_lines.append(f"  Fulltext filter: {fulltext_message}")

            row = {
                "doi": nd,
                "title": title,
                "source": rec.get("source", ""),
                "keyword": kw,
                "abstract_available": abstract_available,
                "abstract_matched": abstract_matched,
                "pdf_downloaded": pdf_ok,
                "xml_downloaded": xml_ok,
                "fulltext_matched": fulltext_matched,
                "notes": ",".join(notes) if notes else "",
            }
            append_inventory_row(row)
            seen.add(nd)
            if verbose:
                print("\n".join(report_lines), flush=True)
                print(flush=True)
    if verbose:
        print(f"Done. Summary in {config.LOG_INVENTORY}", flush=True)


def run_local(
    pdf_path: str | Path,
    fulltext_filter: bool = False,
    fulltext_regex: list[str] | None = None,
    inventory: bool = False,
    save_text: bool = True,
) -> dict[str, str]:
    """Run full text regex checks for a locally available PDF file."""

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    fulltext_res = [re.compile(p) for p in (fulltext_regex or [])] if fulltext_filter else []

    full_text = extract_text_from_pdf(pdf_path)
    tables_text = extract_tables_text(pdf_path)
    if tables_text:
        full_text += "\n\n" + tables_text
    full_text = normalize_spaces(full_text.strip())

    fulltext_status: bool | str | None = None

    if fulltext_filter:
        if full_text:
            if fulltext_res:
                fulltext_status = all(bool(p.search(full_text)) for p in fulltext_res)
            else:
                fulltext_status = True
        else:
            fulltext_status = False
    fulltext_result = _format_check_result(fulltext_status)
    summary_lines = [f"File: {pdf_path.name}"]
    summary_lines.append(f"Fulltext check: {fulltext_result}")
    output_text = "\n".join(summary_lines)

    if save_text and full_text:
        text_path = pdf_path.with_suffix(".txt")
        text_path.write_text(full_text, encoding="utf-8", errors="ignore")

    if inventory:
        inventory_path = pdf_path.parent / "inventory"
        with inventory_path.open("a", encoding="utf-8") as f:
            f.write(output_text + "\n\n")
    else:
        print(output_text, flush=True)

    return {"fulltext": fulltext_result}
