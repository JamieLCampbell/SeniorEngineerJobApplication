-- Producer retries reuse event_id. Collapse exact duplicates; exclude conflicting
-- payloads under the same ID rather than choosing an arbitrary version.
CREATE OR REPLACE VIEW `data-enginner-job-app.platform_demo.events_curated` AS
WITH distinct_events AS (
  SELECT DISTINCT event_id, customer_id, event_type, event_time
  FROM `data-enginner-job-app.platform_demo.events`
)
SELECT * FROM distinct_events
QUALIFY COUNT(*) OVER (PARTITION BY event_id) = 1;
