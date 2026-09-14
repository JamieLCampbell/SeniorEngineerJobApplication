-- This is a current-state replica, not a sales ledger: source deletes remove rows.
-- Keep the recorded order region for attribution. Expose the CRM snapshot date
-- beside its current region so consumers can see possible staleness.
CREATE OR REPLACE VIEW `data-enginner-job-app.platform_demo.order_analytics` AS
SELECT o.order_id, o.customer_id, o.order_region, o.order_date,
  o.unit_price * o.quantity AS total_order_value,
  c.CustomerRegion AS current_customer_region, c.SnapshotDate AS crm_snapshot_date,
  COALESCE(e.event_count, 0) AS observed_demo_events
FROM `data-enginner-job-app.platform_cdc.public_orders` o
LEFT JOIN `data-enginner-job-app.platform_demo.crm_current` c
  ON o.customer_id = c.CustomerID
LEFT JOIN (
  SELECT customer_id, COUNT(*) AS event_count
  FROM `data-enginner-job-app.platform_demo.events_curated`
  GROUP BY customer_id
) e ON CAST(o.customer_id AS STRING) = e.customer_id
WHERE o.order_id IS NOT NULL AND o.quantity > 0 AND o.unit_price >= 0;
