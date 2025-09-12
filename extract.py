from pathlib import Path
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as pdf_extract_text
from utils import normalize_spaces

# optional dependencies for tables
HAS_CAMELOT, HAS_TABULA = False, False
try:
    import camelot  # type: ignore
    HAS_CAMELOT = True
except Exception:
    pass

try:
    import tabula  # type: ignore
    HAS_TABULA = True
except Exception:
    pass

def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        raw = pdf_extract_text(str(pdf_path))
        return normalize_spaces(raw)
    except Exception:
        return ""

def extract_text_from_xml(xml_path: Path) -> str:
    try:
        content = xml_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(content, "lxml-xml")
        pieces = []
        for tag in ["article-title", "title", "abstract", "body"]:
            for el in soup.find_all(tag):
                pieces.append(el.get_text(separator=" ", strip=True))
        if not pieces:
            pieces.append(soup.get_text(separator=" ", strip=True))
        raw = "\n\n".join([p for p in pieces if p])
        return normalize_spaces(raw)
    except Exception:
        return ""

def extract_tables_text(pdf_path: Path) -> str:
    # Camelot
    if HAS_CAMELOT:
        try:
            chunks = []
            for flavor in ("lattice", "stream"):
                try:
                    tables = camelot.read_pdf(str(pdf_path), pages="all", flavor=flavor)
                    for t in tables:
                        df = t.df
                        chunks.append("\n".join(["\t".join(map(str, row)) for row in df.values]))
                except Exception:
                    continue
            if chunks:
                return normalize_spaces("\n\n".join(chunks))
        except Exception:
            pass
    # Tabula
    if HAS_TABULA:
        try:
            dfs = tabula.read_pdf(str(pdf_path), pages="all", multiple_tables=True)
            chunks = []
            for df in dfs or []:
                try:
                    chunks.append("\n".join(["\t".join(map(str, row)) for row in df.values]))
                except Exception:
                    continue
            if chunks:
                return normalize_spaces("\n\n".join(chunks))
        except Exception:
            pass
    return ""