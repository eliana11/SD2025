resource "google_compute_firewall" "allow-gke-to-vms" {
  name    = "allow-gke-to-vms"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["5672", "15672", "6379"]  # Puertos para RabbitMQ y Redis
  }

  source_tags = ["gke-node"]

  target_tags = ["worker"]

  description = "Permite el tráfico entre el clúster GKE y las VMs externas para Redis y RabbitMQ"
}
