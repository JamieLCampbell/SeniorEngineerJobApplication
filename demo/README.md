# Full platform demonstration

This optional extension is separate from the submitted Part 2 batch. It deploys synthetic sources to exercise the proposed routes, then removes the continuously billed resources. Do not deploy it as an always-on personal environment.

## Components and limits

- Cloud Run Job executes the Python orders pipeline using the existing dev loader identity. Inputs come from Cloud Storage; reports, rejected records and source-fix drafts are persisted in the restricted demo bucket before the container exits.
- An authenticated Cloud Run service publishes small JSON requests to Pub/Sub. One private-IP Dataflow worker runs Google's pinned Pub/Sub-to-BigQuery template with a small validation UDF. Invalid events go to a separate BigQuery table. An independent Cloud Storage subscription archives events.
- A small Cloud SQL PostgreSQL 15 instance supplies actual changes to Datastream. Connections require encryption and only Datastream's regional IPs are allowlisted. The replication password is stored in Secret Manager, not Terraform or Git.
- Composer 3 runs a manual CRM DAG: check export completeness, load staging, validate, publish. It has one active DAG run, no schedule and no task retries for this bounded demonstration. Invalid snapshots must leave the last valid snapshot available.
- The existing `orders_dev` resources are reused only by the batch demonstration. Temporary resources use `platform_demo` / `platform_cdc` datasets, their own Terraform state prefix and a dedicated bucket.

The collector limits request size and acknowledges only after publishing. It does not make producer retries exactly once. The event ID must remain stable across retries; curated event queries deduplicate by ID for this synthetic contract. Conflicting events under the same ID and production deduplication horizons need explicit rules.

The fixture scripts and SQL deliberately target `data-enginner-job-app` in London. To reuse this example in another project, change those project references as well as the Terraform variables. This is an assessment demonstration, not a general deployment framework. `source_changes.sql` and the four-message publisher are intended to run once against a fresh demo.

## Reproduction order

1. Enable the APIs used by the extension in the chosen dev project. Create Pub/Sub's service identity before the archive subscription IAM grants. Use the existing private state bucket with the `platform-demo/dev` prefix; never reuse the base dev state prefix.
2. Copy the example variables, select a currently supported Composer 3 image and discover Datastream's regional static IPs. Review `terraform plan` for `infra/platform-demo`. This starts a paid database and Composer environment when applied.
3. Build `demo/Dockerfile` through `demo/cloudbuild.yaml` using the builder account. `.gcloudignore` restricts uploaded source. Set the immutable resulting image digest in `infra/platform-run/terraform.tfvars` and initialise that root with the same state bucket. Its distinct `platform-demo/run` state allows container deployment after the image exists without coupling it to slow Composer provisioning. Review and apply its plan.
4. Upload the synthetic input CSVs, CRM manifest and event UDF. Run `python -m demo.bootstrap_source`, then import its password-free `source/setup.sql` into the `shop` database as postgres. Wait for success, then import `source/slot.sql` as datastream. These must be separate successful transactions: a failed SQL import rolls back its earlier grants. Grant the Datastream service agent secret-version access on the replication secret. Enable `cdc_ready` in the core root only after replication setup completes, then review and apply the three-resource Datastream plan.
5. Launch the pinned Dataflow template with one `e2-standard-2` worker, the demo subnetwork, private worker IPs, the processing subscription, accepted/rejected tables and `transform` UDF. Its runtime job ID is recorded separately from Terraform.
6. Upload `demo/dags/assessment_crm.py` to the Composer DAG directory and wait for DAG discovery. Run the Cloud Run Job and the manual DAG, which also invokes the orders job after a valid CRM publication. Send synthetic valid and invalid click events, and modify the source database to verify CDC insert/update/delete handling.
7. Preserve execution IDs, query results, archives and negative-test evidence before teardown. Final verification status is recorded separately; source code alone is not evidence that a cloud test passed.

## Commands used for the main checks

After configuring each root's ignored `backend.hcl` and variables, initialise, review and apply its saved plan. PowerShell needs the `=` arguments quoted:

```powershell
terraform '-chdir=infra/platform-demo' init '-backend-config=backend.hcl'
terraform '-chdir=infra/platform-demo' plan '-out=demo.tfplan'
terraform '-chdir=infra/platform-demo' apply demo.tfplan
# Repeat init/plan/apply for infra/platform-run after building its image.
```

Enable `run`, `artifactregistry`, `cloudbuild`, `dataflow`, `pubsub`, `composer`, `sqladmin`, `datastream`, `secretmanager`, and `compute` APIs in addition to the base batch APIs. The operator needs permission to provision these resources; runtime accounts have separate roles. The Composer-to-Run completion role has only `run.operations.get`, expires at `status_access_expires`, and is removed at teardown. Job metadata access is scoped to the one job. Set the expiry to the planned end of your demonstration before applying.

```powershell
gcloud builds submit . --project=data-enginner-job-app --region=europe-west2 --config=demo/cloudbuild.yaml --gcs-source-staging-dir=gs://data-enginner-job-app-platform-demo/build-source --service-account=projects/data-enginner-job-app/serviceAccounts/demo-builder@data-enginner-job-app.iam.gserviceaccount.com
gcloud storage cp data/customer_orders.csv gs://data-enginner-job-app-platform-demo/inputs/customer_orders.csv
gcloud storage cp demo/event_transform.js gs://data-enginner-job-app-platform-demo/code/event_transform.js
python -m demo.crm_test good
python -m demo.bootstrap_source
# Wait for the printed user operation to finish, then import setup.sql successfully,
# followed by slot.sql; check each operation for errors before proceeding.
gcloud sql import sql assessment-source-dev gs://data-enginner-job-app-platform-demo/source/setup.sql --database=shop --user=postgres
gcloud sql import sql assessment-source-dev gs://data-enginner-job-app-platform-demo/source/slot.sql --database=shop --user=datastream
```

The `source_ca` variable is populated locally by bootstrap. Create the Datastream service identity, then grant it `roles/secretmanager.secretAccessor` on `assessment-cdc-password` only. Enable `cdc_ready` and apply the core root again. Datastream's initial backfill is asynchronous; a RUNNING stream does not yet prove that rows have arrived.

```powershell
gcloud dataflow jobs run assessment-events-dev --project=data-enginner-job-app --region=europe-west2 --gcs-location=gs://dataflow-templates-europe-west2/2026-09-01-00_RC00/PubSub_Subscription_to_BigQuery --staging-location=gs://data-enginner-job-app-platform-demo/dataflow-temp --service-account-email=demo-dataflow@data-enginner-job-app.iam.gserviceaccount.com --worker-machine-type=e2-standard-2 --num-workers=1 --max-workers=1 --subnetwork=https://www.googleapis.com/compute/v1/projects/data-enginner-job-app/regions/europe-west2/subnetworks/assessment-demo --disable-public-ips '--parameters=inputSubscription=projects/data-enginner-job-app/subscriptions/assessment-demo-processing,outputTableSpec=data-enginner-job-app:platform_demo.events,outputDeadletterTable=data-enginner-job-app:platform_demo.rejected_events,javascriptTextTransformGcsPath=gs://data-enginner-job-app-platform-demo/code/event_transform.js,javascriptTextTransformFunctionName=transform'
python -m demo.publish_events COLLECTOR_URL_FROM_TERRAFORM
# Execute demo/events_curated.sql in BigQuery before verification.
python -m pip install -r demo/requirements-verify.txt
python -m demo.verify_events
python -m demo.verify_cdc initial
gcloud storage cp demo/source_changes.sql gs://data-enginner-job-app-platform-demo/source/changes.sql
gcloud sql import sql assessment-source-dev gs://data-enginner-job-app-platform-demo/source/changes.sql --database=shop --user=postgres
python -m demo.verify_cdc changed
```

Upload the DAG to `dag_prefix` from Terraform output; wait for `python -m demo.airflow discovery` to list it without import errors. DAG file updates also take time to propagate.

```powershell
python -m demo.airflow trigger demo-valid
python -m demo.airflow status demo-valid
python -m demo.crm_test verify --label valid
# After the run finishes, stage duplicate, trigger demo-duplicate, inspect its
# expected validation failure, then verify that crm_current remains unchanged.
python -m demo.crm_test duplicate
python -m demo.airflow trigger demo-duplicate
# Repeat with stale / demo-stale, then restore good input for a final valid run.
```

`demo/analytics.sql` joins the three routes and exposes CRM snapshot age beside recorded order region. The demonstrated replica represents current source state, including deletions; it is not a historical sales ledger. The tiny demo scans are capped, but the checks do not establish production throughput or recovery targets.

## Teardown

Cancel the demo Dataflow job first and wait for a terminal state. Review and apply destroy plans for `infra/platform-run` first and `infra/platform-demo` second. Never destroy the base `infra/environments/dev` root as part of demo cleanup. Demo destruction deletes temporary datasets, bucket contents, image repository, Cloud Run resources, source database, Composer environment and their IAM bindings. Those deletion settings are intentionally limited to synthetic demo data.

Remove the replication secret and any Composer-generated storage bucket left after environment deletion. Retain the Terraform state bucket and existing Part 2 dev resources. API enablement alone is not a running worker. Verify that no demo Dataflow job, Composer environment or SQL instance remains running before calling cleanup complete.

`python -m demo.verify_cleanup` checks the named resources from this recorded run and confirms the original six-row orders table remains. Update its generated Composer bucket name and Dataflow job ID when auditing a different run. The [recorded verification](../docs/platform-verification.md) includes the completed teardown.

Costs include provisioning time, Composer environment capacity, streaming workers and source database/storage. Worker limits and job timeouts reduce exposure but do not create an account-wide monetary cap. There is no recurring schedule for this demonstration.
