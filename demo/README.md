# Full platform demonstration

This optional extension is separate from the submitted Part 2 batch. It deploys synthetic sources to exercise the proposed routes, then removes the continuously billed resources. Do not deploy it as an always-on personal environment.

## Components and limits

- Cloud Run Job executes the Python orders pipeline using the existing dev loader identity. Inputs come from Cloud Storage; reports, rejected records and source-fix drafts are persisted in the restricted demo bucket before the container exits.
- An authenticated Cloud Run service publishes small JSON requests to Pub/Sub. One private-IP Dataflow worker runs Google's pinned Pub/Sub-to-BigQuery template with a small validation UDF. Invalid events go to a separate BigQuery table. An independent Cloud Storage subscription archives events.
- A small Cloud SQL PostgreSQL 15 instance supplies actual changes to Datastream. Connections require encryption and only Datastream's regional IPs are allowlisted. The replication password is stored in Secret Manager, not Terraform or Git.
- Composer 3 runs a manual CRM DAG: check export completeness, load staging, validate, publish. It has one active DAG run, no schedule and no task retries for this bounded demonstration. Invalid snapshots must leave the last valid snapshot available.
- The existing `orders_dev` resources are reused only by the batch demonstration. Temporary resources use `platform_demo` / `platform_cdc` datasets, their own Terraform state prefix and a dedicated bucket.

The collector limits request size and acknowledges only after publishing. It does not make producer retries exactly once. The event ID must remain stable across retries; curated event queries deduplicate by ID for this synthetic contract. Conflicting events under the same ID and production deduplication horizons need explicit rules.

## Reproduction order

1. Enable the APIs used by the extension in the chosen dev project. Create Pub/Sub's service identity before the archive subscription IAM grants. Use the existing private state bucket with the `platform-demo/dev` prefix; never reuse the base dev state prefix.
2. Copy the example variables, select a currently supported Composer 3 image and discover Datastream's regional static IPs. Review `terraform plan` for `infra/platform-demo`. This starts a paid database and Composer environment when applied.
3. Build `demo/Dockerfile` through `demo/cloudbuild.yaml` using the builder account. `.gcloudignore` restricts uploaded source. Set the immutable resulting image digest in `infra/platform-run/terraform.tfvars` and initialise that root with the same state bucket. Its distinct `platform-demo/run` state allows container deployment after the image exists without coupling it to slow Composer provisioning. Review and apply its plan.
4. Upload the synthetic input CSVs, CRM manifest and event UDF. Run `python -m demo.bootstrap_source`, then import its password-free `source/setup.sql` into the `shop` database as postgres. Wait for success, then import `source/slot.sql` as datastream. These must be separate successful transactions: a failed SQL import rolls back its earlier grants. Grant the Datastream service agent secret-version access on the replication secret. Enable `cdc_ready` in the core root only after replication setup completes, then review and apply the three-resource Datastream plan.
5. Launch the pinned Dataflow template with one `e2-standard-2` worker, the demo subnetwork, private worker IPs, the processing subscription, accepted/rejected tables and `transform` UDF. Its runtime job ID is recorded separately from Terraform.
6. Upload `demo/dags/assessment_crm.py` to the Composer DAG directory and wait for DAG discovery. Run the Cloud Run Job and the manual DAG, which also invokes the orders job after a valid CRM publication. Send synthetic valid and invalid click events, and modify the source database to verify CDC insert/update/delete handling.
7. Preserve execution IDs, query results, archives and negative-test evidence before teardown. Final verification status is recorded separately; source code alone is not evidence that a cloud test passed.

## Teardown

Cancel the demo Dataflow job first and wait for a terminal state. Review and apply destroy plans for `infra/platform-run` first and `infra/platform-demo` second. Never destroy the base `infra/environments/dev` root as part of demo cleanup. Demo destruction deletes temporary datasets, bucket contents, image repository, Cloud Run resources, source database, Composer environment and their IAM bindings. Those deletion settings are intentionally limited to synthetic demo data.

Remove the replication secret and any Composer-generated storage bucket left after environment deletion. Retain the Terraform state bucket and existing Part 2 dev resources. API enablement alone is not a running worker. Verify that no demo Dataflow job, Composer environment or SQL instance remains running before calling cleanup complete.

Costs include provisioning time, Composer environment capacity, streaming workers and source database/storage. Worker limits and job timeouts reduce exposure but do not create an account-wide monetary cap. There is no recurring schedule for this demonstration.
