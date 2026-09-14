terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 8.2, < 9.0"
    }
  }
}

locals {
  labels = {
    environment = var.environment
    application = "orders-assessment"
    managed_by  = "terraform"
  }
}

resource "google_project_service" "required" {
  for_each           = toset(["storage.googleapis.com", "bigquery.googleapis.com", "iam.googleapis.com"])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "orders" {
  project                     = var.project_id
  name                        = "${var.project_id}-orders-${var.environment}"
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  deletion_policy             = var.environment == "dev" ? "DELETE" : "PREVENT"
  labels                      = local.labels

  # This is an explicit input: production retention is a business decision.
  lifecycle_rule {
    condition {
      age = var.file_retention_days
    }
    action {
      type = "Delete"
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  depends_on = [google_project_service.required]
}

resource "google_bigquery_dataset" "orders" {
  project                    = var.project_id
  dataset_id                 = "orders_${var.environment}"
  location                   = var.location
  description                = "Assessment orders for ${var.environment}; raw access is separate from reporting access."
  delete_contents_on_destroy = false
  labels                     = local.labels
  depends_on                 = [google_project_service.required]
}

resource "google_bigquery_table" "cleaned_orders" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.orders.dataset_id
  table_id            = "cleaned_orders"
  deletion_protection = var.environment != "dev"
  labels              = local.labels
  schema              = file("${path.module}/orders-schema.json")

  # Keep this small table unpartitioned. Add partitioning when volume and
  # date-filtered queries justify it; changing it later needs migration review.
}

resource "google_service_account" "loader" {
  project      = var.project_id
  account_id   = "orders-loader-${var.environment}"
  display_name = "Orders batch loader (${var.environment})"
  depends_on   = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "loader" {
  bucket = google_storage_bucket.orders.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_bigquery_dataset_iam_member" "loader" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.orders.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_project_iam_member" "loader_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.loader.email}"
}
