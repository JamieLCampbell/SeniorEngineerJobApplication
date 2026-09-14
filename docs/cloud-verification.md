# Dev verification — 14 September 2026

The Part 2 batch ran successfully in Google Cloud twice, using the scoped loader service account. Full run/job identifiers, query usage and results are preserved in [machine-readable evidence](evidence/dev-2026-09-14.json). These are actual service responses and checked results, not mocked deployment evidence.

## Deployment

- Project: `data-enginner-job-app`; location: `europe-west2`.
- Terraform applied 10 additions, zero changes and zero deletions: data bucket, dataset/table, loader service account, three API entries and three IAM grants.
- Dedicated private, versioned state bucket was bootstrapped separately: `data-enginner-job-app-tfstate-dev`.
- Developer impersonation was granted only on `orders-loader-dev@data-enginner-job-app.iam.gserviceaccount.com`; no service-account key was created.
- A post-load Terraform plan reported **no changes**.
- Pre/prod and the streaming platform remain undeployed.

## Data and query checks

Each run read ten input records, accepted six, rejected four and removed no duplicates. Two missing-product warnings remained. Only accepted CSV files were uploaded. The data bucket contained two 355-byte objects (710 bytes total) after the runs. Quarantine and source-fix drafts stayed local.

| Check | Result |
| --- | --- |
| Stored IDs and exact order totals | 101: 150; 104: 1400; 105: 100; 106: 150; 107: 100; 109: 2910 |
| Second complete snapshot load | Still six rows, with the same totals; no append duplicates |
| Regional averages | London 2155; Yorkshire 150; Tyne & Wear 100; two orders each |
| Sample rolling averages | Customer 1: 150; customer 2: 100; customer 3: 2155 |
| BigQuery calendar fixture | Inclusive 30-day boundary, same-date peers, gaps and customer isolation passed |
| BigQuery NUMERIC fixture | Exact multiplication of a high-precision value matched Python's expected Decimal |
| Local Python suite | 24 tests passed with cloud dependencies installed |
| Terraform mocked suite | Five tests passed |

First successful load job: `31b29ea0-02f4-4bf9-a40b-b2d167109f39`.
Replacement load job: `a169f381-2304-4c4c-8f09-5b096173ec11`.

## Usage and limits

Each successful run used 240 processed bytes for the rolling query, 160 for the regional query and 144 for the stored-total verification. BigQuery reported 10 MiB billed bytes per table-reading query, reflecting minimum query billing units; inline-fixture queries reported zero bytes. Across both successful runs, the six table-reading queries reported 60 MiB billed bytes. These statistics are not currency charges and do not determine whether free allowances apply. Storage and final billing are separate.

The first two local attempts failed at impersonation before upload while the new IAM grant propagated. The developer identity was verified; the same grant then worked without broadening the loader's roles. Those attempts did not load data or execute analytical queries.

This proves the small sequential batch, not production throughput, concurrent loading, disaster recovery or CDC behaviour. The unit-price interpretation remains an assessment assumption requiring stakeholder confirmation in real work. Cloud quarantine and automated ticket submission remain outside the implemented scope.

The dev resources remain available for review; billing is enabled. Data objects have lifecycle expiry, but the BigQuery table and Terraform state do not automatically expire. Follow the [cleanup guidance](cloud-run.md#costs-and-cleanup) after review.
