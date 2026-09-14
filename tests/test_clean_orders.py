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
        self.assertEqual([r.values["TotalOrderValue"] for r in result.accepted], [
            Decimal("150"), Decimal("1400"), Decimal("100"),
            Decimal("150"), Decimal("100"), Decimal("2910"),
        ])
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

    def test_missing_product_warns_but_quantity_is_required(self):
        result = clean_orders([order(ProductID="")])
        self.assertEqual(len(result.accepted), 1)
        self.assertIsNone(result.accepted[0].values["ProductID"])
        self.assertEqual(result.accepted[0].warnings, ["ProductID:missing"])
        for change in ({"Quantity": " "}, {"Quantity": "1.5"}, {"ProductID": "unknown"}, {"OrderRegion": ""}):
            self.assertEqual(len(clean_orders([order(**change)]).rejected), 1)

    def test_no_guessing_and_explicit_unit_price_calculation(self):
        for change in ({"OrderAmount": ""}, {"OrderDate": "01/02/2023"}, {"OrderAmount": "about 100"}):
            self.assertEqual(len(clean_orders([order(**change)]).rejected), 1)
        result = clean_orders([order(Quantity="4")])
        self.assertEqual(result.accepted[0].values["OrderAmount"], Decimal("150"))
        self.assertEqual(result.accepted[0].values["TotalOrderValue"], Decimal("600"))

    def test_total_precision_and_overflow(self):
        exact = clean_orders([order(OrderAmount="12345678901234567890.123456789", Quantity="3")])
        self.assertEqual(exact.accepted[0].values["TotalOrderValue"], Decimal("37037036703703703670.370370367"))
        overflow = clean_orders([order(OrderAmount="99999999999999999999999999999", Quantity="2")])
        self.assertEqual(overflow.accepted, [])
        self.assertIn("TotalOrderValue:outside_bigquery_numeric", overflow.rejected[0].reasons)
        zero = clean_orders([order(OrderAmount="0", Quantity="3")])
        self.assertEqual(zero.accepted[0].values["TotalOrderValue"], Decimal(0))

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
            write_result(clean_orders(rows), directory, source_name="source.csv")
            with (directory / "cleaned_orders.csv").open(newline="") as source:
                cleaned = list(csv.DictReader(source))
            self.assertEqual(cleaned[0]["OrderDate"], "2023-07-01")
            self.assertEqual(cleaned[0]["ProductID"], "1001")
            self.assertEqual(Decimal(cleaned[0]["TotalOrderValue"]), Decimal("150"))
            schema = json.loads((ROOT / "infra/modules/orders/orders-schema.json").read_text())
            self.assertEqual(list(cleaned[0]), [field["name"] for field in schema])
            rejected = json.loads((directory / "rejected.jsonl").read_text())
            self.assertEqual(rejected["raw"], rows[2])
            self.assertEqual(rejected["reasons"], ["OrderAmount:missing"])
            report = json.loads((directory / "report.json").read_text())
            self.assertEqual(report["input_rows"], 3)
            self.assertEqual(report["accepted_rows"] + report["rejected_rows"] + report["duplicate_rows"], 3)
            request = json.loads((directory / "source_fix_request.json").read_text())
            self.assertEqual(request["status"], "draft_not_sent")
            self.assertEqual(request["source_file"], "source.csv")
            self.assertIsNone(request["source_owner"])
            self.assertEqual(request["affected_records"], [
                {"source_row": 4, "order_id": "2", "reasons": ["OrderAmount:missing"], "warnings": []},
            ])
            self.assertNotIn("raw", request["affected_records"][0])
            with self.assertRaises(FileExistsError):
                write_result(clean_orders(rows), directory)

    def test_bad_csv_schema_and_short_rows_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            for content in ("OrderID,OrderID\n1,1\n", ",".join(order()) + "\n1,2\n"):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_orders(path)

    def test_valid_batch_does_not_request_unnecessary_correction(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "run"
            write_result(clean_orders([order()]), directory)
            request = json.loads((directory / "source_fix_request.json").read_text())
            self.assertEqual(request["status"], "not_required")
            self.assertEqual(request["affected_records"], [])


if __name__ == "__main__":
    unittest.main()
