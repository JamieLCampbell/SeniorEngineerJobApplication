mock_provider "google" {}

variables {
  project_id          = "assessment-test-project"
  environment         = "dev"
  file_retention_days = 7
}

run "dev_is_disposable_but_not_public" {
  command = plan
  assert {
    condition     = google_storage_bucket.orders.public_access_prevention == "enforced" && google_storage_bucket.orders.uniform_bucket_level_access && !google_storage_bucket.orders.force_destroy
    error_message = "Development must remain private and must not force-delete data."
  }
  assert {
    condition     = !google_bigquery_table.cleaned_orders.deletion_protection && google_bigquery_dataset.orders.location == google_storage_bucket.orders.location
    error_message = "Dev must use compatible locations and allow deliberate table replacement."
  }
}

run "pre_matches_production_guards" {
  command = plan
  variables {
    environment         = "pre"
    file_retention_days = 14
  }
  assert {
    condition     = google_bigquery_table.cleaned_orders.deletion_protection && google_storage_bucket.orders.deletion_policy == "PREVENT" && google_bigquery_dataset.orders.dataset_id == "orders_pre"
    error_message = "Pre must exercise the production deletion guards with its own resource names."
  }
}

run "production_is_protected" {
  command = plan
  variables {
    environment         = "prod"
    file_retention_days = 90
  }
  assert {
    condition     = google_bigquery_table.cleaned_orders.deletion_protection && google_storage_bucket.orders.deletion_policy == "PREVENT" && !google_bigquery_dataset.orders.delete_contents_on_destroy
    error_message = "Production data must not be silently removed by Terraform destroy."
  }
  assert {
    condition     = google_storage_bucket.orders.name == "assessment-test-project-orders-prod" && google_service_account.loader.account_id == "orders-loader-prod"
    error_message = "Production resources must have environment-specific names."
  }
}

run "reject_unknown_environment" {
  command = plan
  variables { environment = "production-typo" }
  expect_failures = [var.environment]
}

run "reject_zero_retention" {
  command = plan
  variables { file_retention_days = 0 }
  expect_failures = [var.file_retention_days]
}
