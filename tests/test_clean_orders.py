import csv
import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from orders.cleaning import clean_orders
from orders.files import read_orders, write_result
from orders.parsing import parse_amount, parse_order_date, parse_positive_integer


ROOT = Path(__file__).resolve().parents[1]


def order(**changes):
    row = dict(zip(
        ("OrderID", "CustomerID", "OrderRegion", "OrderDate", "OrderAmount", "ProductID", "Quantity"),
        ("1", "2", "Yorkshire", "2023-07-01", "150.0", "1001.0", "1.0"),
    ))
    return row | changes


class CleaningTests(unittest.TestCase):
    def test_sample_classification_and_source_preservation(self):
        path = ROOT / "data/customer_orders.csv"
        original = path.read_bytes()
        rows = read_orders(path)
        result = clean_orders(rows)
        self.assertEqual([r.values["OrderID"] for r in result.accepted], [101, 104, 105, 106, 107, 109])
        self.assertEqual([r.values["OrderID"] for r in result.rejected], [102, 103, 108, 110])
        self.assertEqual(result.duplicates, [])
        self.assertEqual(result.accepted[2].values["OrderAmount"], Decimal("100"))
        self.assertEqual(result.rejected[2].values["Quantity"], 3)
        self.assertEqual(result.accepted[1].warnings, ["ProductID:missing"])
        self.assertEqual(rows[4]["OrderAmount"], "One Hundred Pounds")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(result.summary()["input_rows"], 10)

    def test_equivalent_repeat_removed_but_distinct_id_kept(self):
        result = clean_orders([order(), order(OrderID="1.0", OrderAmount="150.00"), order(OrderID="2")])
        self.assertEqual(len(result.accepted), 2)
        self.assertEqual(len(result.duplicates), 1)
        self.assertEqual(result.duplicates[0].reasons, ["duplicate_of_source_row:2"])

    def test_conflicting_id_quarantines_all_versions_in_any_order(self):
        for rows in ([order(), order(OrderAmount="160")], [order(OrderAmount="160"), order()]):
            result = clean_orders(rows)
            self.assertEqual(result.accepted, [])
            self.assertEqual(len(result.rejected), 2)
            self.assertTrue(all("OrderID:conflicting_records" in r.reasons for r in result.rejected))

    def test_invalid_version_cannot_be_hidden_by_valid_version(self):
        result = clean_orders([order(), order(OrderDate="INVALID_DATE")])
        self.assertEqual(len(result.rejected), 2)
        self.assertEqual(result.accepted, [])

    def test_optional_missing_fields_warn_but_invalid_values_reject(self):
        result = clean_orders([order(ProductID="", Quantity=" ")])
        self.assertEqual(len(result.accepted), 1)
        self.assertIsNone(result.accepted[0].values["Quantity"])
        self.assertEqual(len(result.accepted[0].warnings), 2)
        for change in ({"Quantity": "1.5"}, {"ProductID": "unknown"}, {"OrderRegion": ""}):
            self.assertEqual(len(clean_orders([order(**change)]).rejected), 1)

    def test_no_guessing_or_implicit_total_calculation(self):
        for change in ({"OrderAmount": ""}, {"OrderDate": "01/02/2023"}, {"OrderAmount": "about 100"}):
            self.assertEqual(len(clean_orders([order(**change)]).rejected), 1)
        result = clean_orders([order(Quantity="4")])
        self.assertEqual(result.accepted[0].values["OrderAmount"], Decimal("150"))

    def test_numeric_limits_without_rounding(self):
        maximum = "99999999999999999999999999999.999999999"
        self.assertEqual(parse_amount(maximum), Decimal(maximum))
        self.assertEqual(parse_amount("0.1000000000"), Decimal("0.1"))
        self.assertEqual(parse_amount(" One   Hundred Pounds "), Decimal("100"))
        self.assertEqual(parse_positive_integer("9223372036854775807"), 9223372036854775807)
        for value in ("NaN", "Infinity", "-1", "1e29", "0.0000000001"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)
        for value in ("0", "-1", "1.1", "9223372036854775808", "NaN"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_positive_integer(value)

    def test_date_validation(self):
        self.assertEqual(parse_order_date("2024-02-29"), date(2024, 2, 29))
        for value in ("2023-02-29", "20230701", "2023-07-01T10:00:00Z", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_order_date(value)

    def test_outputs_reconcile_and_cannot_overwrite_previous_run(self):
        rows = [order(), order(), order(OrderID="2", OrderAmount="")]
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "run"
            write_result(clean_orders(rows), directory)
            with (directory / "cleaned_orders.csv").open(newline="") as source:
                cleaned = list(csv.DictReader(source))
            self.assertEqual(cleaned[0]["OrderDate"], "2023-07-01")
            self.assertEqual(cleaned[0]["ProductID"], "1001")
            rejected = json.loads((directory / "rejected.jsonl").read_text())
            self.assertEqual(rejected["raw"], rows[2])
            self.assertEqual(rejected["reasons"], ["OrderAmount:missing"])
            report = json.loads((directory / "report.json").read_text())
            self.assertEqual(report["input_rows"], 3)
            self.assertEqual(report["accepted_rows"] + report["rejected_rows"] + report["duplicate_rows"], 3)
            with self.assertRaises(FileExistsError):
                write_result(clean_orders(rows), directory)

    def test_bad_csv_schema_and_short_rows_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            for content in ("OrderID,OrderID\n1,1\n", ",".join(order()) + "\n1,2\n"):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_orders(path)


if __name__ == "__main__":
    unittest.main()
