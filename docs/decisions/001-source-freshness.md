# 001: Choose freshness by source

Status: proposed for discussion. No numeric freshness target has been agreed.

## Problem

The brief requires real-time analytics and consideration of batch processing. It names transactional databases, clicks, and CRM data, but does not say whether every source must be continuously updated. Choosing tools before resolving this would conceal an important assumption.

Freshness means the elapsed time between a source change and the moment the corresponding data is available to its intended consumer. Source extraction, waiting, processing, warehouse visibility, and dashboard refresh can all contribute.

## Options

| Option | Benefit | Consequence | When it fits |
| --- | --- | --- | --- |
| Schedule all sources in batches | Finite runs and straightforward replay boundaries | Batch waiting may fail the real-time requirement | Consumers accept the measured delay |
| Stream every source | Potential for fresh data throughout | Requires suitable source interfaces and continuous operational handling | Every source has a demonstrated freshness need |
| Stream event sources; batch reference data where acceptable | Supports fresh events without requiring continuous extraction everywhere | Joins can combine fresh events with older customer attributes | Consumers accept a stated reference-data age |

## Recommendation

Use the third option as the working design: a streaming route for clicks and order changes, and a batch route for CRM **if** the agreed use cases tolerate its age. Preserve a replay route. Defer the CRM cadence and numerical freshness targets until their purpose is clear.

This is a source-level choice, not yet a selection of Pub/Sub, Dataflow, Composer, or a database connector. The brief calls for discussing those services; we will justify their roles separately.

## Why this is defensible

The architecture demonstrates both processing modes required by the brief. It makes freshness an explicit business trade-off rather than assuming that every dataset must be equally fresh. It also exposes the main disadvantage: if customer attributes drive an immediate decision, an older CRM snapshot may produce an unacceptable result.

## Concrete example (hypothetical)

A new order arrives at 10:02. Its customer's region changed in CRM at 09:30, but the latest imported CRM snapshot is from 09:00. Joining the order to that snapshot uses an older region even if the order itself was processed immediately.

Possible responses: refresh CRM more often, capture CRM changes, or use the region recorded on the order if that is the intended metric. These alternatives have different business meanings. The sample field is OrderRegion; we must not silently replace it with current customer region.

Resolved for regional spending in [Decision 002](002-order-region-attribution.md): use the region recorded on the order, with no CRM join. CRM freshness therefore does not affect this metric. Other CRM-dependent consumers still need their own freshness requirements.

## What would change the recommendation?

- CRM changes must affect decisions immediately: evaluate an incremental or streaming CRM route.
- Consumers accept longer delays for all data: evaluate scheduled batches against the brief's real-time wording and document the mismatch.
- Order changes cannot be published reliably: inspect database change capture or an outbox mechanism before committing to a connector.
- Measured freshness misses the target: locate the delay before adding services or compute.

## Next discussion

Which remaining consumers need CRM enrichment, and how old can their customer attributes be? Regional order spending no longer depends on that answer.

## Evidence and limits

The requirement comes from Part 1 of the supplied assessment. This is a design argument, not a measured performance or cost claim. Google documents support for both batch and streaming in [Dataflow](https://docs.cloud.google.com/dataflow/docs/overview); the service choice is still a separate decision.
