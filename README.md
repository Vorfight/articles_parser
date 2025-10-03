# Articles Parser

Articles Parser automates the collection and processing of scientific publications. It can search various sources, filter results, download full texts, extract their contents, and save the data for further analysis. The parser is flexible and can gather information on any chemical or physical properties.

## Workflow

1. Search articles: the parser queries selected scientific databases using user-specified parameters.
2. Initial filtering: titles and abstracts are filtered with regular expressions.
3. Download: full texts are downloaded.
4. Text extraction: text is extracted from the downloaded files.
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

```bash
python cli.py --keywords "oil viscosity" "petrol viscosity" \
    --abstract-filter --abstract-regex temperature \
    --fulltext-filter --fulltext-regex "kinematic viscosity" "dynamic viscosity" \
    --oa-only --max-per-source 50 --output-dir ./output \
    --save-text \
    --sources OpenAlex Sciencedirect
```

Add `--no-verbose` to hide detailed per-article output and only keep the search progress bars.
Use `--no-save-text` to skip storing extracted `.txt` files alongside downloaded articles.

Parameters can be combined as needed. The package can also be used as a library:

```python
from pipeline import run_pipeline

run_pipeline(
    keywords=["oil viscosity", "petrol viscosity"],
    abstract_filter=True,
    abstract_regex=["temperature"],
    fulltext_filter=True,
    fulltext_regex=["kinematic viscosity", "dynamic viscosity"],
    oa_only=True,
    max_per_source=50,
    output_directory="./output",
    sources=["OpenAlex", "Sciencedirect"],
    verbose=True,
    save_text=True,
)
```

To validate a locally stored PDF without running the full search pipeline:

```python
from pipeline import run_local

run_local(
    pdf_path="/path/to/article.pdf",
    fulltext_filter=True,
    fulltext_regex=["kinematic viscosity", "mm^2/s"],
    inventory=False,
    save_text=True,
)
```

## Examples

See [`examples/test.ipynb`](examples/test.ipynb) for a sample notebook demonstrating both Python API and CLI usage.
