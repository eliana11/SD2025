#!/bin/bash

# Pipeline para desplegar servicios internos en el clúster GKE: Coordinador, Redis y RabbitMQ
set -euo pipefail

K8S_DIR="../cloud/k8s"

echo "🚀 Iniciando despliegue de servicios internos del clúster..."

# Validar que el directorio existe
if [ ! -d "$K8S_DIR" ]; then
  echo "❌ El directorio $K8S_DIR no existe. Abortando."
  exit 1
fi

# Cambiar al directorio donde están los manifiestos YAML
cd "$K8S_DIR"

echo "📦 Aplicando archivos YAML de Kubernetes..."
kubectl apply -f .

echo "✅ Servicios internos desplegados correctamente en el clúster."
