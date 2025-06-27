terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.6.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_container_cluster" "blockchain_cluster" {
  name     = "blockchain-cluster"
  location = var.region

  remove_default_node_pool = true
  initial_node_count       = 1

  networking_mode = "VPC_NATIVE"

  ip_allocation_policy {}
}

# 🟦 Infraestructura (Redis, RabbitMQ, etc.)
resource "google_container_node_pool" "infra_pool" {
  name     = "infra-pool"
  cluster  = google_container_cluster.blockchain_cluster.name
  location = var.region

  initial_node_count = 1  # Reducido para evitar errores de cuota

  node_config {
    machine_type   = "e2-small"
    disk_type      = "pd-standard"
    disk_size_gb   = 20  # Seguro con cuentas de prueba
    image_type     = "COS_CONTAINERD"  # Imagen base oficial y ligera
    oauth_scopes   = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    labels = {
      tipo = "infraestructura"
    }
  }
}

# 🟩 Aplicaciones (coordinador, frontend, mineros, etc.)
resource "google_container_node_pool" "app_pool" {
  name     = "app-pool"
  cluster  = google_container_cluster.blockchain_cluster.name
  location = var.region

  initial_node_count = 1  # Reducido también para asegurar disponibilidad

  node_config {
    machine_type   = "e2-medium"
    disk_type      = "pd-standard"
    disk_size_gb   = 20
    image_type     = "COS_CONTAINERD"
    oauth_scopes   = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    labels = {
      tipo = "aplicaciones"
    }
  }
}
