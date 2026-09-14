# Senior Cloud Data Engineer assessment

Working submission for the supplied GCP assessment. We are starting with architecture discussion; Python is selected for Part 2.

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

- Part 1: discuss assumptions, compare architecture options, then produce a diagram and decision record.
- Part 2: build and verify Python cleaning, Cloud Storage output, BigQuery loading, and analytical SQL.
- Optional infrastructure as code: decide after the implementation scope is agreed.

No cloud resources have been provisioned by this repository. Cloud execution and streaming behaviour have not been validated. Completed changes are pushed to the private [GitHub repository](https://github.com/JamieLCampbell/SeniorEngineerJobApplication) on `codex/architecture-learning`.
