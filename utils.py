import re, time, requests
from pathlib import Path
from .config import (DATA_DIR, PDF_DIR, XML_DIR, TEXT_DIR, REQUESTS_TIMEOUT,
                     RATE_LIMIT_SLEEP)

_SPECIAL_SPACES = dict.fromkeys([
    0x00A0,  # NO-BREAK SPACE
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,  # EN/EM и т.п.
    0x2007, 0x2008, 0x2009, 0x200A,                          # figure, punctuation, thin, hair
    0x202F,  # NARROW NO-BREAK SPACE
    0x205F,  # MEDIUM MATHEMATICAL SPACE
    0x3000,  # IDEOGRAPHIC SPACE
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE (BOM)
    0x2060,  # WORD JOINER
    0x180E,  # MONGOLIAN VOWEL SEPARATOR (deprecated space)
], " ")  # map → ordinary space

def normalize_spaces(text: str) -> str:
    """Заменяет NBSP/узкие/zero-width пробелы на обычный пробел, упрощает поведение регулярок."""
    if not text:
        return text
    # заменим спец-пробелы
    t = text.translate(_SPECIAL_SPACES)
    # унифицируем «смех» из пробелов: не трогаем переводы строк
    # (много пробелов подряд -> один)
    t = re.sub(r"[ \t\u000B\u000C\r]+", " ", t)
    return t

def ensure_dirs():
    for d in [DATA_DIR, PDF_DIR, XML_DIR, TEXT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def norm_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    doi = str(raw).strip()
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = doi.replace("doi:", "").replace("DOI:", "").strip()
    return doi.lower() if doi else None

def doi_to_fname(doi: str) -> str:
    clean = norm_doi(doi) or doi  # если это "arxiv:xxx", оставим как есть
    # заменим проблемные символы
    return (clean.replace('/', '_')
                 .replace(':', '_')
                 .replace(' ', '_'))

def safe_request_json(url, params=None, headers=None):
    time.sleep(RATE_LIMIT_SLEEP)
    try:
        r = requests.get(url, params=params, headers=headers, timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(e)
        return None

def safe_get(url, stream=False):
    time.sleep(RATE_LIMIT_SLEEP)
    try:
        r = requests.get(url, timeout=REQUESTS_TIMEOUT, stream=stream, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception:
        return None
    
def is_valid_pdf(file_path: Path) -> bool:
    try:
        with open(file_path, "rb") as f:
            sig = f.read(5)
        return sig == b"%PDF-"
    except Exception:
        return False

def delete_if_exists(path: Path):
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass

def mentions_gamma(text: str, gamma_hints: list[str]) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(h in t for h in gamma_hints)