# Full-platform cloud verification

On 14 September 2026, the optional demonstration exercised all three source routes in `data-enginner-job-app`, `europe-west2`, using synthetic data. All functional checks below passed. The temporary platform was then torn down and its deletion verified.

The [machine-readable evidence](evidence/platform-demo.json) contains execution and query IDs, observed rows, task outcomes and exact deployed version identifiers. The [demo guide](../demo/README.md) explains the code and reproduction order. This extends the assessment; Part 1 itself asks for a design rather than a deployed production platform.

## What actually ran

| Route | Observed result |
| --- | --- |
| Cloud Run orders job → Cloud Storage → BigQuery | Four container executions succeeded. Each stored six accepted orders and retained four rejected records plus the draft source-fix request. Exact totals, regional averages, rolling-window boundaries and NUMERIC precision checks passed. |
| Authenticated collector → Pub/Sub | Anonymous request returned 403. Four authenticated fixture messages returned 202 only after successful publication. |
| Pub/Sub → Dataflow → BigQuery | Three accepted raw rows and one rejected event. The rejection retained its original payload and `unsupported:event_type` reason. |
| Raw Pub/Sub archive → Cloud Storage | Four Avro records decoded and matched the four published payloads, including the invalid event. |
| Curated event view | The deliberate exact retry became one event: two unique events remained. Conflicting payloads under one ID are excluded by the view rather than arbitrarily selected. Conflict handling was reviewed in SQL but was not a separate live producer test. |
| PostgreSQL → Datastream → BigQuery | Initial orders 201, 202 and 203 arrived. After source mutations, 201 had unit price 175, 202 was absent, and new order 204 had unit price 50 and quantity 3. |
| Composer → CRM staging → publication → Cloud Run | All four tasks in `demo-complete` succeeded. Its Cloud Run execution was `assessment-orders-cloud-wrzg7`. |
| CRM quality and age gates | `demo-duplicate` failed for a duplicate customer ID; `demo-stale` failed for an older snapshot. Both left the three-row snapshot dated 2026-09-14 unchanged and prevented the downstream batch task. |
| Joined analytical view | CDC orders, CRM and curated events joined correctly: totals 175, 1400 and 150 for orders 201, 203 and 204; event counts 1, 0 and 1 respectively. Recorded order region and CRM snapshot date remain visible. |

Dataflow used Google's dated `2026-09-01-00_RC00` Pub/Sub-subscription-to-BigQuery template with one private-IP `e2-standard-2` worker. Its job ID was `2026-09-14_05_29_51-10151398287747062658`. It reached `JOB_STATE_CANCELLED` after verification.

Composer used `composer-3-airflow-2.11.1-build.19`, one worker and a manual DAG with no schedule or task retries. Cloud SQL used PostgreSQL 15, a small zonal instance, encrypted connections and the Datastream regional IP allowlist. The replication login's default administrative membership was revoked; its password stayed in Secret Manager and did not enter Terraform state or Git.

Cloud Run used immutable image digest `sha256:6f2e5d6495c2dd1e7d2d664dce76817e401b84d1e6e8ddecdd37dca76c1f038f`, produced by build `35fc6c4d-9936-4f3a-a8bb-741e9605f323`. The first execution ran independently; the final one was orchestrated by Composer. Two intermediate Airflow tasks failed while their already-launched Cloud Run executions completed successfully, which is why four successful container executions do not mean four successful DAG runs.

## Issues found and corrected

- A conflicting Pub/Sub SDK dependency prevented the first image build. The collector uses the authenticated Pub/Sub REST publish endpoint with the existing authentication dependencies.
- Source setup and replication-slot creation needed separate successful SQL imports. A failed import rolled back earlier grants. The replication slot is created under the replication role.
- A 10 MiB whole-script cap stopped the CRM SQL after its first minimum billed scan. The four-statement script now has a 40 MiB cap; the Part 2 individual-query cap remains 10 MiB.
- Composer DAG file changes took time to propagate. The deployed source was checked before retrying with the corrected limit.
- Job invocation permission did not allow Composer to poll the regional operation. The final configuration uses a single expiring `run.operations.get` permission and job-scoped metadata access. The complete DAG then passed.

## Limits of this evidence

These are small functional tests, not throughput, outage recovery or long-running cost tests. There is no measured production latency guarantee. The CRM input is mutable between manual runs; production should identify immutable export versions and validate a stronger source completion contract. The demo does not implement incident delivery, archive replay, a historical order ledger, point-in-time ML features or production alert thresholds.

The event UDF's additional impossible-calendar-date guard was added and checked locally after the streaming run. The live run verifies accepted events and unsupported-event rejection; it does not separately verify that additional guard inside Dataflow. The deployed UDF hash is retained in the evidence. Local Python checks passed 26 tests, and the JavaScript checks cover valid leap day, impossible date, missing field, unsupported type and malformed JSON.

The demo deliberately uses shared private storage for runtime artifacts and permissive deletion settings for synthetic resources. Those settings are not a production quarantine access policy or retention commitment. The Terraform environment roots for pre/prod were not deployed.

## Cleanup

The user requested teardown after testing. The demo has distinct `platform-demo/dev` and `platform-demo/run` Terraform state prefixes. Cleanup removes the streaming worker, Cloud Run resources, Composer, Datastream, source database, temporary datasets, image repository, demo bucket and temporary IAM grants. The replication secret and Composer-generated bucket are cleaned up separately.

The original Part 2 `orders_dev` dataset, `data-enginner-job-app-orders-dev` bucket, loader identity and private Terraform state bucket are retained. Local run files, quarantine and raw Avro samples are retained under ignored `outputs/platform-demo`; selected synthetic results are committed in the evidence JSON. No credentials, local Terraform variables or state files are submitted.

Final cleanup verification passed at 13:17 UTC on 14 September 2026. Both demo Terraform states are empty after 44 resource deletions. The named Composer, SQL, Datastream, Cloud Run, Pub/Sub, dataset, image, network, bucket and secret endpoints returned 404; Dataflow remained CANCELLED. The original orders table still contained six rows, both original buckets remained, and the base dev Terraform plan reported no changes. Provisioning and test usage still incur charges; deletion does not undo usage already incurred.
