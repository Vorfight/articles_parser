import sys
import argparse
from pipeline import run_pipeline


def main(argv=None):
    parser = argparse.ArgumentParser(description="Universal articles parser")
    parser.add_argument("--keywords", nargs="+", required=True, help="search keywords")
    parser.add_argument("--abstract-filter", action="store_true", help="enable abstract filtering")
    parser.add_argument("--abstract-patterns", nargs="*", default=[], help="patterns that must appear in abstract")
    parser.add_argument(
        "--property-filter",
        choices=["names", "units", "names_units"],
        default=None,
        help="filter full texts by property names/units",
    )
    parser.add_argument("--property-names", nargs="*", default=[], help="property name synonyms")
    parser.add_argument("--property-units", nargs="*", default=[], help="property units")
    parser.add_argument("--oa-only", action="store_true", help="only download open access articles")
    parser.add_argument("--max-per-source", type=int, default=None, help="limit of records per source")
    parser.add_argument("--output-dir", default="data", help="directory for output data")
    parser.add_argument(
        "--sources",
        nargs="*",
        default=[],
        help="list of sources to search (e.g. OpenAlex Sciencedirect)",
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=True,
        help="enable detailed per-article output",
    )
    parser.add_argument(
        "--no-verbose",
        dest="verbose",
        action="store_false",
        help="disable detailed per-article output",
    )
    parser.add_argument(
        "--save-text",
        dest="save_text",
        action="store_true",
        default=True,
        help="store extracted text files for downloaded articles",
    )
    parser.add_argument(
        "--no-save-text",
        dest="save_text",
        action="store_false",
        help="do not store extracted text files for downloaded articles",
    )
    args = parser.parse_args(argv)

    run_pipeline(
        keywords=args.keywords,
        abstract_filter=args.abstract_filter,
        abstract_patterns=args.abstract_patterns,
        property_names_units_filter=args.property_filter,
        property_names=args.property_names,
        property_units=args.property_units,
        oa_only=args.oa_only,
        max_per_source=args.max_per_source,
        output_directory=args.output_dir,
        sources=args.sources or None,
        verbose=args.verbose,
        save_text=args.save_text,
    )


if __name__ == "__main__":
    if "ipykernel_launcher" in sys.argv[0]:
        main([])
    else:
        main()

