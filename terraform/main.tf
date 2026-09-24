terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Dedicated Least-Privilege Service Account for CartCompass UK Agent
resource "google_service_account" "cartcompass_agent_sa" {
  account_id   = "cartcompass-uk-agent-sa"
  display_name = "CartCompass UK Multi-Agent Service Account"
  description  = "Identity for Cloud Run CartCompass UK 20km Grocery & Loyalty Optimizer"
}

# 2. Google Cloud Secret Manager Secrets (No Hardcoded API Keys)
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "retailer_catalog_api_key" {
  secret_id = "RETAILER_CATALOG_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "agent_gemini_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cartcompass_agent_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "agent_catalog_secret_access" {
  secret_id = google_secret_manager_secret.retailer_catalog_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cartcompass_agent_sa.email}"
}

# 3. Artifact Registry Repository for Container Images
resource "google_artifact_registry_repository" "cartcompass_repo" {
  location      = var.region
  repository_id = "cartcompass-repo"
  description   = "Container registry for CartCompass UK Agent"
  format        = "DOCKER"
}

# 4. Google Cloud Run v2 Service Hosting the Multi-Agent Application
resource "google_cloud_run_v2_service" "cartcompass_service" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cartcompass_agent_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8765
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "USE_GCP_SECRET_MANAGER"
        value = "1"
      }

      env {
        name  = "DEFAULT_UK_POSTCODE"
        value = "PO20 3SJ"
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "RETAILER_CATALOG_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.retailer_catalog_api_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }
  }
}
