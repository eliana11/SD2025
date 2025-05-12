import cv2
import numpy as np
import base64
import json
import pika
import redis
import os
import time

def sobel(imagen):
    print("Aplicando filtro Sobel...")
    sobelx = cv2.Sobel(imagen, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(imagen, cv2.CV_64F, 0, 1, ksize=3)
    magnitud = cv2.magnitude(sobelx, sobely)
    resultado = cv2.convertScaleAbs(magnitud)
    print("Filtro Sobel aplicado correctamente.")
    return resultado

def procesar_tarea(ch, method, properties, body):
    print("Mensaje recibido de RabbitMQ.")
    tarea = json.loads(body)
    chunk_id = tarea["chunk_id"]
    b64_img = tarea["imagen"]

    print(f"Procesando chunk ID: {chunk_id}")

    try:
        # Decodificar imagen
        print("Decodificando imagen desde base64...")
        imagen_bytes = base64.b64decode(b64_img)
        np_arr = np.frombuffer(imagen_bytes, np.uint8)
        imagen = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
        print("Imagen decodificada correctamente.")
    except Exception as e:
        print(f"Error al decodificar imagen: {e}")
        return

    try:
        # Aplicar Sobel
        resultado = sobel(imagen)
    except Exception as e:
        print(f"Error al aplicar filtro Sobel: {e}")
        return

    try:
        print("Codificando resultado a base64...")
        _, buffer = cv2.imencode('.jpg', resultado)
        b64_resultado = base64.b64encode(buffer)
        print("Codificación exitosa.")
    except Exception as e:
        print(f"Error al codificar imagen: {e}")
        return

    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        print(f"Conectando a Redis en: {redis_host}")
        r = redis.Redis(host=redis_host, port=6379)
        r.set(f"resultado:{chunk_id}", b64_resultado)
        print(f"Resultado guardado en Redis para chunk {chunk_id}")
    except Exception as e:
        print(f"Error al guardar en Redis: {e}")

def conectar_rabbitmq(reintentos=5, espera=10):
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    print(f"[DEBUG] Variable de entorno RABBITMQ_HOST = {rabbitmq_host}")
    print("[DEBUG] Intentando conectar a RabbitMQ...")

    for i in range(reintentos):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=rabbitmq_host,
                port=5672,
                credentials=pika.PlainCredentials("guest", "guest")))
            print("✅ Conectado a RabbitMQ")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ Intento {i+1} de {reintentos}: RabbitMQ no disponible, esperando {espera}s...")
            print(f"🔍 Error: {e}")
            time.sleep(espera)

    raise Exception("❌ No se pudo conectar a RabbitMQ luego de varios intentos.")

def main():
    print("⏳ Iniciando worker...")
    print(f"[DEBUG] REDIS_HOST = {os.getenv('REDIS_HOST', 'localhost')}")
    print(f"[DEBUG] RABBITMQ_HOST = {os.getenv('RABBITMQ_HOST', 'localhost')}")
    
    connection = conectar_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue='tareas')

    print("📡 Esperando tareas de RabbitMQ...")
    channel.basic_consume(queue='tareas', on_message_callback=procesar_tarea, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    main()
