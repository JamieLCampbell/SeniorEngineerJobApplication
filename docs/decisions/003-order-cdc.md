# 003: Capture order changes with CDC

Status: CDC accepted on 14 September 2026. Datastream to BigQuery is the working GCP implementation, conditional on source compatibility.

## Choice and reason

Use Change Data Capture (CDC) for transactional orders. It captures database changes without requiring the shop application to publish a separate event for each change. The brief names transactional databases but does not establish that we can change the application.

Working route: **source database → Datastream → BigQuery replica → analytical SQL**. Use an initial backfill for existing rows, followed by ongoing changes. Prefer the direct BigQuery destination over adding an intermediate processing pipeline when replication is all this step needs.

## Trade-offs

- CDC depends on the database engine/version, replication configuration, permissions, and connectivity. These are unknown in the brief and must be checked before deployment.
- Database changes describe rows, not necessarily business events such as “payment accepted”. Application events would be preferable if those meanings were required; reliable publishing would then need its own design.
- The working design uses merge mode with a supported primary key. Updates and deletes change the replica. It is not an immutable order history or event archive. If audit history or historical reconstruction is required, revisit append-only capture or archival explicitly.
- Replication does not clean the data. Keep the replica separate from analytical transformations, and monitor replication lag and errors. No numerical freshness guarantee has been established.

Pub/Sub and Dataflow can still serve clickstream ingestion and processing; they are not required intermediaries for this direct CDC route. Their selection remains a separate decision.

## Before deployment

Confirm the source engine/version, an appropriate stable primary key (OrderID only if it is genuinely unique), supported types, replication/log retention settings, permissions, and network access. Validate backfill, update/delete behaviour, and recovery on that source. No source database was supplied, so this is an architecture decision, not a deployed CDC implementation.

Sources: [Datastream for BigQuery](https://cloud.google.com/datastream-for-bigquery), [destination configuration and merge mode](https://docs.cloud.google.com/datastream/docs/configure-bigquery-destination), [destination limitations](https://docs.cloud.google.com/datastream/docs/destination-bigquery).
