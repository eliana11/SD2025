resource "google_compute_instance" "minero_gpu" {
  name         = "minero-gpu"
  machine_type = "n1-standard-2"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 20
    }
  }

  network_interface {
    network       = "default"
    access_config {}  # para tener IP pública
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y build-essential git wget curl

    # Instalar CUDA si es necesario...
    # wget https://developer.download.nvidia.com/...

    git clone https://github.com/usuario/minero-gpu.git /opt/minero
    cd /opt/minero
    make
    ./minero --coordinador http://IP_DEL_COORDINADOR:PORT
  EOT

  tags = ["minero"]

  labels = {
    tipo = "gpu"
  }

  scheduling {
    on_host_maintenance = "TERMINATE"
    automatic_restart   = true
    preemptible         = false
  }

  service_account {
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}
