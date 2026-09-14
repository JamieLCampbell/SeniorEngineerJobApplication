"""Trigger or inspect the manual demo through Composer's authenticated API."""
import argparse
import json
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["trigger", "status", "discovery"])
    parser.add_argument("run_id", nargs="?", default="demo-valid")
    args = parser.parse_args()
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    root = "https://composer.googleapis.com/v1/projects/data-enginner-job-app/locations/europe-west2/environments/assessment-orchestrator-dev"
    response = session.get(root, timeout=60)
    response.raise_for_status()
    api = response.json()["config"]["airflowUri"] + "/api/v1"
    dag = api + "/dags/assessment_crm"
    if args.action == "discovery":
        response = session.get(api + "/dags", timeout=60)
        response.raise_for_status()
        print([(d["dag_id"], d["has_import_errors"]) for d in response.json()["dags"]])
        response = session.get(api + "/importErrors", timeout=60)
    elif args.action == "trigger":
        response = session.patch(dag, json={"is_paused": False}, timeout=60)
        response.raise_for_status()
        response = session.post(dag + "/dagRuns", json={"dag_run_id": args.run_id}, timeout=60)
    else:
        response = session.get(dag + "/dagRuns/" + args.run_id + "/taskInstances", timeout=60)
    response.raise_for_status()
    result = response.json()
    if args.action == "status":
        result = {"run_id": args.run_id, "tasks": [
            {k: t[k] for k in ["task_id", "state", "start_date", "end_date", "try_number"]}
            for t in result["task_instances"]]}
        output = Path("outputs/platform-demo")
        output.mkdir(parents=True, exist_ok=True)
        (output / (args.run_id + ".json")).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
