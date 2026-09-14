-- GoogleSQL. Replace PROJECT_ID and DATASET_ID after creating cleaned_orders.
-- Attribution building block; see regional_spending.sql for the aggregation.
-- Assessment assumption: OrderAmount is unit price, so total = amount * quantity.
-- Confirm with a stakeholder/source owner before reporting in a real project.
-- See docs/spending-metrics.md; this query only selects region attribution.
-- Decision 002: historical spending uses the region recorded on each order.
-- A later customer move must not reassign that order to a new region.
-- Keep missing regions visible for the cleaning/quality policy; do not fill
-- them from current CRM data, which does not establish the historical region.
--
-- Alternative: expose a separately named current-customer-region report using
-- a CRM snapshot, with its snapshot time disclosed. If customer region AT ORDER
-- TIME is needed instead, join effective-dated history on CustomerID and
-- valid_from <= OrderDate AND OrderDate < valid_to (allow an open final interval).
-- Require valid timestamps and at most one matching history row per order;
-- surface unmatched/ambiguous records rather than multiplying order values.
-- See docs/decisions/002-order-region-attribution.md for the trade-offs.

SELECT
    OrderID,
    CustomerID,
    OrderRegion AS order_region
FROM `PROJECT_ID.DATASET_ID.cleaned_orders`;
