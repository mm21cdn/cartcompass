variable "project_id" {
  description = "Google Cloud Project ID for CartCompass UK deployment"
  type        = string
  default     = "cartcompass-uk-prod"
}

variable "region" {
  description = "GCP Region (London europe-west2 for UK low-latency)"
  type        = string
  default     = "europe-west2"
}

variable "service_name" {
  description = "Cloud Run v2 service name"
  type        = string
  default     = "cartcompass-uk-agent"
}

variable "container_image" {
  description = "Container image URI in Artifact Registry"
  type        = string
  default     = "europe-west2-docker.pkg.dev/cartcompass-uk-prod/cartcompass-repo/cartcompass-agent:latest"
}

variable "min_instances" {
  description = "Minimum warm Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum autoscaled Cloud Run instances"
  type        = number
  default     = 10
}
