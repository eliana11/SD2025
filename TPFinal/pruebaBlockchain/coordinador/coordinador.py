import pika
import json
import threading
from flask import Flask, request, jsonify
import uuid
import time
import hashlib
import os
import redis

app = Flask(__name__)
transacciones_pendientes = []

rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = rabbit_connection.channel()
channel.queue_declare(queue='mining_tasks')


redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.route('/registro', methods=['POST'])
def registrar_usuario():
    datos = request.get_json()
    if 'clave_publica' not in datos:
        return jsonify({"error": "Falta clave_publica"}), 400
    redis_client.set(f"usuario:{datos['clave_publica']}", json.dumps(datos))
    return jsonify({"mensaje": "Usuario registrado"}), 201

# Endpoint para agregar una nueva transacción
@app.route('/transaccion', methods=['POST'])
def agregar_transaccion():
    datos = request.get_json()

    if not datos or 'de' not in datos or 'para' not in datos or 'monto' not in datos:
        return jsonify({"error": "Faltan campos requeridos (de, para, monto)"}), 400

    transaccion = {
        "id": str(uuid.uuid4()),
        "de": datos["de"],
        "para": datos["para"],
        "monto": datos["monto"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Guardar transacción en Redis
    redis_client.set(f"transaccion:{transaccion['id']}", json.dumps(transaccion))
    redis_client.rpush("mempool", transaccion['id'])

    print("[🧾] Transacción agregada:", transaccion)
    return jsonify({"mensaje": "Transacción recibida", "transaccion": transaccion}), 201


# Endpoint para ver todas las transacciones pendientes (opcional)
@app.route('/transacciones', methods=['GET'])
def ver_transacciones():
    ids = redis_client.lrange("mempool", 0, -1)
    transacciones = [json.loads(redis_client.get(f"transaccion:{tid}")) for tid in ids]
    return jsonify(transacciones), 200


@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    # Conectarse a RabbitMQ y consumir UNA tarea de la cola
    method_frame, header_frame, body = channel.basic_get(queue='mining_tasks', auto_ack=True)
    
    if method_frame:
        tarea = json.loads(body)
        return jsonify(tarea), 200
    else:
        return jsonify({"mensaje": "No hay tareas disponibles"}), 204

@app.route('/resultado', methods=['POST'])
def recibir_resultado_mineria():
    bloque = request.get_json()

    if not bloque or 'hash' not in bloque or 'nonce' not in bloque:
        return jsonify({"error": "Bloque inválido o incompleto"}), 400

    # Obtener la dificultad desde Redis
    config = json.loads(redis_client.get("configuracion_blockchain"))
    dificultad = config.get("dificultad", 1)

    # Recalcular el hash y verificar que coincida y cumpla con la dificultad
    hash_calculado = calcular_hash(bloque)

    if hash_calculado != bloque["hash"]:
        return jsonify({"error": "Hash inválido"}), 400

    if not bloque["hash"].startswith("0" * dificultad):
        return jsonify({"error": f"No cumple la dificultad ({dificultad})"}), 400

    # Guardar el bloque en Redis
    guardar_bloque_en_redis(bloque)

    # Eliminar transacciones de mempool
    for tx in bloque["transacciones"]:
        redis_client.delete(f"transaccion:{tx['id']}")
        redis_client.lrem("mempool", 0, tx["id"])

    print("[✅] Bloque minado recibido y agregado a la blockchain.")
    return jsonify({"mensaje": "Bloque agregado correctamente"}), 200


def calcular_hash(bloque):
    bloque_str = json.dumps(bloque, sort_keys=True).encode()
    return hashlib.sha256(bloque_str).hexdigest()

def guardar_bloque_en_redis(bloque):
    hash_bloque = bloque["hash"]
    bloque_id = str(bloque.get("index", 0))

    # Guardar el bloque como JSON completo
    redis_client.set(f"bloque:{hash_bloque}", json.dumps(bloque))

    # Relacionar el index con el hash
    redis_client.set(f"bloque_id:{bloque_id}", hash_bloque)

    # Agregar a la lista principal de la blockchain
    redis_client.rpush("blockchain", hash_bloque)

def obtener_ultimo_hash():
    if redis_client.llen("blockchain") == 0:
        return "0" * 64
    ultimo = redis_client.lindex("blockchain", -1)
    bloque_json = redis_client.get(f"bloque:{ultimo}")
    bloque = json.loads(bloque_json)
    return bloque["hash"]

def crear_tarea_de_mineria(transacciones):
    tarea = {
        "index": redis_client.llen("blockchain"),  # siguiente bloque
        "transacciones": transacciones,
        "prev_hash": obtener_ultimo_hash(),
        "dificultad": 2,  # podés hacer configurable esto
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    channel.basic_publish(
        exchange='',
        routing_key='mining_tasks',
        body=json.dumps(tarea)
    )
    print("[📤] Tarea de minería publicada:", tarea)

def crear_bloque_genesis(config):
    transaccion_recompensa = {
        "id": str(uuid.uuid4()),
        "de": "CoinBase",
        "para": "Bautista",
        "monto": config["coins"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    bloque = {
        "index": 0,
        "transacciones": [transaccion_recompensa],
        "prev_hash": "0" * 64,
        "nonce": 0
    }

    bloque["hash"] = calcular_hash(bloque)
    return bloque

def crear_configuracion():
    config = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "curva": "secp384r1",
        "alg": "md5",
        "coins": 21000000,
        "halving": 10,
        "factor": 0.9,
        "dificultad": 2
    }
    redis_client.set("configuracion_blockchain", json.dumps(config))
    return config

def enviar_a_minar(bloque):
    tarea = {
        "bloque": bloque,
        "dificultad": redis_client.get("configuracion_blockchain") and json.loads(redis_client.get("configuracion_blockchain"))["dificultad"] or 1
    }
    channel.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(tarea))
    print("[🚀] Bloque enviado a minar.")


def inicializar_blockchain():
    if redis_client.llen("blockchain") == 0:
        print("[🧱] No se encontró blockchain. Generando config y bloque génesis...")

        config = crear_configuracion()
        bloque_genesis = crear_bloque_genesis(config)
        enviar_a_minar(bloque_genesis)

    else:
        print("[✅] Blockchain ya existe.")


if __name__ == "__main__":
    inicializar_blockchain()
    app.run(debug=True, port=5000)