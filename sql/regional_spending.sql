-- GoogleSQL. Replace PROJECT_ID and DATASET_ID with the target environment.
-- Average total order value over accepted orders, not average customer lifetime spend.
-- TotalOrderValue assumes OrderAmount is unit price: confirm with a stakeholder.
-- Use the order's recorded region; joining current CRM would reassign past sales
-- when a customer moves. A current-customer report should be a separate metric.
SELECT
    OrderRegion,
    COUNT(*) AS AcceptedOrderCount,
    AVG(TotalOrderValue) AS AverageOrderValue
FROM `PROJECT_ID.DATASET_ID.cleaned_orders`
GROUP BY OrderRegion
ORDER BY AverageOrderValue DESC, OrderRegion;
