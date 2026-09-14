# Source correction and optional downstream repair

Our production preference is an agreed source contract: when a required numeric/date field violates that contract or is missing, quarantine the record and ask the source owner to correct it. Meeting the assessment's cleaning requirement does not mean inventing complete data.

## Two options to present

| Option | What we do | Trade-off |
| --- | --- | --- |
| Correct at source (preferred in production) | Report invalid/missing fields and request a corrected export | Improves the upstream data for all consumers, but reports remain incomplete while we wait |
| Controlled downstream repair (assessment demonstration) | Apply explicit approved mappings such as `Three` → `3`; use authoritative replacement data if supplied | Faster for known cases, but adds maintained rules and can conceal a recurring source problem |

The current code demonstrates the second option for the two known text phrases. It does **not** implement a strict source-contract mode switch. In production we would agree which representations the contract permits before enabling such mappings. For additional repairs, keep the original value, corrected value, rule/version, and approval or source evidence. That repair audit is a proposed extension, not an existing automated workflow.

Unknown prices or dates cannot be repaired without evidence. Defaulting to zero, an average, today's date, or quantity 1 would invent facts. An agreed imputation for a separate statistical use must be flagged as an estimate and must not be silently mixed into this spending report.

## What quarantine currently does

Each CLI run writes a new local output directory. `cleaned_orders.csv` contains accepted rows only. `rejected.jsonl` retains the original fields, source record number, all detected rejection reasons, and warnings. `duplicates.jsonl` separately records removed valid repeats. Input is never overwritten.

For the current sample, quarantine contains 102 and 110 (missing amount), and 103 and 108 (invalid date); 103 also has a missing-quantity rejection reason. Orders 104 and 109 remain accepted with missing-product warnings. Quantity is mandatory because the unit-price assumption requires it to calculate spending.

This is logical separation on local disk, not an enforced security boundary. The proposed cloud extension is a restricted quarantine location with explicit retention and an operations-only identity. Do not upload the entire output directory to the analyst-facing destination. Cloud quarantine, its IAM, and automated incident integration are not implemented by the current Terraform.

## How we request and verify a fix

1. The cleaner now creates `source_fix_request.json`: a draft containing the input filename, run-directory identifier, affected order IDs, reasons, and accepted-record warnings. It references quarantine without copying raw customer payloads. It is marked `draft_not_sent`; owner and ticket reference are unassigned.
2. The operator assigns the source owner, reviews the issues and business impact, and submits the request through the agreed ticket channel. Share raw evidence only through authorised access. No ticket or message is sent by this code.
3. Ask for confirmed values and a corrected, identifiable export, plus an explanation of the recurring source defect where relevant. Do not edit the original file in place.
4. Run the corrected export through the same validation into a new run directory. Link the old and new runs to the ticket, check the affected IDs and counts, and publish through a replacement/upsert process that cannot double-count an earlier accepted order.
5. Close the request after revalidation and reconciliation succeed, not merely because the source says it is fixed. Until then, expose the rejected count and report coverage.

Ticket submission, ownership tracking, corrected-export lineage and cloud publication are manual/planned steps. The executable scope is quarantine files plus a draft handoff artifact; no automated request tracking or replay service is claimed.
