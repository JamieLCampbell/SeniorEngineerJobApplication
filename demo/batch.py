"""Cloud Run entry point; durable evidence and quarantine go to a restricted bucket."""
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4
from google.cloud import storage, bigquery
from orders.cloud import run_pipeline
from scripts.verify_cloud_sample import verify


def main():
    project = os.environ["PROJECT_ID"]
    bucket = storage.Client(project=project).bucket(os.environ["DEMO_BUCKET"])
    run_id = os.environ.get("CLOUD_RUN_EXECUTION", uuid4().hex)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "orders.csv"
        bucket.blob("inputs/customer_orders.csv").download_to_filename(str(source))
        output = root / "result"
        try:
            evidence = run_pipeline(source, output, project, "europe-west2")
            verify(bigquery.Client(project=project, location="europe-west2"), project, output)
            print(json.dumps({"status": "verified", "execution": run_id, "load_job_id": evidence["load_job_id"]}))
        finally:
            # Only this isolated run directory; no credentials or environment dump.
            if output.exists():
                for item in output.iterdir():
                    bucket.blob(f"runs/{run_id}/{item.name}").upload_from_filename(str(item), if_generation_match=0)

if __name__ == "__main__":
    main()
