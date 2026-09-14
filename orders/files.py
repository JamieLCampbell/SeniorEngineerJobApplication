"""CSV input and inspectable outputs; field rules live in cleaning/parsing."""

import csv
import json
from decimal import Decimal
from pathlib import Path

from .cleaning import FIELDS, OUTPUT_FIELDS


def read_orders(path: Path) -> list:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Expected the seven assessment columns in their original order")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("A row has a different number of cells from the header")
    return rows


def write_result(result, directory: Path, source_name: str | None = None):
    # One new directory per run: an accidental rerun must not overwrite evidence.
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "cleaned_orders.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows({
            key: format(value, "f") if isinstance(value, Decimal) else value
            for key, value in row.values.items()
        } for row in result.accepted)
    for name, rows in (("rejected", result.rejected), ("duplicates", result.duplicates)):
        with (directory / f"{name}.jsonl").open("w", encoding="utf-8") as output:
            for row in rows:
                output.write(json.dumps({
                    "source_row": row.source_row, "raw": row.raw,
                    "reasons": row.reasons, "warnings": row.warnings,
                }, ensure_ascii=False) + "\n")
    (directory / "report.json").write_text(
        json.dumps(result.summary(), indent=2) + "\n", encoding="utf-8",
    )
    # Prepare an owner handoff, not an email/ticket submission. Raw payloads
    # remain in quarantine; this draft references only the records and issues.
    correction_request = {
        "status": "draft_not_sent" if result.rejected else "not_required",
        "source_file": source_name,
        "run_id": directory.name,
        "source_owner": None,
        "ticket_reference": None,
        "requested_action": "Confirm the issues and provide a corrected export; do not guess missing facts.",
        "quarantine_file": "rejected.jsonl",
        "affected_records": [
            {"source_row": row.source_row, "order_id": row.raw["OrderID"],
             "reasons": row.reasons, "warnings": row.warnings}
            for row in result.rejected
        ],
        "accepted_record_warnings": result.summary()["warnings"],
    }
    (directory / "source_fix_request.json").write_text(
        json.dumps(correction_request, indent=2) + "\n", encoding="utf-8",
    )
