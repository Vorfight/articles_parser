from pathlib import Path
from tqdm import tqdm

from config import (KEY_TERMS, GAMMA_HINTS, PDF_DIR, XML_DIR, TEXT_DIR)
from utils import ensure_dirs, norm_doi, doi_to_fname, mentions_gamma, normalize_spaces
from search import (
    search_openalex, search_europe_pmc,
    search_arxiv, search_sciencedirect, search_crossref,
)
from download import try_download_pdf_with_validation, try_download_xml
from extract import extract_text_from_pdf, extract_text_from_xml, extract_tables_text
from inventory import load_seen_inventory, ensure_inventory_file, append_inventory_row
from patterns import DOSE_CONST_NEAR, G_VALUE_ANY

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

def run_pipeline(max_per_source=200):
    ensure_dirs()
    ensure_inventory_file()  # ← файл и заголовок появятся сразу

    # --- ПОСЛЕДОВАТЕЛЬНЫЙ ПОИСК ---
    openalex = search_openalex(max_per_source)
    europepmc = search_europe_pmc(max_per_source)
    crossref = search_crossref(max_per_source)
    arxiv = search_arxiv(max_per_source)
    scidir = search_sciencedirect(max_per_source)

    db = _merge_sources(openalex, europepmc, crossref, arxiv, scidir)
    print(f"Всего уникальных записей: {len(db)}")

    seen = load_seen_inventory()

    for rec_id, rec in db.items():
        nd = norm_doi(rec_id) or rec_id  # допускаем "arxiv:xxxx"
        if nd in seen:
            continue

        title = rec.get("title") or ""
        abstr = rec.get("abstract") or ""
        abstract_available = bool(title) and bool(abstr)

        gamma_in_ta = False
        gamma_in_text = False
        pdf_ok = False
        xml_ok = False
        dose_const_found = False
        g_value_found = False
        notes = []

        # — решение о скачивании —
        if abstract_available:
            gamma_in_ta = mentions_gamma(title + "\n" + abstr, GAMMA_HINTS)
            if not gamma_in_ta:
                notes.append("skip:no_gamma_in_title_abstract")
            else:
                pdf_ok = try_download_pdf_with_validation(rec_id, rec.get("pdf_url"))
                xml_ok = try_download_xml(rec_id, rec.get("xml_url"))
                if not pdf_ok and not xml_ok:
                    notes.append("download_failed")
        else:
            pdf_ok = try_download_pdf_with_validation(rec_id, rec.get("pdf_url"))
            xml_ok = try_download_xml(rec_id, rec.get("xml_url"))
            if not pdf_ok and not xml_ok:
                notes.append("download_failed")

        # — извлечение/поиск —
        full_text = ""
        if pdf_ok:
            pdf_path = PDF_DIR / f"{doi_to_fname(rec_id)}.pdf"
            full_text += extract_text_from_pdf(pdf_path)
            tt = extract_tables_text(pdf_path)
            if tt:
                full_text += "\n\n" + tt
        if xml_ok:
            xml_path = XML_DIR / f"{doi_to_fname(rec_id)}.xml"
            full_text += "\n\n" + extract_text_from_xml(xml_path)

        full_text = normalize_spaces(full_text.strip())
        if full_text:
            if not abstract_available:
                gamma_in_text = mentions_gamma(full_text, GAMMA_HINTS)
            gamma_flag = gamma_in_ta or gamma_in_text
            if gamma_flag:
                if DOSE_CONST_NEAR.search(full_text):
                    dose_const_found = True
                if G_VALUE_ANY.search(full_text):
                    g_value_found = True
            (TEXT_DIR / f"{doi_to_fname(rec_id)}.txt").write_text(full_text, encoding="utf-8", errors="ignore")

        # — пишем строку СРАЗУ —
        row = {
            "doi": nd,
            "title": title,
            "source": rec.get("source", ""),
            "abstract_available": abstract_available,
            "gamma_in_ta": gamma_in_ta,
            "gamma_in_text": gamma_in_text,
            "pdf_downloaded": pdf_ok,
            "xml_downloaded": xml_ok,
            "dose_const_found": dose_const_found,
            "g_value_found": g_value_found,
            "notes": ",".join(notes) if notes else ""
        }
        append_inventory_row(row)  # ← моментальный лог прогресса

    print("Готово. Сводка в data/inventory.csv")