variable "project_id" {
  type        = string
  default     = "the-program-457617-r1"
}

variable "zone" {
  default = "us-central1-a"
}

variable "instance_tipe"{
  type = string
  default = "e2-standard-2"
}

variable "instance_name" {
  type    = string
  default = "e2-standard-2"
}

variable "credentials_file_path" {
  description = "Path to GCP service account credentials file"
  default     = "./terraform-sa-key.json"
}

variable "instance_count" {
  type    = number
  default = 3
}