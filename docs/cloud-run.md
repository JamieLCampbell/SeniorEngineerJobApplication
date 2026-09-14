# Running the dev batch in Google Cloud

This guide covers the manual CSV batch using Cloud Storage and BigQuery. The optional [full-platform demonstration](platform-verification.md) also runs the batch in a Cloud Run Job and exercises CDC, clickstream and CRM. Its [separate run guide](../demo/README.md) covers deployment and teardown. Pre/prod roots remain undeployed.

## Setup

Use Python 3.14 (the tested version), an authenticated Google Cloud CLI, and the Terraform setup in [infra/README.md](../infra/README.md). Install the pinned cloud dependencies in a virtual environment; the standalone cleaner still uses only the standard library.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
gcloud auth application-default login
```

The CLI login and application-default login are separate. Terraform uses the developer's application-default credentials. The batch can impersonate the narrower loader identity with short-lived tokens; no service-account key is created. Enable `iamcredentials.googleapis.com` and grant the developer `roles/iam.serviceAccountTokenCreator` on that loader service account only. This identity bootstrap is outside the shared Terraform module. The loader has object access to the data bucket, data editor access to its dataset, and project-level BigQuery job creation; it has no billing-management role.

For the assessment dev deployment, the project is `data-enginner-job-app`, the state bucket is `data-enginner-job-app-tfstate-dev`, and both data resources are in London (`europe-west2`). State was bootstrapped with uniform bucket access, public access prevention and versioning. Keep state, credentials and saved plans out of Git.

## Run and verify

Run these from the repository root. Choose a fresh local output directory each time.

```powershell
.\.venv\Scripts\python.exe -m orders.cloud data/customer_orders.csv --output-dir outputs/cloud-example --project data-enginner-job-app --impersonate-service-account orders-loader-dev@data-enginner-job-app.iam.gserviceaccount.com
.\.venv\Scripts\python.exe -m scripts.verify_cloud_sample outputs/cloud-example --project data-enginner-job-app --impersonate-service-account orders-loader-dev@data-enginner-job-app.iam.gserviceaccount.com
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The verifier is deliberately specific to the supplied ten-row fixture. It checks six exact stored totals, both metric results, and an inline BigQuery fixture for date boundaries, same-day peers, gaps and customer isolation. It also checks exact NUMERIC arithmetic. It creates no additional tables.

## Why these choices?

- Clean locally first. Only `cleaned_orders.csv` is uploaded, under `accepted/<unique-run-id>/`. Rejected rows and the draft source-fix request remain local. Upload uses a generation precondition to prevent overwriting an existing object.
- Load the complete accepted snapshot with `WRITE_TRUNCATE`, an explicit schema, zero tolerated bad records and `CREATE_NEVER`. Terraform owns table creation. Successful reruns replace the same snapshot instead of appending another copy. This is a small assessment snapshot, not a safe incremental ingestion strategy; incremental production data would need staging and a keyed merge.
- An entirely rejected input fails before cloud access, preserving the previous table. Partially accepted batches publish with recorded coverage; six accepted rows are not complete revenue.
- Dry-run each analytical query and enforce a server-side 10 MiB maximum bytes billed. Disable query caching during verification so the evidence records an executed query. This is a per-job control, not an account-wide spending cap, and does not restrict queries launched elsewhere.
- Write load/query job IDs, counts and processed/billed byte statistics to `cloud_run.json`. Query results and the fixture verifier's evidence are separate JSON files. Decimal values are stored as strings in JSON to preserve precision.

A failure after upload may leave an accepted object. A failure after a successful load may leave the new table even if querying fails. A timeout does not guarantee a submitted Google job was cancelled: inspect job history before retrying. This sequential CLI is not a distributed transaction or a production scheduler. Do not run competing snapshots concurrently; the last successful load wins.

## Costs and cleanup

Only dev storage, a small BigQuery table, APIs and IAM are deployed. There are no Composer, Dataflow, Datastream, VM or Cloud Run compute resources in this implementation. London storage can incur charges. Query byte statistics are usage evidence, not a final invoice or a promise of zero charges. Billing reporting can lag.

The data bucket has a seven-day lifecycle and seven-day soft delete. The table and versioned Terraform state do not automatically expire. Keep the live evidence available for review, then remove assessment data and use a reviewed Terraform destroy plan for dev. The private state bucket is outside that plan and needs separate deliberate cleanup after the environment is destroyed and state evidence is retained appropriately. Do not delete the state bucket first. Soft-deleted data may continue to occupy billed storage until its retention expires.

Sources: [upload preconditions](https://docs.cloud.google.com/storage/docs/samples/storage-upload-file), [BigQuery cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs).
