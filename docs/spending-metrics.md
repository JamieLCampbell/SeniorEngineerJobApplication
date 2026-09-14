# Spending assumptions

For this assessment, **we assume `OrderAmount` is the product's unit price**, and calculate total order value as `OrderAmount × Quantity`. The brief does not define the field clearly. This is an assumption, not a fact established by the sample values.

**In a real project, we would confirm this definition with the business stakeholder or source-system owner before using the results for reporting.** We would check whether the amount is per unit or already a total, how discounts, tax, shipping and refunds are represented, and whether each record is an order or an order line. Divisibility by quantity does not establish the field's meaning.

Under this assumption:

- A valid quantity is required to calculate spending. Do not replace a missing quantity with 1.
- The 30-day metric is each customer's average total order value on the reporting date and previous 29 calendar days. It is an average over orders, not over days, and includes all orders on the same date.
- Regional spending is average total order value grouped by the region recorded on the order.
- Results cover accepted records only and do not represent complete revenue when records are rejected.

If the stakeholder confirms that `OrderAmount` is already the total, use it directly instead of multiplying; update the transformation, tests and metric documentation together.

Implementation status: these definitions are recorded. The current cleaner still preserves the supplied amount, permits missing quantity with a warning, and does not derive a total. Updating those rules and implementing/testing the spending SQL are the next tasks.
