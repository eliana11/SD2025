FROM python:3.10-slim

# Dependencias necesarias para OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY . .

# CMD que permite pasar argumentos desde docker-compose
ENTRYPOINT ["python", "coordinador.py"]
