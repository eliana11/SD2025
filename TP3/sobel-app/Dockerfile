# Imagen base de Python
FROM python:3.10-slim

# Instala dependencias necesarias del sistema
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sobel.py .

# Comando por defecto (puede ser override con args)
ENTRYPOINT ["python", "sobel.py"]
