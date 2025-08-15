import sys
import argparse
from .pipeline import run_pipeline

def main(argv=None):
    parser = argparse.ArgumentParser(description="Gamma radiolysis DB builder")
    parser.add_argument("--max-per-source", type=int, default=200, help="сколько записей запрашивать у каждого источника")
    args = parser.parse_args(argv)
    run_pipeline(max_per_source=args.max_per_source)

if __name__ == "__main__":
    # поддержка jupyter: не передавать лишние аргументы
    if "ipykernel_launcher" in sys.argv[0]:
        main([])
    else:
        main()