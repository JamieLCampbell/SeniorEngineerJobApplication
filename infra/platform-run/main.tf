terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers { google = { source = "hashicorp/google", version = "8.2.0" } }
  backend "gcs" { prefix = "platform-demo/run" }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
variable "project_id" { type = string }
variable "region" { default = "europe-west2" }
variable "image" { type = string }
resource "google_cloud_run_v2_job" "batch" {
  count               = var.image == "" ? 0 : 1
  name                = "assessment-orders-cloud"
  location            = var.region
  deletion_protection = false
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = "orders-loader-dev@${var.project_id}.iam.gserviceaccount.com"
      timeout         = "600s"
      max_retries     = 0
      containers {
        image = var.image
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "DEMO_BUCKET"
          value = "${var.project_id}-platform-demo"
        }
        resources { limits = { cpu = "1", memory = "512Mi" } }
      }
    }
  }
}
resource "google_cloud_run_v2_job_iam_member" "composer" {
  count    = var.image == "" ? 0 : 1
  name     = google_cloud_run_v2_job.batch[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:demo-composer@${var.project_id}.iam.gserviceaccount.com"
}
variable "status_access_expires" { type = string }
resource "google_project_iam_custom_role" "run_status" {
  project     = var.project_id
  role_id     = "assessmentRunStatus"
  title       = "Read assessment job completion"
  permissions = ["run.operations.get"]
}
resource "google_project_iam_member" "composer_run_status" {
  project = var.project_id
  role    = google_project_iam_custom_role.run_status.name
  member  = "serviceAccount:demo-composer@${var.project_id}.iam.gserviceaccount.com"
  # Operation polling is authorised at project level. Limit this to one read
  # permission with an expiry; job metadata access is bound to the job below.
  condition {
    title      = "assessment_status_only"
    expression = "request.time < timestamp('${var.status_access_expires}')"
  }
}
resource "google_cloud_run_v2_job_iam_member" "composer_status" {
  count    = var.image == "" ? 0 : 1
  name     = google_cloud_run_v2_job.batch[0].name
  location = var.region
  role     = "roles/run.viewer"
  member   = "serviceAccount:demo-composer@${var.project_id}.iam.gserviceaccount.com"
}
resource "google_cloud_run_v2_service" "collector" {
  count               = var.image == "" ? 0 : 1
  name                = "assessment-collector"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = "demo-collector@${var.project_id}.iam.gserviceaccount.com"
    timeout                          = "60s"
    max_instance_request_concurrency = 1
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image   = var.image
      command = ["python", "-m", "demo.collector"]
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
    }
  }
}
output "collector_url" {
  value = var.image == "" ? "" : google_cloud_run_v2_service.collector[0].uri
}
