"""Explicit live acceptance checks for the supplied fixture, not arbitrary inputs."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from google.cloud import bigquery

from orders.cloud import ROOT, credentials_for, run_query


def verify(client, project, run_directory):
    manifest = json.loads((run_directory / "cloud_run.json").read_text())
    if manifest["status"] != "complete" or manifest["project"] != project:
        raise ValueError("Expected a completed cloud run for this project")
    query_evidence = {}

    def check_query(name, sql):
        rows, details = run_query(client, sql)
        query_evidence[name] = details
        return rows

    rows = check_query("stored_orders", f"SELECT OrderID, TotalOrderValue FROM `{project}.orders_dev.cleaned_orders` ORDER BY OrderID")
    expected = [(101, Decimal("150")), (104, Decimal("1400")), (105, Decimal("100")),
                (106, Decimal("150")), (107, Decimal("100")), (109, Decimal("2910"))]
    if [(r["OrderID"], r["TotalOrderValue"]) for r in rows] != expected:
        raise AssertionError("Stored sample orders/totals differ from expected values")
    region = json.loads((run_directory / "regional_spending.json").read_text())
    if [(r["OrderRegion"], r["AcceptedOrderCount"], Decimal(r["AverageOrderValue"])) for r in region] != [
        ("London", 2, Decimal("2155")), ("Yorkshire", 2, Decimal("150")), ("Tyne & Wear", 2, Decimal("100")),
    ]:
        raise AssertionError("Unexpected regional averages")
    rolling = json.loads((run_directory / "customer_rolling_spending.json").read_text())
    if [(r["OrderID"], r["OrdersInWindow"], Decimal(r["AverageOrderValue30Days"])) for r in rolling] != [
        (101, 2, Decimal("150")), (106, 2, Decimal("150")),
        (105, 2, Decimal("100")), (107, 2, Decimal("100")),
        (104, 2, Decimal("2155")), (109, 2, Decimal("2155")),
    ]:
        raise AssertionError("Unexpected sample rolling averages")

    # An inline fixture exercises real BigQuery RANGE semantics without creating
    # extra cloud tables or replacing the assessment data.
    fixture = """(
        SELECT 1 AS OrderID, 1 AS CustomerID, DATE '2023-01-01' AS OrderDate, NUMERIC '100' AS TotalOrderValue
        UNION ALL SELECT 2, 1, DATE '2023-01-02', NUMERIC '20'
        UNION ALL SELECT 3, 1, DATE '2023-01-30', NUMERIC '30'
        UNION ALL SELECT 4, 1, DATE '2023-01-30', NUMERIC '50'
        UNION ALL SELECT 5, 1, DATE '2023-01-31', NUMERIC '100'
        UNION ALL SELECT 6, 2, DATE '2023-01-30', NUMERIC '999'
        UNION ALL SELECT 7, 1, DATE '2023-03-15', NUMERIC '70'
    )"""
    sql = (ROOT / "sql/customer_rolling_spending.sql").read_text().replace(
        "`PROJECT_ID.DATASET_ID.cleaned_orders`", fixture,
    )
    boundary = check_query("calendar_boundary", sql)
    actual = [(r["OrderID"], r["OrdersInWindow"], r["AverageOrderValue30Days"]) for r in boundary]
    expected = [(1, 1, 100), (2, 2, 60), (3, 4, 50), (4, 4, 50), (5, 4, 50), (7, 1, 70), (6, 1, 999)]
    if actual != expected:
        raise AssertionError("BigQuery calendar boundary, same-day peers or customer isolation failed")
    precision = check_query("numeric_precision", "SELECT NUMERIC '12345678901234567890.123456789' * 3 AS total")
    if precision[0]["total"] != Decimal("37037036703703703670.370370367"):
        raise AssertionError("Unexpected BigQuery NUMERIC result")
    evidence = {"status": "passed", "checks": ["six exact stored totals", "regional averages and counts",
                "sample rolling averages", "calendar boundary, peers, gaps and customer isolation", "NUMERIC precision"],
                "queries": query_evidence}
    (run_directory / "cloud_verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="europe-west2")
    parser.add_argument("--impersonate-service-account", required=True)
    args = parser.parse_args()
    client = bigquery.Client(project=args.project, location=args.location,
                            credentials=credentials_for(args.impersonate_service_account))
    print(json.dumps(verify(client, args.project, args.run_directory), indent=2))
