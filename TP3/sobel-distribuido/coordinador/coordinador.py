from flask import Flask, request, jsonify, render_template_string, send_file
import cv2
import numpy as np
import base64
import json
import time
import pika
import redis

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<html>
  <head><title>Filtro Sobel</title></head>
  <body>
    <h1>Subir imagen para aplicar filtro</h1>
    <form method="POST" enctype="multipart/form-data">
      Imagen: <input type="file" name="imagen" accept="image/*" required><br>
      Nro de Workers: <input type="number" name="nro_workers" min="1" required><br>
      <input type="submit" value="Procesar Imagen">
    </form>
  </body>
</html>
"""

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

def conectar_rabbitmq(reintentos=5, espera=10):
    for i in range(reintentos):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='rabbitmq-service',
                port=5672,
                credentials=pika.PlainCredentials("guest", "guest")
            ))
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

def esperar_resultados_redis(n, reintentos=3, espera_reintento=2):
    """
    Espera los resultados de los workers, maneja fallos y reintentos.
    Si un worker falla, redistribuye la tarea a otro worker disponible.
    
    :param n: Número de partes a procesar.
    :param reintentos: Número de reintentos si un worker falla.
    :param espera_reintento: Tiempo de espera antes de reintentar.
    :return: Lista de partes procesadas de la imagen.
    """
    r = redis.Redis(host='redis-service', port=6379)
    partes_procesadas = []
    tareas_en_proceso = set(range(n))  # Mantener un registro de qué tareas están en proceso

    while tareas_en_proceso:
        for i in list(tareas_en_proceso):
            key = f"resultado:{i}"
            if r.exists(key):
                # Si el resultado ya está disponible
                b64 = r.get(key)
                img_bytes = base64.b64decode(b64)
                parte = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
                partes_procesadas.append(parte)
                tareas_en_proceso.remove(i)  # Eliminar la tarea completada
            else:
                # Si el worker no ha terminado, intentamos reintentar o redistribuir la tarea
                print(f"Tarea {i} aún no procesada. Intentando nuevamente...")
                if reintentos > 0:
                    print(f"Tarea {i} no completada, reintentando en {espera_reintento} segundos...")
                    time.sleep(espera_reintento)
                    # Reducción de reintentos
                    reintentos -= 1
                else:
                    # Si no se han completado después de los intentos, redistribuir la tarea a otro worker.
                    print(f"Tarea {i} falló después de varios intentos, redistribuyendo...")
                    # Aquí puede implementarse la lógica para redistribuir la tarea a otro worker.
                    tareas_en_proceso.add(i)  # Volver a poner la tarea en la cola para que otro worker la procese
                    reintentos = 3  # Restablecer reintentos para las nuevas tareas

        # Esperar un breve intervalo antes de volver a comprobar el estado de las tareas
        time.sleep(1)

    return partes_procesadas

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(HTML_FORM)

    # POST: procesar imagen
    if "imagen" not in request.files or "nro_workers" not in request.form:
        return "Faltan parámetros.", 400

    try:
        n = int(request.form["nro_workers"])
        file = request.files["imagen"]
        if file.filename == "":
            return "No se seleccionó archivo.", 400

        file_bytes = file.read()
        img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)

        partes = dividir_imagen(img, n)
        enviar_tareas(partes)

        print("Tareas enviadas. Esperando resultados...")
        partes_filtradas = esperar_resultados_redis(n)
        resultado = unir_imagenes(partes_filtradas)

        # Guardar imagen temporalmente
        filename = "/tmp/resultado.jpg"
        cv2.imwrite(filename, resultado)

        # Enviar como descarga
        return send_file(filename, as_attachment=True, download_name="resultado.jpg", mimetype="image/jpeg")
    
    except Exception as e:
        return f"Error interno: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)