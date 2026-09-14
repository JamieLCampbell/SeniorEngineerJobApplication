# 005: Land CRM exports before loading reports

Status: accepted for the assessment architecture on 14 September 2026. Not deployed.

**Route: CRM export → Cloud Storage → BigQuery staging → SQL validation → reporting tables.**

## Why this route

Keep the original export in restricted Cloud Storage so we can investigate an issue or rerun a load without asking the CRM for the data again. Load into a staging table first: a failed or incomplete import must not replace the last good reporting data. Use SQL for tabular validation and preparation rather than introduce another processing service.

Record an export identifier, the source snapshot/export time, and the load time. These have different meanings: a file loaded now may contain yesterday's customer information. Expose the source timestamp to consumers. A dated filename alone does not prove when the underlying snapshot was taken.

## Assumptions and reruns

Assume the CRM can provide a complete snapshot for each run; confirm this with the actual source. Load each export in isolation, validate required identifiers, duplicates and completeness, then publish the validated snapshot as a whole. Reprocessing the same export should replace its staged result, not append duplicate customer rows. Only a newer valid snapshot should advance the current report; replaying an older file must not roll it back.

If the CRM provides incremental changes instead, this replacement approach is wrong: we would need keys, update ordering, and deletion handling. A customer absent from a partial extract is not necessarily deleted. Structurally unreadable files fail the load; invalid business records or failed completeness checks block publication and produce diagnostic reasons. Keep the last good report with its existing freshness timestamp visible.

## Trade-off and alternative

Keeping files adds storage and responsibility for customer data. Restrict access and set a finite lifecycle once the recovery and privacy requirements are agreed; export cadence and retention duration are still open. Check soft-delete/versioning settings when implementing expiry. Do not imply that a lifecycle action guarantees immediate permanent erasure.

A direct CRM-to-BigQuery load would remove a storage step, but lose our independent copy for investigation and reruns. Prefer it only if the source or connector provides adequate replay capability. Use compatible bucket/dataset locations for the load.

[Decision 006](006-batch-orchestration.md) assigns batch coordination to Composer in the platform design. No CRM schema or connector was supplied, so this remains Part 1 design work. Part 2 still requires Python cleaning of the supplied orders CSV before its cleaned output goes to Cloud Storage.

Sources: [BigQuery batch loading](https://docs.cloud.google.com/bigquery/docs/batch-loading-data), [Cloud Storage lifecycle management](https://docs.cloud.google.com/storage/docs/lifecycle).
