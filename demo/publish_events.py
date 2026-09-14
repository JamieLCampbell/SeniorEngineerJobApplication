"""Publish the bounded fixture through the authenticated Cloud Run collector."""
import argparse
import json
import subprocess
from pathlib import Path
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Collector URL from Terraform output")
    parser.add_argument("--gcloud", default="gcloud")
    args = parser.parse_args()
    url = args.url.rstrip("/") + "/events"
    # Capture the token in memory; never write it into evidence or command output.
    token = subprocess.check_output([args.gcloud, "auth", "print-identity-token"], text=True).strip()
    result = {"unauthenticated_status": requests.post(url, json={}, timeout=60).status_code, "published": []}
    assert result["unauthenticated_status"] == 403
    for event_id, customer, kind, minute in [("demo-view-1", "1", "view", "00"),
            ("demo-view-1", "1", "view", "00"), ("demo-purchase-2", "2", "purchase", "01"),
            ("demo-invalid-3", "3", "invalid", "02")]:
        payload = dict(event_id=event_id, customer_id=customer, event_type=kind,
                       event_time=f"2026-09-14T12:{minute}:00Z")
        response = requests.post(url, json=payload, headers={"Authorization": "Bearer " + token}, timeout=60)
        assert response.status_code == 202, response.status_code
        result["published"].append({"event_id": event_id, "status": response.status_code, "response": response.json()})
    output = Path("outputs/platform-demo")
    output.mkdir(parents=True, exist_ok=True)
    (output / "collector.json").write_text(json.dumps(result, indent=2))
    print("Published four fixture messages; anonymous request denied")


if __name__ == "__main__":
    main()
