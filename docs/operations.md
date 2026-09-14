# Operating the proposed platform

These are design controls, not deployed settings. Exact thresholds and retention periods need workload and business requirements.

## Access

Use separate service identities for collection, processing, and batch coordination. The collector publishes to its topic; processing reads its subscription and writes its outputs; batch coordination accesses the required files and jobs. Resolve exact roles and service-agent permissions during provisioning rather than granting project-wide Editor access.

Analysts can query curated data and run query jobs without modifying raw inputs. ML consumers initially use curated tables for offline training; online serving is outside this design. Restrict raw and rejected records, exclude unnecessary customer fields, and avoid payloads in operational logs. Use local Application Default Credentials and deployed workload identities rather than repository-stored keys.

## Monitoring and response

Use Cloud Monitoring and Cloud Logging for failures and pipeline metrics. Every alert needs an owner and response; set thresholds against agreed freshness targets and normal volumes.

| Signal | Why it matters | First response |
| --- | --- | --- |
| Datastream lag/errors | Orders may be stale | Check connectivity and source logs; reconcile after recovery |
| Publish failures and oldest unacknowledged message age | Events may be missing or waiting | Check collection and processing capacity |
| Dataflow errors and rejected-event rate | A running job can still produce unusable data | Check rejection reasons and schema changes |
| Missing CRM export, batch failure, source snapshot age | An old successful load is still stale | Keep the last good report and investigate |
| Input/accepted/rejected counts and write failures | Job status may conceal loss or duplicates | Reconcile by export/event identity before publication or replay |

## Recovery

- CRM: reload a retained export into staging and validate. Do not replace newer reporting data with an older replay.
- Clickstream: use a separate Pub/Sub Cloud Storage subscription to archive payloads and metadata independently of Dataflow, avoiding a custom archive consumer. Monitor that subscription separately. Preserve event IDs, reconcile archived input, and implement duplicate-safe writes before enabling replay. Retention and the replay job remain to be implemented.
- Orders: resume CDC from available source logs, or re-backfill and reconcile if necessary. The current-state replica cannot restore deleted historical versions; audit history would require another design.

Recovery only covers retained inputs. Agree recovery time and acceptable data loss before promising an SLA. A second-region failover system needs a requirement that justifies its cost.

## Scale and cost

Pub/Sub buffers temporary differences in arrival and processing rates within retention limits. Dataflow worker limits and quotas must match measured peaks; extra workers will not repair a bad schema or constrained destination. Backfills also load the source database, so scope and monitor them.

For large curated time-based tables, evaluate date partitioning and useful date filters; select clustering from actual query filters. The ten-row sample does not need these optimisations. Select only needed columns and use BigQuery dry runs and maximum bytes billed for on-demand queries. Monitor spend with a project budget; alerts-only budgets do not stop usage. Set finite raw/staging retention, considering recovery needs and soft-delete settings.

Composer and continuously running Dataflow add operating cost. They remain architecture components, not resources to provision for the CSV demonstration. There is no cost estimate or load-test evidence yet.

Sources: [service accounts](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts), [BigQuery cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs), [Cloud Storage subscriptions](https://docs.cloud.google.com/pubsub/docs/cloudstorage), [budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).
