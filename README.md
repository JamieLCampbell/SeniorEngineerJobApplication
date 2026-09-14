# Senior Cloud Data Engineer assessment

Working submission for the supplied GCP assessment. We are starting with architecture discussion; Python is selected for Part 2.

## Learning deck

Open [GCP data engineering from first principles](docs/first-principles.html) in a browser. It is a self-contained HTML presentation and works offline. Use the arrow buttons or keys, the topic selector, and expandable speaking notes (`N`). Print uses a landscape layout and includes every slide without notes.

The deck adapts the selected Simple Dark Mode template's black background, white typography, and blue accents to responsive HTML. It is a teaching companion, not a PowerPoint file or the final architecture submission. Proposed latency, ingestion, and quality policies are explicitly open for discussion. Google documentation is linked in relevant notes.

## Review approach

Use small commits representing complete changes. Subjects describe the change; bodies explain the reason, alternatives, consequences, and relevant validation. Record actual decisions as they are made, without presenting proposals as agreed requirements.

## Current scope

- Part 1: discuss assumptions, compare architecture options, then produce a diagram and decision record.
- Part 2: build and verify Python cleaning, Cloud Storage output, BigQuery loading, and analytical SQL.
- Optional infrastructure as code: decide after the implementation scope is agreed.

No cloud resources have been provisioned by this repository. Cloud execution and streaming behaviour have not been validated. A GitHub remote has not yet been configured.
