"""Inspect the raw assessment orders without changing or correcting them."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


FIELDS = [
    "OrderID", "CustomerID", "OrderRegion", "OrderDate",
    "OrderAmount", "ProductID", "Quantity",
]


def profile(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != FIELDS:
            raise ValueError("Expected the seven assessment columns in their original order")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("A row has a different number of cells from the header")

    missing = {field: [] for field in FIELDS}
    non_numeric = {field: [] for field in ("OrderAmount", "ProductID", "Quantity")}
    invalid_dates = []
    exact_rows = defaultdict(list)
    order_ids = defaultdict(list)
    similar_orders = defaultdict(list)

    for row_number, row in enumerate(rows, start=2):
        order_id = row["OrderID"]
        order_ids[order_id].append(row_number)
        exact_rows[tuple(row[field] for field in FIELDS)].append(row_number)
        # Similar values are a review hint, not authority to delete another ID.
        similar_orders[tuple(row[field] for field in FIELDS[1:])].append(order_id)
        for field, value in row.items():
            if not value.strip():
                missing[field].append(order_id)
        for field in non_numeric:
            value = row[field].strip()
            if value:
                try:
                    if not Decimal(value).is_finite():
                        raise InvalidOperation
                except InvalidOperation:
                    non_numeric[field].append(order_id)
        if row["OrderDate"].strip():
            try:
                parsed = date.fromisoformat(row["OrderDate"])
                if parsed.isoformat() != row["OrderDate"]:
                    raise ValueError
            except ValueError:
                invalid_dates.append(order_id)

    return {
        "row_count": len(rows),
        "missing_values_by_order_id": {k: v for k, v in missing.items() if v},
        "invalid_iso_dates_by_order_id": invalid_dates,
        "non_numeric_values_by_order_id": {k: v for k, v in non_numeric.items() if v},
        "exact_duplicate_csv_row_groups": [v for v in exact_rows.values() if len(v) > 1],
        "repeated_order_ids_csv_rows": {k: v for k, v in order_ids.items() if len(v) > 1},
        "matching_other_fields_with_different_order_ids": [
            ids for ids in similar_orders.values() if len(set(ids)) > 1
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, nargs="?",
        default=Path(__file__).resolve().parents[1] / "data" / "customer_orders.csv",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(profile(args.input), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not profile orders: {error}\n")
