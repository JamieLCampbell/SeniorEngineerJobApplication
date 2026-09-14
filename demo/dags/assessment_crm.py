"""Manual synthetic CRM snapshot DAG; never scheduled after the demonstration."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.cloud_run import CloudRunExecuteJobOperator
from google.cloud import storage, bigquery

PROJECT = "data-enginner-job-app"
BUCKET = PROJECT + "-platform-demo"
DATASET = PROJECT + ".platform_demo"


def export_ready():
    bucket = storage.Client(project=PROJECT).bucket(BUCKET)
    manifest = json.loads(bucket.blob("inputs/crm_manifest.json").download_as_text())
    rows = list(csv.DictReader(io.StringIO(bucket.blob("inputs/crm.csv").download_as_text())))
    if len(rows) != manifest["expected_rows"] or not rows:
        raise ValueError("Export completeness check failed")
    return manifest


def load_staging():
    client = bigquery.Client(project=PROJECT, location="europe-west2")
    config = bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField("CustomerID", "INTEGER"),
                bigquery.SchemaField("CustomerRegion", "STRING"),
                bigquery.SchemaField("SnapshotDate", "DATE")],
        source_format="CSV", skip_leading_rows=1, write_disposition="WRITE_TRUNCATE", max_bad_records=0,
    )
    job = client.load_table_from_uri("gs://" + BUCKET + "/inputs/crm.csv", DATASET + ".crm_staging", job_config=config)
    print("Load job:", job.job_id)
    job.result(timeout=120)


def validate_and_publish(ti):
    manifest = ti.xcom_pull(task_ids="export_ready")
    client = bigquery.Client(project=PROJECT, location="europe-west2")
    query = f"""
    ASSERT (SELECT COUNT(*) = @expected AND COUNT(*) = COUNT(DISTINCT CustomerID)
      AND COUNTIF(CustomerID IS NULL OR CustomerRegion IS NULL OR TRIM(CustomerRegion) = ''
        OR SnapshotDate IS NULL OR SnapshotDate != @snapshot) = 0
      FROM `{DATASET}.crm_staging`) AS 'Invalid or incomplete CRM snapshot';
    CREATE TABLE IF NOT EXISTS `{DATASET}.crm_current`
      AS SELECT * FROM `{DATASET}.crm_staging` WHERE FALSE;
    ASSERT (SELECT COALESCE(MAX(SnapshotDate), DATE '1900-01-01') <= @snapshot
      FROM `{DATASET}.crm_current`) AS 'Older snapshot must not replace newer data';
    CREATE OR REPLACE TABLE `{DATASET}.crm_current` AS SELECT * FROM `{DATASET}.crm_staging`;
    """
    # Four statements can each incur BigQuery's minimum billed scan. A 10 MiB
    # cap for the whole script stopped publication even for this three-row file.
    config = bigquery.QueryJobConfig(maximum_bytes_billed=40*1024*1024,
        query_parameters=[bigquery.ScalarQueryParameter("expected", "INT64", manifest["expected_rows"]),
                          bigquery.ScalarQueryParameter("snapshot", "DATE", manifest["snapshot_date"])])
    job = client.query(query, job_config=config)
    print("Publication job:", job.job_id)
    job.result(timeout=120)

with DAG("assessment_crm", start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
         schedule=None, catchup=False, max_active_runs=1,
         default_args={"retries": 0, "execution_timeout": timedelta(minutes=5)},
         tags=["assessment", "synthetic"]) as dag:
    ready = PythonOperator(task_id="export_ready", python_callable=export_ready)
    stage = PythonOperator(task_id="load_staging", python_callable=load_staging)
    publish = PythonOperator(task_id="validate_and_publish", python_callable=validate_and_publish)
    batch = CloudRunExecuteJobOperator(task_id="run_orders_batch", project_id=PROJECT,
        region="europe-west2", job_name="assessment-orders-cloud", deferrable=False,
        timeout_seconds=240)
    ready >> stage >> publish >> batch
