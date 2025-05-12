#!/bin/bash

# Pipeline para aplicar reglas de firewall necesarias para la comunicación entre el clúster y las VMs externas (workers)
set -euo pipefail

FIREWALL_DIR="../cloud/firewalls"

echo "🚀 Iniciando configuración de reglas de firewall..."

# Validar que el directorio existe
if [ ! -d "$FIREWALL_DIR" ]; then
  echo "❌ El directorio $FIREWALL_DIR no existe. Abortando."
  exit 1
fi

# Cambiar al directorio
cd "$FIREWALL_DIR"

echo "📦 Inicializando Terraform..."
terraform init

echo "🛠 Aplicando configuración..."
terraform apply -auto-approve

echo "✅ Reglas de firewall aplicadas correctamente."
