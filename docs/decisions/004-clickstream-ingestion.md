# 004: Process clickstream through Pub/Sub and Dataflow

Status: accepted for the assessment architecture on 14 September 2026. Not deployed.

**Route: website → collection endpoint → Pub/Sub → Dataflow → BigQuery.**

## Why each component is here

- The collection endpoint receives browser events, checks request size/basic structure, and publishes using a server identity. Cloud publishing credentials must not be embedded in the browser. Its hosting remains unspecified; an existing website backend may suffice.
- Pub/Sub separates collection from processing and buffers published events during processing delays, within configured retention limits. A dedicated subscription supplies Dataflow.
- Dataflow owns event-specific validation, supported type/timestamp conversions, and routing invalid records with a reason to a separate restricted output. BigQuery receives the accepted event records for analysis.

These processing rules are a design assumption: the brief supplies no clickstream schema. We will not add session windows, enrichment joins, or real-time aggregates without a use case.

## Trade-off and simpler alternative

Dataflow gives us an explicit place to maintain and test custom processing, but adds a continuously running job, cost, and operational work. Basic format conversion alone does not require it: a Pub/Sub BigQuery subscription, potentially with a supported transformation, may be sufficient. Revisit direct delivery if the agreed event contract needs only those simpler operations. Dataflow remains the selected assessment route, rather than a claim that it is the only valid solution.

## Failure behaviour to preserve

The endpoint reports acceptance only after publishing succeeds. A retry after a lost response can still publish the same event again, so preserve a stable event ID across producer retries. End-to-end duplicate handling and its retention horizon must be defined before implementation; a buffer does not guarantee unique business events.

Handle known invalid payloads in the pipeline with explicit rejected-record output; distinguish them from infrastructure or write failures, which must surface and be retried appropriately. Do not silently count rejected events as successful analytical data. Monitor publish failures, backlog age, pipeline errors, and accepted/rejected counts. Pub/Sub is a finite buffer, not a permanent archive.

## Scope

This decision describes Part 1. The supplied Part 2 CSV remains a separate Python batch implementation. The final architecture selects a separate Pub/Sub Cloud Storage subscription for the archive. Replay implementation, exact schemas, retention, latency targets and deployment sizing still require source and consumer requirements.

Sources: [BigQuery subscriptions and the Dataflow alternative](https://docs.cloud.google.com/pubsub/docs/bigquery), [Pub/Sub to BigQuery template guidance](https://docs.cloud.google.com/dataflow/docs/guides/templates/provided/pubsub-subscription-to-bigquery), [Dataflow's Pub/Sub integration guidance](https://docs.cloud.google.com/dataflow/docs/concepts/streaming-with-cloud-pubsub).
