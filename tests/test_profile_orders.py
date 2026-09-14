import csv
import tempfile
import unittest
from pathlib import Path

from scripts.profile_orders import FIELDS, profile


class ProfileOrdersTests(unittest.TestCase):
    def test_sample_findings_without_changing_input(self):
        path = Path(__file__).resolve().parents[1] / "data/customer_orders.csv"
        original = path.read_bytes()
        result = profile(path)
        self.assertEqual(result["row_count"], 10)
        self.assertEqual(result["missing_values_by_order_id"], {
            "OrderAmount": ["102", "110"], "ProductID": ["104", "109"],
            "Quantity": ["103"],
        })
        self.assertEqual(result["invalid_iso_dates_by_order_id"], ["103", "108"])
        self.assertEqual(result["non_numeric_values_by_order_id"], {
            "OrderAmount": ["105", "107"], "Quantity": ["108"],
        })
        self.assertEqual(result["exact_duplicate_csv_row_groups"], [])
        self.assertEqual(result["repeated_order_ids_csv_rows"], {})
        self.assertEqual(result["matching_other_fields_with_different_order_ids"], [
            ["101", "106"], ["105", "107"],
        ])
        self.assertEqual(path.read_bytes(), original)

    def test_exact_duplicate_and_conflicting_id_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "orders.csv"
            row = ["1", "8", "London", "2023-07-01", "10", "1001", "1"]
            with path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(FIELDS)
                writer.writerows([row, row, row[:4] + ["20"] + row[5:]])
            result = profile(path)
            self.assertEqual(result["exact_duplicate_csv_row_groups"], [[2, 3]])
            self.assertEqual(result["repeated_order_ids_csv_rows"], {"1": [2, 3, 4]})
            self.assertEqual(result["matching_other_fields_with_different_order_ids"], [])

    def test_truncated_record_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "orders.csv"
            path.write_text(",".join(FIELDS) + "\n1,8,London\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "number of cells"):
                profile(path)


if __name__ == "__main__":
    unittest.main()
