# Articles Parser

Articles Parser automates the collection and processing of scientific publications. It can search various sources, filter results, download full texts, extract their contents, and save the data for further analysis.

## Workflow

1. Search articles: the parser queries selected scientific databases using user-specified keywords.
2. Initial filtering: titles and abstracts are filtered with user-provided regular expressions.
3. Download: full texts are downloaded.
4. Text extraction: text and tables is extracted from the downloaded files.
5. Secondary filtering: full text is filtered with user-provided regular expressions.

## Usage

1. Create and activate a conda environment:

```bash
conda create -n articles_parser_env python=3.8 -y
conda activate articles_parser_env
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the parser:

```python
from pipeline import run_pipeline

run_pipeline(
    keywords=["radiolysis", "radiolytic stability",  "dose constant", "radiation chemical yield"],
    abstract_filter=True,
    abstract_regex = [
        r"(?i)radiolysis",
        r"(?i)gamma|γ",
        r"(?i)beta|β|electron",
        r"(?i)degradation",
        ],
    fulltext_filter=True,
    fulltext_regex = [
        r'(?i)(?:molecules?|mols?|mol)\s*(?:/|per)\s*100\s*eV',
        r'(?i)(?:μ|µ|u|m|)?mol\s*/\s*J',
        r'(?i)k?(?:Gy|rad)\^?(?:[-\u2212\u2010\u2011\u2012\u2013\u2014\u2015])',
        r'(?i)(?<!\w)G(?:[-\u2212\u2010\u2011\u2012\u2013\u2014\u2015]|\s+)values?',
        r'(?i)(?<!\w)G\s*\([^)]*\)',
        ],
    oa_only=False,
    max_per_source=100000,
    output_directory="./output",
    sources=["OpenAlex", "ScienceDirect", "arXiv", "EuropePMC"],
    verbose=False
)
```

To validate a locally stored PDF without running the full search pipeline:

```python
from pipeline import run_local

run_local(
    pdf_path="/path/to/article.pdf",
    fulltext_filter=True,
    fulltext_regex=[r"(?i)kinematic viscosity", r"(?i)m{2}\s*(?:\^?2|²)\s*(?:/\s*s|\s*s\s*(?:\^?-?1|⁻1|⁻¹))"],
    inventory=False,
    save_text=True,
)
```
