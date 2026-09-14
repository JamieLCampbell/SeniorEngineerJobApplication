"""Run the actual SQL locally: SQLite RANGE/AVG plus a UNIX_DATE compatibility UDF.

This checks query semantics on small fixtures, not BigQuery NUMERIC arithmetic,
permissions or cloud execution. Exact monetary multiplication is tested in Python.
"""

import sqlite3
import unittest
from datetime import date
from pathlib import Path

from orders.cleaning import clean_orders
from orders.files import read_orders


ROOT = Path(__file__).resolve().parents[1]


class SpendingSQLTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.create_function("UNIX_DATE", 1, lambda value: (date.fromisoformat(value) - date(1970, 1, 1)).days)
        self.db.execute('CREATE TABLE `PROJECT_ID.DATASET_ID.cleaned_orders` '
                        '(OrderID INTEGER, CustomerID INTEGER, OrderRegion TEXT, OrderDate TEXT, TotalOrderValue REAL)')

    def insert(self, rows):
        self.db.executemany('INSERT INTO `PROJECT_ID.DATASET_ID.cleaned_orders` VALUES (?, ?, ?, ?, ?)', rows)

    def query(self, filename):
        return [dict(row) for row in self.db.execute((ROOT / "sql" / filename).read_text())]

    def test_calendar_boundary_same_day_peers_and_customer_isolation(self):
        # Deliberately unordered: Jan 1 is included on Jan 30, excluded on Jan 31.
        self.insert([
            (5, 1, "Yorkshire", "2023-01-31", 100),
            (4, 1, "Yorkshire", "2023-01-30", 50),
            (1, 1, "Yorkshire", "2023-01-01", 100),
            (6, 2, "London", "2023-01-30", 999),
            (2, 1, "Yorkshire", "2023-01-02", 20),
            (3, 1, "Yorkshire", "2023-01-30", 30),
            (7, 1, "Yorkshire", "2023-03-15", 70),
        ])
        result = self.query("customer_rolling_spending.sql")
        by_id = {row["OrderID"]: row for row in result}
        for order_id in (3, 4):
            self.assertEqual(by_id[order_id]["OrdersInWindow"], 4)
            self.assertEqual(by_id[order_id]["AverageOrderValue30Days"], 50)
        self.assertEqual(by_id[5]["OrdersInWindow"], 4)
        self.assertEqual(by_id[5]["AverageOrderValue30Days"], 50)
        self.assertEqual(by_id[6]["AverageOrderValue30Days"], 999)
        self.assertEqual(by_id[7]["OrdersInWindow"], 1)
        self.assertEqual(by_id[7]["AverageOrderValue30Days"], 70)
        self.assertEqual([r["OrderID"] for r in result], [1, 2, 3, 4, 5, 7, 6])

    def test_region_average_is_order_weighted_with_deterministic_ties(self):
        self.insert([
            (1, 1, "Yorkshire", "2023-01-01", 10),
            (2, 1, "Yorkshire", "2023-01-01", 20),
            (3, 2, "Yorkshire", "2023-01-01", 90),
            (4, 3, "London", "2023-01-01", 40),
            (5, 3, "Tyne & Wear", "2023-01-01", 100),
        ])
        result = self.query("regional_spending.sql")
        self.assertEqual([r["OrderRegion"] for r in result], ["Tyne & Wear", "London", "Yorkshire"])
        self.assertEqual(result[2]["AcceptedOrderCount"], 3)
        self.assertEqual(result[2]["AverageOrderValue"], 40)

    def test_cleaned_sample_results(self):
        cleaned = clean_orders(read_orders(ROOT / "data/customer_orders.csv"))
        self.insert([
            (r.values["OrderID"], r.values["CustomerID"], r.values["OrderRegion"],
             r.values["OrderDate"].isoformat(), float(r.values["TotalOrderValue"]))
            for r in cleaned.accepted
        ])
        result = self.query("regional_spending.sql")
        self.assertEqual([(r["OrderRegion"], r["AverageOrderValue"]) for r in result], [
            ("London", 2155), ("Yorkshire", 150), ("Tyne & Wear", 100),
        ])
        self.assertEqual(len(self.query("customer_rolling_spending.sql")), 6)

    def test_empty_input_has_no_metrics(self):
        self.assertEqual(self.query("regional_spending.sql"), [])
        self.assertEqual(self.query("customer_rolling_spending.sql"), [])


if __name__ == "__main__":
    unittest.main()
