resource "google_compute_instance" "worker1" {
  name         = "worker-1"
  machine_type = "e2-small"
  zone         = var.zone
  tags         = ["worker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  metadata_startup_script = file("${path.module}/startup.sh")

  network_interface {
    network = "default"
    access_config {}
  }
}

resource "google_compute_instance" "worker2" {
  name         = "worker-2"
  machine_type = "e2-small"
  zone         = var.zone
  tags         = ["worker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  metadata_startup_script = file("${path.module}/startup.sh")

  network_interface {
    network = "default"
    access_config {}
  }
}

resource "google_compute_instance" "worker3" {
  name         = "worker-3"
  machine_type = "e2-small"
  zone         = var.zone
  tags         = ["worker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  metadata_startup_script = file("${path.module}/startup.sh")

  network_interface {
    network = "default"
    access_config {}
  }
}
