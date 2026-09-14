# Senior Cloud Data Engineer assessment

Working submission for the supplied GCP assessment. We are starting with architecture discussion; Python is selected for Part 2.

## Work through the project

Open the [architecture decision notebook](docs/learning.html) in a browser. It works offline and focuses on one real project decision at a time, with alternatives, worked examples, an understanding check, and space to explain your reasoning. Browser notes can be downloaded; they do not change repository decisions.

Start with the [assessment requirements](docs/assessment-requirements.md), [logical architecture draft](docs/architecture.md), and [first proposed decision](docs/decisions/001-source-freshness.md). The earlier slide deck remains in `docs/first-principles.html` as a historical draft; the notebook replaces it as the learning entry point.

## Review approach

Use small commits representing complete changes. Subjects describe the change; bodies explain the reason, alternatives, consequences, and relevant validation. Record actual decisions as they are made, without presenting proposals as agreed requirements.

## Current scope

- Part 1: discuss assumptions, compare architecture options, then produce a diagram and decision record.
- Part 2: build and verify Python cleaning, Cloud Storage output, BigQuery loading, and analytical SQL.
- Optional infrastructure as code: decide after the implementation scope is agreed.

No cloud resources have been provisioned by this repository. Cloud execution and streaming behaviour have not been validated. A GitHub remote has not yet been configured.
