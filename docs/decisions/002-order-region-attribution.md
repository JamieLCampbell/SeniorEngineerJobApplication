# 002: Attribute spending to the region recorded on the order

Status: accepted for this project on 14 September 2026.

## Decision

Use the supplied `OrderRegion` for historical regional spending. Treat it as the region recorded for the order, an explicit interpretation of the sample field rather than a guarantee about its upstream provenance. Do not join current CRM data to replace it.

If the region is missing or invalid, preserve that quality issue for the cleaning policy to handle; do not infer a historical region from a current customer profile. A legitimate source correction can update an order through an explicit, auditable correction process. A customer moving is not such a correction.

## Alternatives and trade-offs

| Meaning | Benefit | Consequence | Appropriate use |
| --- | --- | --- | --- |
| Region recorded on the order — chosen | Uses the provided field; customer moves do not reassign past sales; no CRM dependency for this metric | Inherits source errors; cannot describe the current customer base | Historical regional spending |
| Current customer region | Groups historical spending by where customers belong now | Customer moves reassign prior spending; results depend on CRM snapshot age | Current customer segmentation or campaign planning |
| Customer region at order time | Reconstructs historical customer attributes | Requires effective-dated CRM history, valid order timestamps, and non-overlapping intervals | Historical customer analysis where order attributes are insufficient |

## Worked example

An order records Yorkshire. The customer later moves to London. The order remains attributed to Yorkshire in our historical spending report. A separate current-customer report could attribute that customer's past spending to London, but must name that different meaning and expose the CRM snapshot time.

This decision does not assume that billing address, shipping address, and customer residence are interchangeable. Clarify the upstream definition of OrderRegion before using the design in production.

## Effect on the architecture

The regional report reads order data without a CRM enrichment dependency. An older CRM import cannot make this report's region stale because the report does not consume that import. Batch CRM therefore remains a reasonable working proposal for other uses that tolerate it; this decision does not approve a cadence or settle every CRM freshness requirement.

## Implementation and potential alternative

[Order region attribution SQL](../../sql/order_region_attribution.sql) explicitly selects the order field. Its inline comment records the alternative: add a separate current-customer report, or use an effective-dated historical join with `valid_from <= OrderDate < valid_to`. Validate that each order matches at most one history row; ambiguous or unmatched historical joins must not silently duplicate orders or invent regions.

The SQL is an attribution building block, not the finished average-spending query. Amount meaning, aggregation denominator, and quality handling remain separate decisions. Its project/dataset placeholders must be replaced when the cleaned table exists.

## Revisit when

- The stakeholder asks for current customer geography rather than historical order geography.
- The source definition shows OrderRegion does not represent the intended sales attribution.
- OrderRegion is unavailable and a trustworthy historical CRM source exists.

Keep alternative reports separately named so changing the analytical question does not silently change the original report.
