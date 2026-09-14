"""Assert the four-message demo across Dataflow, BigQuery and the raw archive."""
import io
import json
from collections import Counter
from pathlib import Path
from fastavro import reader
from google.cloud import bigquery, storage


def main():
    project = "data-enginner-job-app"
    client = bigquery.Client(project=project, location="europe-west2")
    evidence = {}
    for table, fields in [("events", "*"), ("events_curated", "*"),
                          ("rejected_events", "timestamp, payloadString, errorMessage")]:
        job = client.query(f"SELECT {fields} FROM `{project}.platform_demo.{table}`",
                           job_config=bigquery.QueryJobConfig(maximum_bytes_billed=20*1024*1024))
        evidence[table] = {"job_id": job.job_id, "rows": [dict(r) for r in job.result(timeout=60)]}
    assert Counter(r["event_id"] for r in evidence["events"]["rows"]) == {
        "demo-view-1": 2, "demo-purchase-2": 1}
    assert {r["event_id"] for r in evidence["events_curated"]["rows"]} == {
        "demo-view-1", "demo-purchase-2"}
    bad = evidence["rejected_events"]["rows"]
    assert len(bad) == 1 and "unsupported:event_type" in bad[0]["errorMessage"]
    assert json.loads(bad[0]["payloadString"])["event_id"] == "demo-invalid-3"
    evidence["archive"] = []
    for blob in storage.Client(project=project).list_blobs(project+"-platform-demo", prefix="events/"):
        for record in reader(io.BytesIO(blob.download_as_bytes())):
            evidence["archive"].append({"object": blob.name, "payload": json.loads(record["data"])})
    assert Counter(r["payload"]["event_id"] for r in evidence["archive"]) == {
        "demo-view-1": 2, "demo-purchase-2": 1, "demo-invalid-3": 1}
    output = Path("outputs/platform-demo")
    output.mkdir(parents=True, exist_ok=True)
    (output / "stream-verification.json").write_text(json.dumps(evidence, indent=2, default=str))
    print("Verified: 3 accepted raw rows, 2 unique events, 1 rejection, 4 archived messages")


if __name__ == "__main__":
    main()
