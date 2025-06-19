# Usamos una imagen base oficial de Python
FROM python:3.11-slim

# Establecemos el directorio de trabajo en el contenedor
WORKDIR /app

# Copiamos el script al contenedor
COPY coordinador.py .

# Instalamos la librería pika para RabbitMQ
RUN pip install --no-cache-dir pika

# Comando para ejecutar el script cuando se inicie el contenedor
CMD ["python", "coordinador.py"]
