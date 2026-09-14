"""Read-only post-teardown checks for this explicitly named synthetic demo."""
import json
from datetime import datetime, timezone
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession


def main():
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    project = "data-enginner-job-app"
    location = f"projects/{project}/locations/europe-west2"
    deleted = {
        "composer": f"https://composer.googleapis.com/v1/{location}/environments/assessment-orchestrator-dev",
        "source_database": f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{project}/instances/assessment-source-dev",
        "datastream": f"https://datastream.googleapis.com/v1/{location}/streams/assessment-orders",
        "cloud_run_job": f"https://run.googleapis.com/v2/{location}/jobs/assessment-orders-cloud",
        "collector": f"https://run.googleapis.com/v2/{location}/services/assessment-collector",
        "topic": f"https://pubsub.googleapis.com/v1/projects/{project}/topics/assessment-demo-events",
        "demo_bucket": f"https://storage.googleapis.com/storage/v1/b/{project}-platform-demo",
        "composer_bucket": "https://storage.googleapis.com/storage/v1/b/europe-west2-assessment-orc-49949e4f-bucket",
        "replication_secret": f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/assessment-cdc-password",
        "images": f"https://artifactregistry.googleapis.com/v1/{location}/repositories/assessment-demo",
        "demo_dataset": f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/datasets/platform_demo",
        "cdc_dataset": f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/datasets/platform_cdc",
        "network": f"https://compute.googleapis.com/compute/v1/projects/{project}/global/networks/assessment-demo",
    }
    evidence = {"checked_at": datetime.now(timezone.utc).isoformat(), "deleted": {}}
    for name, url in deleted.items():
        response = session.get(url, timeout=60)
        assert response.status_code == 404, (name, response.status_code)
        evidence["deleted"][name] = "not_found_404"
    response = session.get(f"https://dataflow.googleapis.com/v1b3/{location}/jobs/2026-09-14_05_29_51-10151398287747062658", timeout=60)
    response.raise_for_status()
    evidence["dataflow_state"] = response.json()["currentState"]
    assert evidence["dataflow_state"] == "JOB_STATE_CANCELLED"
    evidence["retained"] = {}
    for name, url in {
        "orders_bucket": f"https://storage.googleapis.com/storage/v1/b/{project}-orders-dev",
        "state_bucket": f"https://storage.googleapis.com/storage/v1/b/{project}-tfstate-dev",
        "orders_table": f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/datasets/orders_dev/tables/cleaned_orders",
    }.items():
        response = session.get(url, timeout=60)
        response.raise_for_status()
        evidence["retained"][name] = "present"
        if name == "orders_table":
            assert int(response.json()["numRows"]) == 6
            evidence["retained"]["order_rows"] = 6
    output = Path("outputs/platform-demo")
    output.mkdir(parents=True, exist_ok=True)
    (output / "cleanup.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
