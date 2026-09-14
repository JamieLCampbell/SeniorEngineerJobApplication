# Orders infrastructure: dev / pre / prod

One shared module provisions the Part 2 foundation: Cloud Storage, a BigQuery dataset and `cleaned_orders` table, a loader service account with scoped access, and the required APIs. It does not deploy Datastream, Dataflow, Pub/Sub, or Composer. Three environment configurations exist; dev was applied and verified on 14 September 2026. Pre/prod are not deployed.

## Why three environments?

| Environment | Purpose | Default/example policy |
| --- | --- | --- |
| dev | Try code and schema changes using synthetic data | Seven-day file lifecycle; Terraform may replace the table |
| pre | Rehearse the same change and checks before production | Fourteen-day file lifecycle; same table/bucket deletion guards as prod |
| prod | Hold the promoted, reviewed workload | Explicit retention input; example 90 days is illustrative, not an agreed policy |

Each root calls the same module, pins Google provider 8.2.0, and uses its own state prefix, bucket/table names, and loader identity. Use a **separate existing GCP project and private state bucket per environment** to isolate IAM, quotas, billing attribution, and state access. Names and state prefixes alone are not security boundaries. Root inputs cannot check another root's project choice: verify all three project IDs differ and use environment-specific deploy permissions. The known personal project is suggested for dev only; pre/prod project IDs remain to be supplied.

Directories make the target visible in commands and review. Terraform workspaces would save a little repetition but would make the selected state less obvious and would not themselves isolate credentials. Separate repositories would add release coordination for this small project. Share code, not state or data.

## Layout

```text
infra/
  environments/dev/   # root configuration and local config examples
  environments/pre/
  environments/prod/
  modules/orders/     # shared resources, schema, and mocked plan tests
```

## Setup (before the first real plan)

1. Install Terraform 1.7 or newer, below 2.0. This change was checked with 1.16.2. Authenticate through `gcloud auth application-default login`; never put a key in tfvars.
2. Supply an existing, billing-enabled project for the chosen environment. Project creation and billing are intentionally outside this module. Enable the Service Usage API as a bootstrap prerequisite. The deploy identity needs permission to enable the listed APIs, manage the bucket/dataset/table and service account, grant the listed IAM roles, and access its state bucket. The loader identity is not the deploy identity.
3. Bootstrap a dedicated private Cloud Storage state bucket in that environment's project. Use uniform access, public access prevention, and object versioning. Grant only the appropriate deploy identities access. It must exist before `terraform init`; it cannot be created by the configuration whose state it stores. Do not use the orders data bucket or apply data-file expiry rules to state. This bootstrap step is not automated here; the dev state bucket was created with the documented controls before the first apply.
4. Copy `terraform.tfvars.example` to `terraform.tfvars` and `backend.hcl.example` to `backend.hcl` inside the chosen environment. Fill in the actual project and state bucket. Both local files are ignored by Git. Retain the fixed environment-specific prefix in `main.tf`.
5. Confirm location and retention. `europe-west2` (London) is an assessment default for both data resources, not a residency requirement from the brief. Pre mirrors prod's structure and protections; differing non-production retention keeps synthetic files short-lived. Production retention must be agreed before apply.

From the repository root, for example:

```powershell
terraform '-chdir=infra/environments/dev' init '-backend-config=backend.hcl'
terraform '-chdir=infra/environments/dev' plan '-out=changes.tfplan'
# Inspect the plan's project, resource names, IAM changes, and replacements.
terraform '-chdir=infra/environments/dev' apply changes.tfplan
terraform '-chdir=infra/environments/dev' output
```

Repeat with `pre` or `prod` only after supplying their separate configurations and reviewing their plans. Do not reuse the saved dev plan for another environment. Applying incurs cloud usage. Dev init, plan and apply have been run against GCP; see [live evidence](../docs/cloud-verification.md).

## Promotion and boundaries

Validate and apply a Git revision in dev, run the Python load/query checks, then promote the **same revision** to pre with synthetic data. Review pre's plan and results before planning prod. Production data does not get copied into dev/pre. These are the documented release steps; automatic deployment and enforced GitHub approval gates are not configured.

State lives in GCS, which supports locking. Do not commit state or saved plans; commit dependency lock files. Project and state-bucket access provide the actual environment boundary, and GCS versioning provides recovery from state mistakes.

The loader can manage objects in its own data bucket, edit its dataset, and create BigQuery jobs in its project. It has no broad project Editor role or cross-environment grants. It is created without a private key. To use it locally, explicitly grant the chosen developer permission to impersonate it; this module does not automatically grant that access. The current developer was granted Token Creator on the dev loader for the verified keyless batch runs. No analyst identities were supplied, so none are granted access here.

## Data and deletion choices

The schema preserves the supplied column names. Date-only input maps to `DATE`, money to exact `NUMERIC`, and integral identifiers/quantity to `INTEGER`. The schema includes derived TotalOrderValue as NUMERIC. Fields remain nullable at storage level; the Python cleaner enforces required metric fields, including quantity and total. OrderAmount is assumed to be unit price for this assessment, subject to stakeholder confirmation. Load only accepted cleaner output into the analytical table.

There is no partitioning for a ten-row demonstration and no automatic table expiry. All environments disable bucket force deletion and dataset contents deletion. Pre/prod additionally prevent bucket deletion through the provider and enable table deletion protection. These are Terraform safeguards, not protection against authorised SQL/API deletion or lifecycle expiry. A deliberate teardown or schema replacement may require changing the guards, applying that change, and reviewing data preservation first.

Uploaded objects become eligible for lifecycle deletion at the configured age. Seven-day soft delete is explicit in every environment; expiry is not immediate permanent erasure and can add storage cost. The production example is not a retention recommendation.

## Local checks without deployment

```powershell
terraform fmt -check -recursive infra
terraform '-chdir=infra/environments/dev' init -backend=false -input=false
terraform '-chdir=infra/environments/dev' validate
# Repeat init/validate for pre and prod.
terraform -chdir=infra/modules/orders init -backend=false -input=false
terraform -chdir=infra/modules/orders test
```

The tests use a mocked Google provider: they verify planned configuration, not API permissions, globally unique bucket names, billing, quotas, or actual cloud behaviour. All three roots validated and all five mock tests passed. A credentialed dev plan/apply and two live pipeline runs also passed; a subsequent plan reported no changes.

Sources: [GCS backend](https://developer.hashicorp.com/terraform/language/backend/gcs), [bucket resource](https://registry.terraform.io/providers/hashicorp/google/8.2.0/docs/resources/storage_bucket), [BigQuery table resource](https://registry.terraform.io/providers/hashicorp/google/8.2.0/docs/resources/bigquery_table).
