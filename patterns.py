import re

# базовые куски
NUM = r'(?:\d+(?:[\.,]\d+)?(?:\s*[×x]\s*10\^[-+]?\d+)?|\d+(?:\.\d+)?[eE][-+]?\d+)'
SP  = r'(?:\s|&nbsp;| | | )*'
INV = r'(?:-1|⁻1|\\?-1|\\?⁻1)'

# единицы для dose constant
DOSE_UNITS = rf'(?:k?Gy{INV}|rad{INV}|krad{INV})'

# единицы для G/RCY (в тексте допускаем и отсутствие единиц)
G_UNITS = (
    r'(?:'
    r'(?:molecules?|mols?|mol)\s*/\s*100\s*eV'
    r'|'
    r'(?:μ|µ|u|m|)?mol\s*/\s*J'
    r')'
)

# dose constant и синонимы (k_d/kd/k) + единицы вблизи
DOSE_CONST_NEAR = re.compile(
    rf'\b(?:dose{SP}constant|radiation{SP}dose{SP}constant|k[_\-]?d|kd|\bk\b){SP}[:=]?\s*(?:{NUM})?[^\n]{{0,50}}{DOSE_UNITS}',
    re.IGNORECASE
)

# разрешаем: G-value | RCY | G(-...)=число [+опц.единицы]
G_VALUE_ANY = re.compile(
    rf'(?:\bG{SP}-?{SP}value\b|\bradiation{SP}chemical{SP}yield\b|\bG\s*\(-[^)]+\))'
    rf'{SP}[:=]?\s*{NUM}(?:{SP}(?:{G_UNITS}))?',
    re.IGNORECASE
)