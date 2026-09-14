-- GoogleSQL. Replace PROJECT_ID and DATASET_ID with the target environment.
-- Input contract: accepted, unique orders with validated dates and total values.
-- Assessment assumption: TotalOrderValue = unit-price OrderAmount * Quantity.
-- Confirm this meaning with a stakeholder before real reporting.
-- RANGE counts calendar days, not the previous 29 orders. Same-date orders
-- share the full day's window because the source has no time-of-day field.
-- Alternative: average daily spend would need a calendar including zero-order days.
SELECT
    OrderID,
    CustomerID,
    OrderDate,
    TotalOrderValue,
    COUNT(*) OVER spending_window AS OrdersInWindow,
    AVG(TotalOrderValue) OVER spending_window AS AverageOrderValue30Days
FROM `PROJECT_ID.DATASET_ID.cleaned_orders`
WINDOW spending_window AS (
    PARTITION BY CustomerID
    ORDER BY UNIX_DATE(OrderDate)
    RANGE BETWEEN 29 PRECEDING AND CURRENT ROW
)
ORDER BY CustomerID, OrderDate, OrderID;
