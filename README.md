# Senior Cloud Data Engineer assessment

Working submission for the supplied GCP assessment. The architecture draft records our choices; Part 2 includes Python cleaning and a verified Cloud Storage-to-BigQuery dev batch.

## Work through the project

Open the [architecture decision notebook](docs/learning.html) in a browser. It works offline and focuses on one real project decision at a time, with alternatives, worked examples, an understanding check, and space to explain your reasoning. Browser notes can be downloaded; they do not change repository decisions.

Start with the [assessment requirements](docs/assessment-requirements.md), [logical architecture draft](docs/architecture.md), and [source freshness decision](docs/decisions/001-source-freshness.md). The earlier slide deck remains in `docs/first-principles.html` as a historical draft; the notebook replaces it as the learning entry point.

Accepted: [historical spending uses the order's recorded region](docs/decisions/002-order-region-attribution.md). The [attribution SQL](sql/order_region_attribution.sql) includes the CRM alternatives beside the implementation. It is a building block with table placeholders, not the completed spending aggregation.

Accepted: [CDC for transactional orders](docs/decisions/003-order-cdc.md). The working GCP route is Datastream directly to BigQuery, subject to source compatibility. It has not been deployed.

Accepted: [clickstream through a collection endpoint, Pub/Sub, and Dataflow](docs/decisions/004-clickstream-ingestion.md). The notes explain each component and when direct delivery to BigQuery would be sufficient.

Accepted: [CRM exports through Cloud Storage and BigQuery staging](docs/decisions/005-crm-batch.md), with SQL validation before publication. Export cadence and retention remain open.

Accepted: [Composer for platform batch coordination](docs/decisions/006-batch-orchestration.md). The small Part 2 implementation will run manually without a Composer environment; a simpler scheduled workflow is documented as an alternative.

## Review approach

Use small commits representing complete changes. Subjects describe the change; bodies explain the reason, alternatives, consequences, and relevant validation. Record actual decisions as they are made, without presenting proposals as agreed requirements.

## Current scope

[Source correction versus downstream repair](docs/source-corrections.md): each cleaning run quarantines rejected rows locally and creates a draft fix request. Submission to a source owner remains manual; no tickets or messages are sent automatically.

[Spending assumptions](docs/spending-metrics.md): treat OrderAmount as unit price for this assessment; in real work, confirm this with a stakeholder before reporting. The cleaner now derives exact totals and requires quantity; the spending SQL is tested locally and in BigQuery.

Inspect the supplied data without changing it:

```sh
python scripts/profile_orders.py
python -m orders data/customer_orders.csv --output-dir outputs/cleaning-v1
python -m unittest discover -s tests -v
```

The cleaner and local SQL tests use Python's standard library. Install requirements-cloud.txt to include the cloud request tests. The source CSV preserves the supplied errors. Use a new output directory for each cleaning run. [Cleaning rules and outputs](docs/cleaning.md) explain six accepted/four rejected sample records and the reusable functions. The rolling and regional SQL, Cloud Storage upload and BigQuery load have passed two live dev runs. See the [cloud run guide](docs/cloud-run.md) and [verification evidence](docs/cloud-verification.md). [Operating controls](docs/operations.md) cover the architecture's access, monitoring, recovery, and cost decisions.

- Part 1: discuss assumptions, compare architecture options, then produce a diagram and decision record.
- Part 2: build and verify Python cleaning, Cloud Storage output, BigQuery loading, and analytical SQL.
- [Terraform dev/pre/prod](infra/README.md): shared Part 2 infrastructure module with separate environment roots and state. Dev deployed and verified; pre/prod validated locally only.

Dev storage, BigQuery and scoped loader IAM are deployed in London. Two live batch runs passed with six orders after replacement; Terraform reports no drift. Streaming behaviour remains unvalidated. Completed changes are pushed to the private [GitHub repository](https://github.com/JamieLCampbell/SeniorEngineerJobApplication) on `codex/architecture-learning`.
