output "cloud_run_service_uri" {
  description = "Public HTTPS endpoint of the deployed CartCompass UK Cloud Run service"
  value       = google_cloud_run_v2_service.cartcompass_service.uri
}

output "service_account_email" {
  description = "Email of the least-privilege CartCompass UK runtime Service Account"
  value       = google_service_account.cartcompass_agent_sa.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository ID"
  value       = google_artifact_registry_repository.cartcompass_repo.id
}
