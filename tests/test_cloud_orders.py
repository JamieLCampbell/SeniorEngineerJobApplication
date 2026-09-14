"""Cloud request contracts; live service evidence is recorded separately."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from orders.cloud import MAXIMUM_BYTES_BILLED, load_orders, run_pipeline, run_query, upload_accepted
    CLOUD_AVAILABLE = True
except ModuleNotFoundError as error:
    if not error.name.startswith("google"):
        raise
    CLOUD_AVAILABLE = False


@unittest.skipUnless(CLOUD_AVAILABLE, "Install requirements-cloud.txt for cloud request tests")
class CloudOrdersTests(unittest.TestCase):
    def test_upload_is_only_the_accepted_file_and_cannot_overwrite(self):
        client = Mock()
        blob = client.bucket.return_value.blob.return_value
        blob.name = "accepted/run123/cleaned_orders.csv"
        uri = upload_accepted(client, "test-bucket", Path("cleaned_orders.csv"), "run123")
        self.assertEqual(uri, "gs://test-bucket/accepted/run123/cleaned_orders.csv")
        blob.upload_from_filename.assert_called_once_with(
            "cleaned_orders.csv", content_type="text/csv", if_generation_match=0, timeout=60,
        )

    def test_load_replaces_snapshot_and_refuses_bad_rows_or_new_tables(self):
        client = Mock()
        load_orders(client, "gs://test/accepted.csv", "project.orders_dev.cleaned_orders", [])
        config = client.load_table_from_uri.call_args.kwargs["job_config"]
        self.assertEqual(config.write_disposition, "WRITE_TRUNCATE")
        self.assertEqual(config.create_disposition, "CREATE_NEVER")
        self.assertEqual(config.max_bad_records, 0)
        self.assertFalse(config.autodetect)
        self.assertFalse(config.ignore_unknown_values)
        self.assertEqual(config.skip_leading_rows, 1)
        client.load_table_from_uri.return_value.result.assert_called_once_with(timeout=120)

    def test_expensive_query_is_not_executed(self):
        client = Mock()
        client.query.return_value.total_bytes_processed = MAXIMUM_BYTES_BILLED + 1
        with self.assertRaisesRegex(ValueError, "scan limit"):
            run_query(client, "SELECT 1")
        self.assertEqual(client.query.call_count, 1)
        self.assertTrue(client.query.call_args.kwargs["job_config"].dry_run)

    def test_execution_also_has_server_side_limit(self):
        preview = Mock(total_bytes_processed=1)
        job = Mock(job_id="job", total_bytes_processed=1, total_bytes_billed=10)
        job.result.return_value = [{"value": 1}]
        client = Mock()
        client.query.side_effect = [preview, job]
        rows, details = run_query(client, "SELECT 1 AS value")
        self.assertEqual(rows, [{"value": 1}])
        config = client.query.call_args.kwargs["job_config"]
        self.assertEqual(config.maximum_bytes_billed, MAXIMUM_BYTES_BILLED)
        self.assertFalse(config.use_query_cache)
        self.assertEqual(details["bytes_billed"], 10)

    def test_all_rejected_batch_does_not_touch_cloud(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.csv"
            source.write_text("OrderID,CustomerID,OrderRegion,OrderDate,OrderAmount,ProductID,Quantity\n1,1,London,INVALID,10,1,1\n")
            with patch("orders.cloud.credentials_for") as auth:
                with self.assertRaisesRegex(ValueError, "No accepted orders"):
                    run_pipeline(source, Path(directory) / "run", "test-project", "europe-west2")
                auth.assert_not_called()
            self.assertTrue((Path(directory) / "run/rejected.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
