#!/bin/bash

# Pipeline 1 - Despliegue de clúster GKE y configuración de kubectl
set -euo pipefail

# Variables
CLUSTER_NAME="cluster-sd"
ZONE="us-central1-a"
PROJECT="sistemas-distribuidos-388122"
GKE_DIR="../cloud/gke/"

echo "🔧 Iniciando pipeline para crear el clúster GKE..."

# Ir al directorio donde están los archivos de Terraform
cd "$GKE_DIR" || { echo "❌ No se pudo acceder a $GKE_DIR"; exit 1; }

echo "📦 Inicializando Terraform..."
terraform init

echo "🚀 Aplicando Terraform (esto puede tardar unos minutos)..."
terraform apply -auto-approve

echo "🔑 Obteniendo credenciales para kubectl..."
gcloud container clusters get-credentials "$CLUSTER_NAME" --zone "$ZONE" --project "$PROJECT"

echo "✅ Clúster desplegado y configurado correctamente para kubectl."
