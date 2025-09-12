# articles_parser/inventory.py
import csv
import os
import pandas as pd
import config

COLUMNS = [
    "doi", "title", "source", "keyword",
    "abstract_available", "abstract_matched",
    "pdf_downloaded", "xml_downloaded",
    "names_found", "units_found",
    "notes",
]

def load_seen_inventory() -> set[str]:
    seen = set()
    if config.LOG_INVENTORY.exists():
        try:
            df = pd.read_csv(config.LOG_INVENTORY)
            for doi in df["doi"].dropna().tolist():
                seen.add(str(doi).strip().lower())
        except Exception:
            pass
    return seen

def ensure_inventory_file():
    """Create CSV with header if it doesn't exist (fsync immediately)."""
    if not config.LOG_INVENTORY.exists():
        config.LOG_INVENTORY.parent.mkdir(parents=True, exist_ok=True)
        with config.LOG_INVENTORY.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            f.flush()
            os.fsync(f.fileno())

def append_inventory_row(row: dict, flush: bool = True):
    """Append a row to CSV. Flush/fsync by default for real-time progress."""
    if not config.LOG_INVENTORY.exists():
        ensure_inventory_file()
    with config.LOG_INVENTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writerow({k: row.get(k) for k in COLUMNS})
        if flush:
            f.flush()
            os.fsync(f.fileno())

# Legacy batch writing (kept for compatibility)
def update_inventory(rows: list[dict]):
    ensure_inventory_file()
    with config.LOG_INVENTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        for r in rows:
            w.writerow({k: r.get(k) for k in COLUMNS})
        f.flush()
        os.fsync(f.fileno())
