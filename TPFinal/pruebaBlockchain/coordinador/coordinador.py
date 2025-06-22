import pika
import json
import threading
from flask import Flask, request, jsonify
import uuid
import time
import hashlib
import os
import redis
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
import base64

app = Flask(__name__)
transacciones_pendientes = []

print("[INIT] Conectando a RabbitMQ...")
rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = rabbit_connection.channel()
channel.queue_declare(queue='mining_tasks')
print("[OK] Conectado a RabbitMQ y cola declarada.")

print("[INIT] Conectando a Redis...")
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
print("[OK] Conectado a Redis.")

@app.route('/registro', methods=['POST'])
def registrar_usuario():
    datos = request.get_json()
    if 'clave_publica' not in datos:
        print("[❌] Registro fallido: falta clave_publica")
        return jsonify({"error": "Falta clave_publica"}), 400
    print("[📝] Registro de usuario:", datos["clave_publica"])
    return jsonify({"mensaje": "Usuario registrado"}), 201

# Endpoint para agregar una nueva transacción
@app.route('/transaccion', methods=['POST'])
def agregar_transaccion():
    datos = request.get_json()

    if not datos or 'transaccion' not in datos or 'clave_publica' not in datos or 'firma' not in datos:
        print("[❌] Transacción incompleta: falta transaccion, clave_publica o firma")
        return jsonify({"error": "Faltan campos requeridos: transaccion, clave_publica, firma"}), 400

    transaccion = datos["transaccion"]
    clave_publica_pem = datos["clave_publica"]
    firma_b64 = datos["firma"]

    # Verificar firma
    try:
        mensaje = json.dumps(transaccion, sort_keys=True).encode()
        firma = base64.b64decode(firma_b64)
        clave_publica = serialization.load_pem_public_key(clave_publica_pem.encode())

        clave_publica.verify(firma, mensaje, ec.ECDSA(hashes.SHA256()))
        print("[🔐] Firma verificada correctamente.")
    except InvalidSignature:
        print("[❌] Firma inválida")
        return jsonify({"error": "Firma inválida"}), 400
    except Exception as e:
        print("[❌] Error en la validación:", e)
        return jsonify({"error": f"Error en la validación: {str(e)}"}), 400

    # Agregar ID y timestamp
    transaccion["id"] = str(uuid.uuid4())
    transaccion["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Guardar transacción en Redis
    redis_client.set(f"transaccion:{transaccion['id']}", json.dumps(transaccion))
    redis_client.rpush("mempool", transaccion["id"])

    print("[🧾] Transacción verificada y agregada:", transaccion)
    return jsonify({"mensaje": "Transacción recibida y válida", "transaccion": transaccion}), 201

# Endpoint para ver todas las transacciones pendientes (opcional)
@app.route('/transacciones', methods=['GET'])
def ver_transacciones():
    print("[🔍] Consultando transacciones pendientes...")
    ids = redis_client.lrange("mempool", 0, -1)
    transacciones = [json.loads(redis_client.get(f"transaccion:{tid}")) for tid in ids]
    return jsonify(transacciones), 200

@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    print("[⛏️] Buscando tarea en cola de minería...")
    # Conectarse a RabbitMQ y consumir UNA tarea de la cola
    method_frame, header_frame, body = channel.basic_get(queue='mining_tasks', auto_ack=True)
    
    if method_frame:
        tarea = json.loads(body)
        print("[📤] Tarea de minería entregada:", tarea)
        return jsonify(tarea), 200
    else:
        print("[🟡] No hay tareas disponibles.")
        return jsonify({"mensaje": "No hay tareas disponibles"}), 204

@app.route('/resultado', methods=['POST'])
def recibir_resultado_mineria():
    bloque = request.get_json()
    print("Recibiendo resultado de minería: ", bloque)

    if not bloque or 'hash' not in bloque or 'nonce' not in bloque:
        print("Bloque inválido o incompleto")
        return jsonify({"error": "Bloque inválido o incompleto"}), 400

    # Obtener el bloque original desde Redis (basado en el index o prev_hash)
    bloque_original_id = bloque.get("index")
    if bloque_original_id is None:
        return jsonify({"error": "Falta el index del bloque para verificar el hash"}), 400

    bloque_guardado_str = redis_client.get(f"tarea_bloque:{bloque_original_id}")
    if not bloque_guardado_str:
        return jsonify({"error": "Bloque original no encontrado en Redis"}), 400

    bloque_guardado = json.loads(bloque_guardado_str)
    bloque_guardado["nonce"] = bloque["nonce"]

    # Recalcular el hash
    hash_calculado = calcular_hash(bloque_guardado)

    if hash_calculado != bloque["hash"]:
        print("Hash inválido. Calculado:", hash_calculado, "Recibido:", bloque["hash"])
        return jsonify({"error": "Hash inválido"}), 400

    # Verificar dificultad
    config = json.loads(redis_client.get("configuracion_blockchain"))
    dificultad = config.get("dificultad", "1")
    if not bloque["hash"].startswith("0" * len(dificultad)):
        print("Hash no cumple la dificultad.")
        return jsonify({"error": f"No cumple la dificultad ({dificultad})"}), 400

    # Guardar bloque y limpiar mempool
    guardar_bloque_en_redis(bloque_guardado)
    for tx in bloque_guardado["transacciones"]:
        redis_client.delete(f"transaccion:{tx['id']}")
        redis_client.lrem("mempool", 0, tx["id"])

    print("Bloque minado recibido y agregado a la blockchain.")
    return jsonify({"mensaje": "Bloque agregado correctamente"}), 200

def calcular_hash(bloque):
    bloque_str = json.dumps(bloque, sort_keys=True, separators=(',', ':'))
    print("[DEBUG] Calculando hash sobre la siguiente cadena JSON ordenada:")
    print(bloque_str)
    return hashlib.md5(bloque_str.encode()).hexdigest()

def guardar_bloque_en_redis(bloque):
    print("[💾] Guardando bloque en Redis...")
    hash_bloque = bloque["hash"]
    bloque_id = str(bloque.get("index", 0))

    # Guardar el bloque como JSON completo
    redis_client.set(f"bloque:{hash_bloque}", json.dumps(bloque))

    # Relacionar el index con el hash
    redis_client.set(f"bloque_id:{bloque_id}", hash_bloque)

    # Agregar a la lista principal de la blockchain
    redis_client.rpush("blockchain", hash_bloque)
    print("[📦] Bloque guardado con hash:", hash_bloque)

def obtener_ultimo_hash():
    if redis_client.llen("blockchain") == 0:
        return "0" * 64
    ultimo = redis_client.lindex("blockchain", -1)
    bloque_json = redis_client.get(f"bloque:{ultimo}")
    bloque = json.loads(bloque_json)
    return bloque["hash"]

def crear_configuracion():
    print("[⚙️] Configurando parámetros de la blockchain...")
    config = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "curva": "secp384r1",
        "alg": "md5",
        "coins": 21000000,
        "halving": 10,
        "factor": 0.9,
        "dificultad": "00"
    }
    redis_client.set("configuracion_blockchain", json.dumps(config))
    print("[⚙️] Configuración almacenada en Redis.")
    return config

def crear_bloque_genesis(config):
    print("[🌱] Creando bloque génesis...")
    transaccion_origen = {
        "de": "CoinBase",
        "para": "Bautista",
        "monto": config["coins"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    bloque = {
        "index": 0,
        "transacciones": [transaccion_origen],
        "prev_hash": "0" * 64,
        "nonce": 0,
        "configuracion": config,
    }

    return bloque

def enviar_a_minar(bloque):
    print("[📤] Enviando bloque a minar...")

    # Guardar el bloque en Redis antes de enviarlo (sin el hash todavía)
    redis_client.set(f"tarea_bloque:{bloque['index']}", json.dumps(bloque))

    channel.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(bloque))
    print("[🚀] Bloque enviado a minar:", bloque)

def inicializar_blockchain():
    print("[🔧] Inicializando blockchain...")
    if redis_client.llen("blockchain") == 0:
        print("[🧱] No se encontró blockchain. Generando configuración y bloque génesis...")
        config = crear_configuracion()
        bloque_genesis = crear_bloque_genesis(config)
        enviar_a_minar(bloque_genesis)
    else:
        print("[✅] Blockchain ya existe.")

if __name__ == "__main__":
    inicializar_blockchain()
    print("[🚀] Coordinador ejecutándose en http://localhost:5000")
    app.run(debug=True, port=5000)