terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = { source = "hashicorp/google", version = "8.2.0" }
  }
  backend "gcs" { prefix = "platform-demo/dev" }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
variable "project_id" { type = string }
variable "region" { default = "europe-west2" }
variable "composer_image" { type = string }
variable "datastream_ips" { type = list(string) }
data "google_project" "current" { project_id = var.project_id }
locals {
  labels   = { application = "orders-assessment", environment = "dev", purpose = "temporary-platform-demo" }
  accounts = toset(["collector", "dataflow", "composer", "builder"])
}
resource "google_service_account" "runtime" {
  for_each     = local.accounts
  account_id   = "demo-${each.key}"
  display_name = "Temporary assessment ${each.key}"
}
resource "google_project_iam_member" "runtime" {
  for_each = { dataflow = "roles/dataflow.worker", composer = "roles/composer.worker", builder = "roles/logging.logWriter" }
  project  = var.project_id
  role     = each.value
  member   = google_service_account.runtime[each.key].member
}
resource "google_project_iam_member" "query" {
  for_each = toset(["composer", "dataflow"])
  project  = var.project_id
  role     = "roles/bigquery.jobUser"
  member   = google_service_account.runtime[each.key].member
}
resource "google_storage_bucket" "demo" {
  name                        = "${var.project_id}-platform-demo"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # Only synthetic, disposable demo artifacts in this bucket.
  labels                      = local.labels
  soft_delete_policy { retention_duration_seconds = 0 }
  lifecycle_rule {
    condition { age = 1 }
    action { type = "Delete" }
  }
}
resource "google_storage_bucket_iam_member" "runtime" {
  for_each = { dataflow = "roles/storage.objectAdmin", composer = "roles/storage.objectViewer", builder = "roles/storage.objectViewer" }
  bucket   = google_storage_bucket.demo.name
  role     = each.value
  member   = google_service_account.runtime[each.key].member
}
resource "google_storage_bucket_iam_member" "batch" {
  bucket = google_storage_bucket.demo.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:orders-loader-dev@${var.project_id}.iam.gserviceaccount.com"
}
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "assessment-demo"
  format        = "DOCKER"
  labels        = local.labels
}
resource "google_artifact_registry_repository_iam_member" "build" {
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.runtime["builder"].member
}
resource "google_bigquery_dataset" "demo" {
  dataset_id                 = "platform_demo"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                     = local.labels
}
resource "google_bigquery_dataset" "cdc" {
  dataset_id                 = "platform_cdc"
  location                   = var.region
  delete_contents_on_destroy = true
  labels                     = local.labels
}
resource "google_bigquery_dataset_iam_member" "runtime" {
  for_each   = toset(["composer", "dataflow"])
  dataset_id = google_bigquery_dataset.demo.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.runtime[each.key].member
}
resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = "events"
  deletion_protection = false
  schema              = jsonencode([for field in ["event_id", "customer_id", "event_type", "event_time"] : { name = field, type = "STRING", mode = "REQUIRED" }])
}
resource "google_pubsub_topic" "events" {
  name = "assessment-demo-events"
  message_storage_policy { allowed_persistence_regions = [var.region] }
  labels = local.labels
}
resource "google_pubsub_subscription" "processing" {
  name                       = "assessment-demo-processing"
  topic                      = google_pubsub_topic.events.id
  ack_deadline_seconds       = 60
  message_retention_duration = "3600s"
}
resource "google_pubsub_topic_iam_member" "collector" {
  topic  = google_pubsub_topic.events.name
  role   = "roles/pubsub.publisher"
  member = google_service_account.runtime["collector"].member
}
resource "google_pubsub_subscription_iam_member" "worker" {
  subscription = google_pubsub_subscription.processing.name
  role         = "roles/pubsub.subscriber"
  member       = google_service_account.runtime["dataflow"].member
}
resource "google_storage_bucket_iam_member" "archive" {
  bucket = google_storage_bucket.demo.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_storage_bucket_iam_member" "archive_metadata" {
  bucket = google_storage_bucket.demo.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_subscription" "archive" {
  name  = "assessment-demo-archive"
  topic = google_pubsub_topic.events.id
  cloud_storage_config {
    bucket          = google_storage_bucket.demo.name
    filename_prefix = "events/"
    max_duration    = "60s"
    avro_config { write_metadata = true }
  }
  depends_on = [google_storage_bucket_iam_member.archive, google_storage_bucket_iam_member.archive_metadata]
}
resource "google_compute_network" "demo" {
  name                    = "assessment-demo"
  auto_create_subnetworks = false
}
resource "google_compute_subnetwork" "demo" {
  name                     = "assessment-demo"
  region                   = var.region
  network                  = google_compute_network.demo.id
  ip_cidr_range            = "10.22.0.0/24"
  private_ip_google_access = true
}
resource "google_compute_firewall" "workers" {
  name          = "assessment-demo-workers"
  network       = google_compute_network.demo.name
  source_ranges = ["10.22.0.0/24"]
  target_tags   = ["dataflow"]
  allow {
    protocol = "tcp"
    ports    = ["12345", "12346"]
  }
}
resource "google_sql_database_instance" "source" {
  name                = "assessment-source-dev"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = false
  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"
    disk_size         = 10
    disk_autoresize   = false
    availability_type = "ZONAL"
    database_flags {
      name  = "cloudsql.logical_decoding"
      value = "on"
    }
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
      dynamic "authorized_networks" {
        for_each = toset(var.datastream_ips)
        content {
          name  = "datastream-${replace(authorized_networks.value, ".", "-")}"
          value = "${authorized_networks.value}/32"
        }
      }
    }
    backup_configuration { enabled = false }
    user_labels = local.labels
  }
}
resource "google_sql_database" "shop" {
  name     = "shop"
  instance = google_sql_database_instance.source.name
}
resource "google_storage_bucket_iam_member" "sql_import" {
  bucket = google_storage_bucket.demo.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_sql_database_instance.source.service_account_email_address}"
}
resource "google_composer_environment" "demo" {
  name   = "assessment-orchestrator-dev"
  region = var.region
  labels = local.labels
  config {
    environment_size = "ENVIRONMENT_SIZE_SMALL"
    node_config { service_account = google_service_account.runtime["composer"].email }
    software_config { image_version = var.composer_image }
    workloads_config {
      scheduler {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }
      dag_processor {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }
      web_server {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
      }
      worker {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        min_count  = 1
        max_count  = 1
      }
    }
  }
  depends_on = [google_project_iam_member.runtime]
}
output "bucket" { value = google_storage_bucket.demo.name }
output "source_ip" { value = google_sql_database_instance.source.public_ip_address }
output "dag_prefix" { value = google_composer_environment.demo.config[0].dag_gcs_prefix }
