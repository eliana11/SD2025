provider "google" {
  credentials = file("terraform-sa-key.json")
  project     = var.project_id
  region      = var.zone
}

resource "google_container_cluster" "primary" {
  name     = "simple-gke-cluster"
  location = var.zone

  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
  networking_mode          = "VPC_NATIVE" # habilita VPC nativa
}

resource "google_container_node_pool" "primary_nodes" {
  name     = "primary-node-pool"
  location = var.zone
  cluster  = google_container_cluster.primary.name

  node_config {
    machine_type = "e2-small"
    disk_type    = "pd-standard"
    disk_size_gb = 12
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }

  initial_node_count = 1

  autoscaling {
    min_node_count = 1
    max_node_count = 1
  }
}
