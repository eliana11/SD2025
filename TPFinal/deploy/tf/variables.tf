variable "project_id" {
  description = "ID del proyecto en Google Cloud"
  type        = string
}

variable "region" {
  description = "Región donde se creará el clúster"
  type        = string
  default     = "us-central1"
}
