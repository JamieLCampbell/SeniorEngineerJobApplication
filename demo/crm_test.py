"""Prepare a deliberate bad/stale export, or verify the last good CRM snapshot."""
import argparse
import json
from pathlib import Path
from google.cloud import bigquery, storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["good", "duplicate", "stale", "verify"])
    parser.add_argument("--label", default="crm")
    args = parser.parse_args()
    project = "data-enginner-job-app"
    if args.action != "verify":
        csv = Path("demo/crm.csv").read_text()
        date = "2026-09-14"
        if args.action == "duplicate":
            csv = csv.replace("2,Tyne & Wear", "1,Tyne & Wear")
        elif args.action == "stale":
            date = "2026-09-13"
            csv = csv.replace("2026-09-14", date)
        bucket = storage.Client(project=project).bucket(project + "-platform-demo")
        bucket.blob("inputs/crm.csv").upload_from_string(csv)
        bucket.blob("inputs/crm_manifest.json").upload_from_string(json.dumps({"expected_rows": 3, "snapshot_date": date}))
        print("Staged", args.action, "export; trigger the manual DAG next")
        return
    client = bigquery.Client(project=project, location="europe-west2")
    job = client.query(f"SELECT * FROM `{project}.platform_demo.crm_current` ORDER BY CustomerID",
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=10*1024*1024))
    rows = [dict(r) for r in job.result(timeout=60)]
    assert [(r["CustomerID"], r["CustomerRegion"], str(r["SnapshotDate"])) for r in rows] == [
        (1, "Yorkshire", "2026-09-14"), (2, "Tyne & Wear", "2026-09-14"), (3, "London", "2026-09-14")], rows
    output = Path("outputs/platform-demo")
    output.mkdir(parents=True, exist_ok=True)
    (output / (args.label + "-snapshot.json")).write_text(json.dumps({"job_id": job.job_id, "rows": rows}, indent=2, default=str))
    print("Last good snapshot verified:", job.job_id)


if __name__ == "__main__":
    main()
