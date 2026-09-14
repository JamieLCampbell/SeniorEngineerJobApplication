variable "project_id" {
  type        = string
  description = "Existing, billing-enabled GCP project for this environment."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Supply an actual GCP project ID (6–30 lowercase letters, digits or hyphens)."
  }
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "pre", "prod"], var.environment)
    error_message = "Environment must be dev, pre, or prod."
  }
}

variable "location" {
  type        = string
  description = "A location supported by both Cloud Storage and BigQuery; identical for both."
  default     = "europe-west2"
}

variable "file_retention_days" {
  type        = number
  description = "Agreed age at which uploaded files become eligible for lifecycle deletion."
  validation {
    condition     = var.file_retention_days >= 1 && floor(var.file_retention_days) == var.file_retention_days
    error_message = "Set a positive whole number of retention days."
  }
}
