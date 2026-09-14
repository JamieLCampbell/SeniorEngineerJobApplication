terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "8.2.0"
    }
  }
  backend "gcs" {
    prefix = "orders/dev"
  }
}

provider "google" {
  project = var.project_id
  region  = var.location
}

module "orders" {
  source              = "../../modules/orders"
  project_id          = var.project_id
  environment         = "dev"
  location            = var.location
  file_retention_days = var.file_retention_days
}

variable "project_id" {
  type        = string
  description = "Existing dedicated dev project; do not reuse another environment's project."
}

variable "location" {
  type    = string
  default = "europe-west2"
}

variable "file_retention_days" {
  type        = number
  description = "Explicit retention policy; production must be agreed before apply."
}

output "resources" {
  value = module.orders
}
