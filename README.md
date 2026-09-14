# Senior Cloud Data Engineer assessment

This project turns the supplied customer-order CSV into cleaned data in Cloud Storage and BigQuery, then calculates 30-day customer spending averages and regional spending. Rows that cannot be safely repaired are quarantined with reasons and a draft request for source correction.

**Verified result:** six accepted orders and four quarantined records. The batch and analytical SQL passed live Google Cloud checks. Part 1 provides the wider e-commerce architecture; an optional demonstration also tested its CDC, clickstream and CRM routes with synthetic data.

## Review path

| Assessment deliverable | Start here |
| --- | --- |
| Part 1: architecture, requirements and trade-offs | [Diagram and explanation](docs/architecture.md) |
| Part 2: reusable Python cleaning | [Cleaner](orders/cleaning.py) and [cleaning rules](docs/cleaning.md) |
| Part 2: analytical SQL | [30-day customer average](sql/customer_rolling_spending.sql) and [regional spending](sql/regional_spending.sql) |
| Cloud execution and checked results | [Part 2 batch evidence](docs/cloud-verification.md) and [later full-platform evidence](docs/platform-verification.md) |
| Optional infrastructure as code | [Terraform dev/pre/prod](infra/README.md) |

The [requirements checklist](docs/assessment-requirements.md) maps the submission to the brief. No cloud deployment is needed to read the evidence or run the local cleaner.

## Deployment status

At the final verification on **14 September 2026**:

- The Part 2 dev storage, BigQuery table and scoped loader identity were retained in London (`europe-west2`).
- The optional Cloud Run, Pub/Sub, Dataflow, Datastream, PostgreSQL and Composer demonstration had passed its functional checks and was **torn down**. Code and evidence remain in the repository.
- Pre/prod Terraform configurations were validated locally but **not deployed**.

The demonstration extends Part 1's design requirement. Its small functional tests do not establish production throughput, latency or recovery guarantees; the [verification notes](docs/platform-verification.md#limits-of-this-evidence) describe those boundaries.

## Run locally

From the repository root:

```sh
python scripts/profile_orders.py
python -m orders data/customer_orders.csv --output-dir outputs/cleaning-v1
python -m unittest discover -s tests -v
```

The cleaner and local SQL tests use Python's standard library. Install `requirements-cloud.txt` to include the cloud request tests. The [source CSV](data/customer_orders.csv) preserves the supplied errors; use a new output directory for each cleaning run. Outputs include accepted records, rejected records with reasons, and a draft source-fix request.

For Google Cloud setup, execution and cleanup, see the [batch run guide](docs/cloud-run.md). The optional platform has a separate [reproduction guide](demo/README.md).

## Decisions worth discussing

- **Repair only what is defensible.** Explicit text mappings are supported; missing prices and invalid dates are not invented. Rejected rows retain their source values. The fix request is a draft for manual submission. See [source correction versus downstream repair](docs/source-corrections.md).
- **Treat `OrderAmount` as unit price.** This is an assessment assumption, requiring stakeholder confirmation in real work. Totals use exact decimal arithmetic. See [spending definitions](docs/spending-metrics.md).
- **Keep the order's recorded region for historical spending.** A customer's current CRM region may differ. See [region attribution and alternatives](docs/decisions/002-order-region-attribution.md).
- **Use CDC for transactional orders and streaming for clickstream.** The [CDC decision](docs/decisions/003-order-cdc.md) explains direct Datastream-to-BigQuery delivery; the [clickstream decision](docs/decisions/004-clickstream-ingestion.md) explains the collector, Pub/Sub and Dataflow route and its simpler alternative.
- **Validate CRM snapshots before publication.** Batch exports introduce staleness; failed validation preserves the last good snapshot. See [CRM trade-offs](docs/decisions/005-crm-batch.md).
- **Keep the small batch independently runnable.** Composer coordinates the optional platform, while Part 2 can run manually. See [orchestration alternatives](docs/decisions/006-batch-orchestration.md).

[Operating controls](docs/operations.md) cover access, monitoring, recovery and cost decisions.
