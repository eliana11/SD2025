resource "google_container_cluster" "cluster-sd" {
  name     = "cluster-sd"
  location = var.zone

  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
}

# Nodepool 1: infra

resource "google_container_node_pool" "infra" {
  name     = "infra-node-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster-sd.name

  node_config {
    machine_type = "e2-small"
    disk_type    = "pd-standard"
    disk_size_gb = 12
    labels = {
      role = "infra"
    }
    tags = ["gke-node"]  # Etiqueta para los nodos de GKE
  }

  initial_node_count = 1
}

# Nodepool 2: aplicaciones

resource "google_container_node_pool" "app" {
  name       = "app-nodepool"
  cluster    = google_container_cluster.cluster-sd.name
  location   = var.zone

  node_config {
    machine_type = "e2-small"
    disk_type    = "pd-standard"
    disk_size_gb = 12
    labels = {
      role = "app"
    }
    tags = ["gke-node"]  # Etiqueta para los nodos de GKE
  }

  initial_node_count = 2
}

output "cluster_endpoint" {
  value = google_container_cluster.cluster-sd.endpoint
}

output "cluster_ca_certificate" {
  value = google_container_cluster.cluster-sd.master_auth[0].cluster_ca_certificate
}