variable "cdc_ready" {
  type    = bool
  default = false
}
variable "source_ca" {
  type    = string
  default = ""
}
resource "google_datastream_connection_profile" "source" {
  count                 = var.cdc_ready ? 1 : 0
  location              = var.region
  connection_profile_id = "assessment-postgres"
  display_name          = "Assessment PostgreSQL"
  postgresql_profile {
    hostname                       = google_sql_database_instance.source.public_ip_address
    port                           = 5432
    username                       = "datastream"
    database                       = "shop"
    secret_manager_stored_password = "projects/${var.project_id}/secrets/assessment-cdc-password/versions/latest"
    ssl_config {
      server_verification { ca_certificate = var.source_ca }
    }
  }
}
resource "google_datastream_connection_profile" "destination" {
  count                 = var.cdc_ready ? 1 : 0
  location              = var.region
  connection_profile_id = "assessment-bigquery"
  display_name          = "Assessment BigQuery"
  bigquery_profile {}
}
resource "google_datastream_stream" "orders" {
  count         = var.cdc_ready ? 1 : 0
  location      = var.region
  stream_id     = "assessment-orders"
  display_name  = "Assessment order changes"
  desired_state = "RUNNING"
  source_config {
    source_connection_profile = google_datastream_connection_profile.source[0].id
    postgresql_source_config {
      publication      = "assessment_publication"
      replication_slot = "assessment_slot"
      include_objects {
        postgresql_schemas {
          schema = "public"
          postgresql_tables { table = "orders" }
        }
      }
    }
  }
  destination_config {
    destination_connection_profile = google_datastream_connection_profile.destination[0].id
    bigquery_destination_config {
      single_target_dataset { dataset_id = "${var.project_id}:${google_bigquery_dataset.cdc.dataset_id}" }
      data_freshness = "60s"
      merge {}
    }
  }
  backfill_all {}
}
