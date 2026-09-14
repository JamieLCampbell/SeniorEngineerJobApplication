"""Verify initial backfill or insert/update/delete against exact source fixtures."""
import argparse
import json
from decimal import Decimal
from pathlib import Path
from google.cloud import bigquery


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["initial", "changed"])
    args = parser.parse_args()
    client = bigquery.Client(project="data-enginner-job-app", location="europe-west2")
    job = client.query("SELECT order_id, customer_id, unit_price, quantity FROM "
        "`data-enginner-job-app.platform_cdc.public_orders` ORDER BY order_id",
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=50*1024*1024))
    rows = [dict(r) for r in job.result(timeout=60)]
    expected = [(201, 1, Decimal("150"), 1), (202, 2, Decimal("100"), 2), (203, 3, Decimal("350"), 4)]
    if args.phase == "changed":
        expected = [(201, 1, Decimal("175"), 1), (203, 3, Decimal("350"), 4), (204, 2, Decimal("50"), 3)]
    actual = [(r["order_id"], r["customer_id"], Decimal(str(r["unit_price"])), r["quantity"]) for r in rows]
    assert actual == expected, actual
    output = Path("outputs/platform-demo")
    output.mkdir(parents=True, exist_ok=True)
    (output / ("cdc-" + args.phase + ".json")).write_text(json.dumps({"job_id": job.job_id, "rows": rows}, indent=2, default=str))
    print("CDC", args.phase, "verified:", job.job_id)


if __name__ == "__main__":
    main()
