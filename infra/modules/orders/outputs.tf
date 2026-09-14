output "bucket_name" {
  value = google_storage_bucket.orders.name
}

output "table_id" {
  value = "${var.project_id}.${google_bigquery_dataset.orders.dataset_id}.${google_bigquery_table.cleaned_orders.table_id}"
}

output "loader_service_account" {
  value = google_service_account.loader.email
}
