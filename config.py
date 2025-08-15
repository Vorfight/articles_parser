from pathlib import Path
import os

# Ключевые термины поиска
KEY_TERMS = [
    "radiolysis",
    "dose constant",
    "G-value",
    "radiation chemical yield",
    "radiolytic stability",
    "radiolytic degradation",
]

# Подсказки про гамма
GAMMA_HINTS = [
    "gamma", "γ", "gamma-ray", "gamma radiation", "gamma irradiation",
    "co-60", "cobalt-60", "cs-137", "cesium-137", "cobalt 60",
    "caesium-137", "60co", "137cs"
]

# HTTP / API
REQUESTS_TIMEOUT = 30
RATE_LIMIT_SLEEP = 0.5
#HEADERS = {"User-Agent": "gamma-radiolysis-db-builder/3.1"}

# Пути
DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
XML_DIR = DATA_DIR / "xmls"
TEXT_DIR = DATA_DIR / "texts"

LOG_INVENTORY = DATA_DIR / "inventory.csv"
LOG_PDF_DOI = DATA_DIR / "pdf_doi.txt"
LOG_XML_DOI = DATA_DIR / "xml_doi.txt"
LOG_DOI_NOT_DOWNL = DATA_DIR / "doi_not_downl.txt"

# Unpaywall
UNPAYWALL_EMAIL = "vorfight@gmail.com" #os.environ.get("UNPAYWALL_EMAIL", "").strip()
ELSEVIER_API_KEY = "7f59af901d2d86f78a1fd60c1bf9426a" #os.environ.get("ELSEVIER_API_KEY", "").strip()