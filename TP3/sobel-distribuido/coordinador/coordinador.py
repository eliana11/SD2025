import cv2
import numpy as np
import sys
import os
import time
import pika
import base64
import json
import redis

def dividir_imagen(imagen, n):
    alto = imagen.shape[0]
    partes = []
    paso = alto // n
    for i in range(n):
        inicio = i * paso
        fin = (i + 1) * paso if i != n - 1 else alto
        partes.append(imagen[inicio:fin])
    return partes

def unir_imagenes(partes):
    return np.vstack(partes)

def conectar_rabbitmq(reintentos=5, espera=5):
    for i in range(reintentos):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='rabbitmq',
                port=5672,
                credentials=pika.PlainCredentials("guest", "guest")))
            print("Conectado a RabbitMQ")
            return connection
        except pika.exceptions.AMQPConnectionError:
            print(f"Intento {i+1} de {reintentos}: RabbitMQ no disponible, esperando {espera}s...")
            time.sleep(espera)
    raise Exception("No se pudo conectar a RabbitMQ luego de varios intentos.")

def enviar_tareas(partes):
    connection = conectar_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue='tareas')

    for idx, parte in enumerate(partes):
        _, buffer = cv2.imencode('.jpg', parte)
        b64_img = base64.b64encode(buffer).decode('utf-8')

        tarea = {
            'chunk_id': idx,
            'imagen': b64_img
        }
        channel.basic_publish(
            exchange='',
            routing_key='tareas',
            body=json.dumps(tarea)
        )
    connection.close()

def esperar_resultados_redis(n):
    r = redis.Redis(host='redis', port=6379)
    partes_procesadas = []

    for i in range(n):
        key = f"resultado:{i}"
        while not r.exists(key):
            time.sleep(0.5)
        b64 = r.get(key)
        img_bytes = base64.b64decode(b64)
        parte = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        partes_procesadas.append(parte)

    return partes_procesadas

def main():
    if len(sys.argv) < 3:
        print("Uso: python coordinador.py <input> <output>")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    n = 4  # o el número de workers que tengas

    img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    partes = dividir_imagen(img, n)
    enviar_tareas(partes)
    print("Tareas enviadas. Esperando resultados...")

    partes_filtradas = esperar_resultados_redis(n)
    resultado = unir_imagenes(partes_filtradas)
    cv2.imwrite(output_path, resultado)
    print(f"Imagen final guardada como {output_path}")

if __name__ == "__main__":
    main()
