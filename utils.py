import re, time, requests
from pathlib import Path
import config

_SPECIAL_SPACES = dict.fromkeys([
    0x00A0,  # NO-BREAK SPACE
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,  # EN/EM etc.
    0x2007, 0x2008, 0x2009, 0x200A,                          # figure, punctuation, thin, hair
    0x202F,  # NARROW NO-BREAK SPACE
    0x205F,  # MEDIUM MATHEMATICAL SPACE
    0x3000,  # IDEOGRAPHIC SPACE
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE (BOM)
    0x2060,  # WORD JOINER
    0x180E,  # MONGOLIAN VOWEL SEPARATOR (deprecated space)
], " ")  # map → ordinary space

def normalize_spaces(text: str) -> str:
    """Replace NBSP/narrow/zero-width spaces with regular spaces to simplify regex behaviour."""
    if not text:
        return text
    # replace special spaces
    t = text.translate(_SPECIAL_SPACES)
    # collapse sequences of spaces while keeping newlines
    # (multiple spaces -> single)
    t = re.sub(r"[ \t\u000B\u000C\r]+", " ", t)
    return t

def ensure_dirs():
    for d in [config.DATA_DIR, config.PDF_DIR, config.XML_DIR, config.TEXT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def norm_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    doi = str(raw).strip()
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = doi.replace("doi:", "").replace("DOI:", "").strip()
    return doi.lower() if doi else None

def doi_to_fname(doi: str) -> str:
    clean = norm_doi(doi) or doi  # if it's "arxiv:xxx", keep as is
    # replace problematic characters
    return (clean.replace('/', '_')
                 .replace(':', '_')
                 .replace(' ', '_'))

def safe_request_json(url, params=None, headers=None):
    time.sleep(config.RATE_LIMIT_SLEEP)
    try:
        r = requests.get(url, params=params, headers=headers, timeout=config.REQUESTS_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(e)
        return None

def safe_get(url, stream=False, headers=None, params=None):
    time.sleep(config.RATE_LIMIT_SLEEP)
    try:
        r = requests.get(
            url,
            timeout=config.REQUESTS_TIMEOUT,
            stream=stream,
            allow_redirects=True,
            headers=headers,
            params=params,
        )
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
