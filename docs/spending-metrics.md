# Spending assumptions

For this assessment, **we assume `OrderAmount` is the product's unit price**, and calculate total order value as `OrderAmount × Quantity`. The brief does not define the field clearly. This is an assumption, not a fact established by the sample values.

**In a real project, we would confirm this definition with the business stakeholder or source-system owner before using the results for reporting.** We would check whether the amount is per unit or already a total, how discounts, tax, shipping and refunds are represented, and whether each record is an order or an order line. Divisibility by quantity does not establish the field's meaning.

Under this assumption:

- A valid quantity is required to calculate spending. Do not replace a missing quantity with 1.
- The 30-day metric is each customer's average total order value on the reporting date and previous 29 calendar days. It is an average over orders, not over days, and includes all orders on the same date.
- Regional spending is average total order value grouped by the region recorded on the order.
- Results cover accepted records only and do not represent complete revenue when records are rejected.

If the stakeholder confirms that `OrderAmount` is already the total, use it directly instead of multiplying; update the transformation, tests and metric documentation together.

## Implementation and evidence

The cleaner now requires quantity and appends exact `TotalOrderValue`, rejecting overflow rather than rounding. Original `OrderAmount` remains available.

- [Customer rolling SQL](../sql/customer_rolling_spending.sql) returns a metric on each order date. `RANGE BETWEEN 29 PRECEDING AND CURRENT ROW` over `UNIX_DATE(OrderDate)` uses calendar days and includes same-date peers. There are no generated rows for days without orders.
- [Regional SQL](../sql/regional_spending.sql) averages accepted order totals and includes an order count. It does not average customer averages.

Replace `PROJECT_ID.DATASET_ID` with the deployed destination before executing. Input must be the accepted, deduplicated cleaner output. For the sample, regional average order values are London 2155, Yorkshire 150, and Tyne & Wear 100 (two accepted orders each).

Tests execute the SQL in SQLite with a UNIX_DATE compatibility function. They cover the inclusive 30-day boundary, same-date peers, customer isolation, gaps, order weighting, ties and empty input. This checks small-fixture semantics, not BigQuery NUMERIC behaviour or cloud execution. Python tests independently check exact totals and numeric overflow. Two live BigQuery runs now also verify the sample, calendar boundaries and NUMERIC arithmetic; see [cloud evidence](cloud-verification.md).

The calendar-window syntax follows the [BigQuery window function documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/window-function-calls).
