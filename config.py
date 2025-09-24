from pathlib import Path
import os

# Search keywords (set at runtime)
KEY_TERMS: list[str] = []

def set_keywords(keywords: list[str]) -> None:
    """Set search keywords used by search modules."""
    KEY_TERMS[:] = keywords or []

# HTTP / API
REQUESTS_TIMEOUT = 30
RATE_LIMIT_SLEEP = 0.5

# Paths (can be overridden by the user)
DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
XML_DIR = DATA_DIR / "xmls"
TEXT_DIR = DATA_DIR / "texts"

LOG_INVENTORY = DATA_DIR / "inventory.csv"
LOG_PDF_DOI = DATA_DIR / "pdf_doi.txt"
LOG_XML_DOI = DATA_DIR / "xml_doi.txt"
LOG_DOI_NOT_DOWNL = DATA_DIR / "doi_not_downl.txt"

def set_output_dir(path: str | Path) -> None:
    """Adjust all output paths to a new base directory."""
    global DATA_DIR, PDF_DIR, XML_DIR, TEXT_DIR
    global LOG_INVENTORY, LOG_PDF_DOI, LOG_XML_DOI, LOG_DOI_NOT_DOWNL
    DATA_DIR = Path(path)
    PDF_DIR = DATA_DIR / "pdfs"
    XML_DIR = DATA_DIR / "xmls"
    TEXT_DIR = DATA_DIR / "texts"
    LOG_INVENTORY = DATA_DIR / "inventory.csv"
    LOG_PDF_DOI = DATA_DIR / "pdf_doi.txt"
    LOG_XML_DOI = DATA_DIR / "xml_doi.txt"
    LOG_DOI_NOT_DOWNL = DATA_DIR / "doi_not_downl.txt"

# Unpaywall
UNPAYWALL_EMAIL = "vorfight@gmail.com"  # os.environ.get("UNPAYWALL_EMAIL", "").strip()

# Elsevier
ELSEVIER_SEARCH_API_KEY = "7f59af901d2d86f78a1fd60c1bf9426a"  # os.environ.get("ELSEVIER_SEARCH_API_KEY", "").strip()
ELSEVIER_DOWNLOAD_API_KEY = "7f59af901d2d86f78a1fd60c1bf9426a"  # os.environ.get("ELSEVIER_DOWNLOAD_API_KEY", "").strip()
