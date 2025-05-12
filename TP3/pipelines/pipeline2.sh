#!/bin/bash

# Pipeline para levantar las VMs externas (workers) que procesarán las imágenes aplicando el filtro de Sobel.
# IMPORTANTE: Antes de ejecutar este script, asegurarse de haber actualizado las IPs en workers/startup.sh

set -euo pipefail

WORKER_DIR="../cloud/workers"

echo "🚀 Desplegando workers..."

# Validar que el directorio existe
if [ ! -d "$WORKER_DIR" ]; then
  echo "❌ El directorio $WORKER_DIR no existe. Abortando."
  exit 1
fi

cd "$WORKER_DIR"

echo "📦 Inicializando Terraform..."
terraform init

echo "🛠 Aplicando configuración de Terraform para workers..."
terraform apply -auto-approve

echo ""
echo "⚠️  ATENCIÓN:"
echo "Verificá que el archivo 'startup.sh' en el directorio 'workers/' tenga las IPs correctas de Redis y RabbitMQ:"
echo ""
echo "  Línea 28-29 debe contener algo como:"
echo "    -e REDIS_HOST=<IP_DE_SERVICIO_REDIS>"
echo "    -e RABBITMQ_HOST=<IP_DE_SERVICIO_RABBITMQ>"
echo ""
echo "Usá este comando para obtenerlas:"
echo ""
echo "  kubectl get svc"
echo ""
echo "🔁 Si modificás el startup.sh, deberás volver a destruir y crear las VMs para que tomen los cambios."
echo ""

echo "✅ Workers desplegados correctamente (si el startup.sh fue configurado bien)."
