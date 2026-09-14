# Senior Cloud Data Engineer assessment

Submission for the supplied GCP assessment. Part 1 separates requirements from choices and assumptions; Part 2 includes Python cleaning and a verified Cloud Storage-to-BigQuery batch. An optional full-platform demonstration also exercised the proposed routes with synthetic data.

## Review the submission

Start with the [final architecture and diagram](docs/architecture.md), then the [cleaning rules](docs/cleaning.md) and [live verification evidence](docs/cloud-verification.md). The [requirements checklist](docs/assessment-requirements.md) maps the deliverables to the brief. [Cloud run instructions](docs/cloud-run.md) explain setup, reruns and cleanup.

Accepted: [historical spending uses the order's recorded region](docs/decisions/002-order-region-attribution.md). The [attribution SQL](sql/order_region_attribution.sql) includes the CRM alternatives beside the implementation. It is a building block with table placeholders, not the completed spending aggregation.

Accepted: [CDC for transactional orders](docs/decisions/003-order-cdc.md). Datastream directly to BigQuery passed initial backfill and insert/update/delete checks using a synthetic PostgreSQL source. Compatibility with the employer's actual source still needs confirmation.

Accepted: [clickstream through a collection endpoint, Pub/Sub, and Dataflow](docs/decisions/004-clickstream-ingestion.md). The notes explain each component and when direct delivery to BigQuery would be sufficient.

Accepted: [CRM exports through Cloud Storage and BigQuery staging](docs/decisions/005-crm-batch.md), with SQL validation before publication. Export cadence and retention remain open.

Accepted: [Composer for platform batch coordination](docs/decisions/006-batch-orchestration.md). The small Part 2 implementation runs manually without a Composer environment; a simpler scheduled workflow is documented as an alternative.

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

- Part 1: final architecture diagram, assumptions, alternatives and decision records.
- Part 2: verified Python cleaning, Cloud Storage output, BigQuery loading and analytical SQL.
- [Terraform dev/pre/prod](infra/README.md): shared Part 2 infrastructure module with separate environment roots and state. Dev deployed and verified; pre/prod validated locally only.

Dev storage, BigQuery and scoped loader IAM are deployed in London. The [full-platform verification](docs/platform-verification.md) records Cloud Run, Pub/Sub, Dataflow, raw archives, Datastream CDC, Composer and the joined analytical view. The [demo code and reproduction guide](demo/README.md) use isolated Terraform state so the temporary platform can be removed while retaining the Part 2 foundation. These small functional tests do not establish production throughput or recovery guarantees.
