FROM python:3.11-slim

WORKDIR /app

# Copiamos los archivos necesarios
COPY coordinador.py .
COPY requirements.txt .

# Instalamos dependencias desde requirements
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "coordinador.py"]
