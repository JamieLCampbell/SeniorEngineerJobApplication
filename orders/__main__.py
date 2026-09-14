"""Run with python -m orders INPUT --output-dir NEW_DIRECTORY."""

import argparse
import csv
import json
from pathlib import Path

from .cleaning import clean_orders
from .files import read_orders, write_result


def main():
    parser = argparse.ArgumentParser(description="Clean orders with explicit rejection reasons.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for this run")
    args = parser.parse_args()
    try:
        result = clean_orders(read_orders(args.input))
        write_result(result, args.output_dir)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Cleaning failed: {error}\n")
    print(json.dumps(result.summary(), indent=2))


if __name__ == "__main__":
    main()
