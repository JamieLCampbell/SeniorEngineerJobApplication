"""Row validation and conservative duplicate handling, independent of files/cloud."""

from collections import defaultdict
from dataclasses import dataclass, field

from .calculations import total_order_value

from .parsing import parse_amount, parse_order_date, parse_positive_integer, parse_region


FIELDS = ("OrderID", "CustomerID", "OrderRegion", "OrderDate", "OrderAmount", "ProductID", "Quantity")
OUTPUT_FIELDS = FIELDS + ("TotalOrderValue",)
PARSERS = {
    "OrderID": parse_positive_integer,
    "CustomerID": parse_positive_integer,
    "OrderRegion": parse_region,
    "OrderDate": parse_order_date,
    "OrderAmount": parse_amount,
    "ProductID": parse_positive_integer,
    "Quantity": lambda value: parse_positive_integer(value, {"three": "3"}),
}
OPTIONAL = {"ProductID"}


@dataclass
class Record:
    source_row: int
    raw: dict
    values: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class CleaningResult:
    accepted: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)

    def summary(self):
        return {
            "input_rows": len(self.accepted) + len(self.rejected) + len(self.duplicates),
            "accepted_rows": len(self.accepted),
            "rejected_rows": len(self.rejected),
            "duplicate_rows": len(self.duplicates),
            "warnings": [
                {"source_row": row.source_row, "order_id": row.values["OrderID"], "warnings": row.warnings}
                for row in self.accepted if row.warnings
            ],
        }


def clean_row(raw: dict, source_row: int) -> Record:
    if set(raw) != set(FIELDS) or any(not isinstance(value, str) for value in raw.values()):
        raise ValueError(f"Source row {source_row}: expected exactly seven string fields")
    record = Record(source_row, dict(raw))
    for name, parser in PARSERS.items():
        if name in OPTIONAL and not raw[name].strip():
            record.values[name] = None
            record.warnings.append(f"{name}:missing")
            continue
        try:
            record.values[name] = parser(raw[name])
        except ValueError as error:
            record.values[name] = None
            record.reasons.append(f"{name}:{error}")
    record.values["TotalOrderValue"] = None
    if record.values["OrderAmount"] is not None and record.values["Quantity"] is not None:
        try:
            record.values["TotalOrderValue"] = total_order_value(
                record.values["OrderAmount"], record.values["Quantity"],
            )
        except ValueError as error:
            record.reasons.append(f"TotalOrderValue:{error}")
    return record


def clean_orders(rows) -> CleaningResult:
    """Classify every row exactly once. Input row dictionaries are never mutated.

    One OrderID is assumed to identify one order record. If the source actually
    contains order lines, change the business key before using this policy.
    """
    records = [clean_row(raw, number) for number, raw in enumerate(rows, start=2)]
    groups = defaultdict(list)
    result = CleaningResult()
    for record in records:
        order_id = record.values["OrderID"]
        if order_id is None:
            result.rejected.append(record)
        else:
            groups[order_id].append(record)

    for group in groups.values():
        first = group[0]
        if len(group) > 1 and (any(row.reasons for row in group) or
                              any(row.values != first.values for row in group[1:])):
            # No source update time exists, so neither "first" nor "last" is reliable.
            for row in group:
                row.reasons.append("OrderID:conflicting_records")
                result.rejected.append(row)
        elif first.reasons:
            result.rejected.append(first)
        else:
            result.accepted.append(first)
            for row in group[1:]:
                row.reasons.append(f"duplicate_of_source_row:{first.source_row}")
                result.duplicates.append(row)

    for classified in (result.accepted, result.rejected, result.duplicates):
        classified.sort(key=lambda row: row.source_row)
    return result
