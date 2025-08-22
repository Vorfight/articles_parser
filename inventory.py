# articles_parser/inventory.py
import csv
import os
import pandas as pd
from config import LOG_INVENTORY

COLUMNS = [
    "doi", "title", "source",
    "abstract_available", "gamma_in_ta", "gamma_in_text",
    "pdf_downloaded", "xml_downloaded",
    "dose_const_found", "g_value_found",
    "notes"
]

def load_seen_inventory() -> set[str]:
    seen = set()
    if LOG_INVENTORY.exists():
        try:
            df = pd.read_csv(LOG_INVENTORY)
            for doi in df["doi"].dropna().tolist():
                seen.add(str(doi).strip().lower())
        except Exception:
            pass
    return seen

def ensure_inventory_file():
    """Создаёт CSV с заголовком, если его ещё нет (и сразу синхронизирует на диск)."""
    if not LOG_INVENTORY.exists():
        LOG_INVENTORY.parent.mkdir(parents=True, exist_ok=True)
        with LOG_INVENTORY.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            f.flush()
            os.fsync(f.fileno())

def append_inventory_row(row: dict, flush: bool = True):
    """Добавляет одну строку в CSV. По умолчанию сразу flush/fsync для «живого» прогресса."""
    if not LOG_INVENTORY.exists():
        ensure_inventory_file()
    with LOG_INVENTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writerow({k: row.get(k) for k in COLUMNS})
        if flush:
            f.flush()
            os.fsync(f.fileno())

# Старая пакетная запись (если где-то нужна)
def update_inventory(rows: list[dict]):
    ensure_inventory_file()
    with LOG_INVENTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        for r in rows:
            w.writerow({k: r.get(k) for k in COLUMNS})
        f.flush()
        os.fsync(f.fileno())