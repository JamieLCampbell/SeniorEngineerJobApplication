"""Small, manual dev batch: clean locally, upload accepted rows, replace, query."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

import google.auth
from google.auth import impersonated_credentials
from google.cloud import bigquery, storage

from .cleaning import clean_orders
from .files import read_orders, write_result


ROOT = Path(__file__).resolve().parents[1]
MAXIMUM_BYTES_BILLED = 10 * 1024 * 1024


def credentials_for(service_account):
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if service_account:
        credentials = impersonated_credentials.Credentials(
            source_credentials=credentials, target_principal=service_account,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"], lifetime=900,
        )
    return credentials


def upload_accepted(client, bucket_name, csv_path, run_id):
    # New objects only: retries must never overwrite a previous run's evidence.
    blob = client.bucket(bucket_name).blob(f"accepted/{run_id}/cleaned_orders.csv")
    blob.upload_from_filename(str(csv_path), content_type="text/csv", if_generation_match=0, timeout=60)
    return f"gs://{bucket_name}/{blob.name}"


def load_orders(client, uri, table_id, schema, on_submit=None):
    # This input is a complete assessment snapshot. Replacing prevents reruns
    # doubling sales. Incremental production batches would need staging + MERGE.
    config = bigquery.LoadJobConfig(
        schema=schema, source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1,
        autodetect=False, max_bad_records=0, ignore_unknown_values=False,
        create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_uri(uri, table_id, job_config=config, timeout=60)
    if on_submit:
        on_submit(job)
    job.result(timeout=120)
    return job


def run_query(client, sql, on_submit=None):
    preview = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False), timeout=60)
    if preview.total_bytes_processed > MAXIMUM_BYTES_BILLED:
        raise ValueError("Query exceeds the assessment's 10 MiB scan limit")
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        maximum_bytes_billed=MAXIMUM_BYTES_BILLED, use_query_cache=False,
    ), timeout=60)
    if on_submit:
        on_submit(job)
    rows = [dict(row) for row in job.result(timeout=120)]
    return rows, {
        "job_id": job.job_id, "estimated_bytes": preview.total_bytes_processed,
        "bytes_processed": job.total_bytes_processed, "bytes_billed": job.total_bytes_billed,
        "maximum_bytes_billed": MAXIMUM_BYTES_BILLED,
    }


def run_pipeline(input_path, output_dir, project, location, service_account=None):
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Invalid project ID")
    # Deliberately dev-only until promotion and production snapshot rules are agreed.
    bucket_name = f"{project}-orders-dev"
    dataset_id = f"{project}.orders_dev"
    table_id = f"{dataset_id}.cleaned_orders"
    result = clean_orders(read_orders(input_path))
    write_result(result, output_dir, source_name=input_path.name)
    if not result.accepted:
        raise ValueError("No accepted orders; refusing to erase the existing cloud table")
    run_id = uuid4().hex
    evidence = {
        "status": "started", "run_id": run_id, "project": project, "location": location,
        "table": table_id, "service_account": service_account, "counts": result.summary(),
    }
    evidence_path = output_dir / "cloud_run.json"

    def save():
        evidence_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")

    save()
    try:
        credentials = credentials_for(service_account)
        gcs = storage.Client(project=project, credentials=credentials)
        bq = bigquery.Client(project=project, location=location, credentials=credentials)
        # Dataset access is already scoped to the loader. Object-only storage access
        # does not need bucket metadata permissions; location is managed by Terraform.
        if bq.get_dataset(dataset_id).location.lower() != location.lower():
            raise ValueError("Dataset location does not match the requested location")
        schema = [bigquery.SchemaField.from_api_repr(field) for field in json.loads(
            (ROOT / "infra/modules/orders/orders-schema.json").read_text(encoding="utf-8")
        )]
        uri = upload_accepted(gcs, bucket_name, output_dir / "cleaned_orders.csv", run_id)
        evidence.update(status="uploaded", uri=uri)
        save()
        def record_load(job):
            evidence.update(status="load_submitted", load_job_id=job.job_id)
            save()

        job = load_orders(bq, uri, table_id, schema, on_submit=record_load)
        evidence.update(status="loaded", load_job_id=job.job_id, loaded_rows=job.output_rows)
        save()
        if job.output_rows != len(result.accepted):
            raise ValueError("Loaded row count does not match accepted rows")
        evidence["queries"] = {}
        for name in ("customer_rolling_spending", "regional_spending"):
            sql = (ROOT / "sql" / f"{name}.sql").read_text().replace("PROJECT_ID.DATASET_ID", dataset_id)
            def record_query(job):
                evidence["queries"][name] = {"job_id": job.job_id, "status": "submitted"}
                save()

            rows, details = run_query(bq, sql, on_submit=record_query)
            (output_dir / f"{name}.json").write_text(json.dumps(rows, indent=2, default=str) + "\n", encoding="utf-8")
            evidence["queries"][name] = details
            save()
        evidence["status"] = "complete"
        save()
    except Exception:
        evidence["failed_after"] = evidence["status"]
        evidence["status"] = "failed"
        save()
        raise
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="europe-west2")
    parser.add_argument("--impersonate-service-account")
    args = parser.parse_args()
    evidence = run_pipeline(args.input, args.output_dir, args.project, args.location, args.impersonate_service_account)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
