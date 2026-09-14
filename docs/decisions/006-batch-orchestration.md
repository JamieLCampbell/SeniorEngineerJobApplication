# 006: Use Composer to coordinate platform batch jobs

Status: accepted for the architecture on 14 September 2026. The optional [cloud demonstration](../platform-verification.md) provisioned Composer and verified a manual CRM workflow followed by the Cloud Run orders job.

Use Cloud Composer (managed Airflow) for the platform's CRM batch dependencies and deliberate reruns of retained exports. Keep the brief's Composer name; current Google documentation also calls the service Managed Service for Apache Airflow.

**Sequence: confirm export ready → load staging → validate → publish if checks pass.**

Composer starts jobs, waits for their completion, and records task outcomes. BigQuery performs the loads and SQL transformations. Composer does not carry every clickstream event or run the continuous CDC stream on a batch schedule.

## Why and what we accept

Airflow provides a place to express dependencies, monitor runs, and retry tasks. This fits a platform with several dependent data jobs and reruns, and gives Composer a concrete role in the assessment. We accept the environment cost and DAG maintenance. The brief mentioning Composer is context, not proof that this workload requires it.

For only this short CRM sequence, Cloud Workflows with Cloud Scheduler would be a simpler alternative that also supports sequencing and retries. Reconsider Composer if broader batch dependencies do not materialise. The Part 2 CSV task needs only the Python pipeline; the optional Composer demonstration verifies the broader design without making it a requirement for that task.

## Failure and rerun rules

- Confirm the expected export is complete before loading. File presence alone need not establish a complete snapshot; use the source's completion signal or agreed export checks.
- Retry transient job failures with bounded attempts; a permanently invalid export needs investigation, not repeated publication attempts.
- Publish only after validation succeeds. Otherwise preserve the last good report and its original freshness timestamp, and surface the failed run.
- Identify the export on every run. Reuse or safely replace its staged result; task retries must not append duplicate records. Rerunning an older snapshot must not overwrite a newer published one.

Schedule, timeout and retry values remain unspecified until export behaviour and freshness needs are known. Reruns only cover retained inputs; Composer cannot reconstruct history that the source or storage no longer holds.

Sources: [Google's orchestration comparison](https://cloud.google.com/workflows/docs/choose-orchestration), [managed Airflow overview](https://docs.cloud.google.com/composer/docs/composer-2/composer-overview).
