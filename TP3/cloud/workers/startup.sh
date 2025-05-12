#!/bin/bash
# Redireccionar salida a log para debug
exec > /var/log/startup-script.log 2>&1
set -e

# Actualizar e instalar dependencias
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Agregar clave GPG de Docker y repositorio
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

# Instalar Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Habilitar e iniciar Docker
systemctl enable docker
systemctl start docker

# Ejecutar contenedor del worker
docker run -d \
  --name worker \
  -e REDIS_HOST=34.56.128.142 \
  -e RABBITMQ_HOST=35.238.6.47 \
  --restart always \
  bautista222221/worker:latest
