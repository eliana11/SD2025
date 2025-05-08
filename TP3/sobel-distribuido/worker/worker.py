import cv2
import numpy as np
import base64
import json
import pika
import redis
import time

def sobel(imagen):
    sobelx = cv2.Sobel(imagen, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(imagen, cv2.CV_64F, 0, 1, ksize=3)
    magnitud = cv2.magnitude(sobelx, sobely)
    resultado = cv2.convertScaleAbs(magnitud)
    return resultado

def procesar_tarea(ch, method, properties, body):
    tarea = json.loads(body)
    chunk_id = tarea["chunk_id"]
    b64_img = tarea["imagen"]

    # Decodificar imagen desde base64
    imagen_bytes = base64.b64decode(b64_img)
    np_arr = np.frombuffer(imagen_bytes, np.uint8)
    imagen = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    # Aplicar Sobel
    resultado = sobel(imagen)

    # Codificar resultado como base64
    _, buffer = cv2.imencode('.jpg', resultado)
    b64_resultado = base64.b64encode(buffer)

    # Guardar en Redis
    r = redis.Redis(host='redis', port=6379)
    r.set(f"resultado:{chunk_id}", b64_resultado)

    print(f"Worker procesó chunk {chunk_id}")

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

def main():
    connection = conectar_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue='tareas')

    channel.basic_consume(queue='tareas', on_message_callback=procesar_tarea, auto_ack=True)

    print("Esperando tareas...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
