# Assessment requirements

Source: the five assessment photographs supplied on 14 September 2026. This is a structured interpretation, not a verbatim transcription. The assessment instructions describe the deliverables; they do not authorise account changes or submission on the candidate's behalf.

## Part 1: architecture (suggested four hours)

| ID | Requirement | Evidence we will produce | Status |
| --- | --- | --- | --- |
| A1 | Design ingestion, processing, storage, and querying for e-commerce analytics on GCP | Architecture diagram showing the data routes | Initial logical outline |
| A2 | Cover transactional databases, clickstream, and CRM | Source routes and source integration assumptions | Routes selected (003–005); source compatibility and CRM export interface unresolved |
| A3 | Consider real-time ingestion and batch processing | Explanation of which sources use each route and why | Mixed approach accepted; numeric targets open |
| A4 | Include services such as Pub/Sub, Dataflow, BigQuery, Cloud Storage, and Composer | Explain each service's role and alternatives | Pub/Sub, Dataflow, BigQuery, and CRM storage roles recorded; orchestration pending |
| A5 | Make data available to analysts and machine learning models | Curated consumption layer in the diagram | Detailed serving needs unresolved |
| A6 | Justify scalability, cost-efficiency, and security | Decision records and operational controls | Pending |
| A7 | Discuss latency, quality, and performance trade-offs | Consequences and revisit conditions in each decision | Started |
| A8 | Optional, preferred infrastructure as code | Reproducible provisioning if included | Scope not yet chosen |

## Part 2: implementation (suggested three hours)

| ID | Requirement | Evidence we will produce | Status |
| --- | --- | --- | --- |
| B1 | Populate the provided ten customer orders in a CSV | Source fixture preserving the supplied values | Pending |
| B2 | Read and clean with Python or Java | Python code with explicit quality rules | Python selected; code pending |
| B3 | Handle missing values, duplicates, invalid dates, and irregular types | Accepted/rejected outputs and meaningful tests | Policies pending |
| B4 | Transform fields and standardise timestamps | Defined output schema and transformations | Pending |
| B5 | Save cleaned data in Cloud Storage | Upload code and evidence of a successful run | Pending |
| B6 | Create a dataset/table and load from Cloud Storage | BigQuery schema, load procedure, and run evidence | Pending |
| B7 | Calculate a rolling 30-day average of customer spending with a window function | SQL and checks against hand-calculated cases | Metric definition pending |
| B8 | Rank regions by average spending | SQL and checks of aggregation grain | Order-region attribution decided (002); amount and denominator pending |

## Submission

Provide architecture diagrams, Python and SQL, and a brief explanation of the approach. The brief accepts a GitHub repository or shared drive. Work is pushed to a private GitHub repository; submission to the reviewers has not occurred. The learning companion is personal study material; it does not replace the final architecture explanation.

## Information the brief does not specify

- Freshness target for each source; “real time” has no numerical target.
- Event rate, payload size, peak load, historical volume, or retention period.
- Database engine, change capture support, clickstream publisher, or CRM export/API capability.
- Recovery targets, budget, deployment region, and sensitive field policy.
- Whether ML requires offline training data or low-latency online features.
- Whether OrderAmount is a unit amount or an order total.
- Whether similar orders with different IDs are duplicates.
- Whether spending averages use orders, customers, or calendar days as their denominator.

We will document assumptions where needed and identify what changes if they prove false. No one-minute target or hourly CRM schedule has been agreed.
