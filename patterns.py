import re

# базовые куски
INV = r'(?:-1|⁻1|\\?-1|\\?⁻1)'

# единицы для dose constant
DOSE_UNITS = rf'(?:k?Gy{INV}|rad{INV}|krad{INV})'
DOSE_UNITS_RE = re.compile(DOSE_UNITS, re.IGNORECASE)

# единицы для G/RCY (в тексте допускаем и отсутствие единиц)
G_UNITS = (
    r'(?:'
    r'(?:molecules?|mols?|mol)\s*/\s*100\s*eV'
    r'|'
    r'(?:μ|µ|u|m|)?mol\s*/\s*J'
    r')'
)
G_UNITS_RE = re.compile(G_UNITS, re.IGNORECASE)

