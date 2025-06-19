import pika
import json
import threading
from flask import Flask, request, jsonify
import uuid
import time
import hashlib
import os

BLOCKCHAIN_PATH = "TPFinal/blockchain.json"

app = Flask(__name__)
transacciones_pendientes = []

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

    transacciones_pendientes.append(transaccion)
    print("[🧾] Transacción agregada:", transaccion)

    return jsonify({"mensaje": "Transacción recibida", "transaccion": transaccion}), 201

# Endpoint para ver todas las transacciones pendientes (opcional)
@app.route('/transacciones', methods=['GET'])
def ver_transacciones():
    return jsonify(transacciones_pendientes), 200

@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    # Conectarse a RabbitMQ y consumir UNA tarea de la cola
    method_frame, header_frame, body = channel.basic_get(queue='mining_tasks', auto_ack=True)
    
    if method_frame:
        tarea = json.loads(body)
        return jsonify(tarea), 200
    else:
        return jsonify({"mensaje": "No hay tareas disponibles"}), 204

def calcular_hash(bloque):
    bloque_str = json.dumps(bloque, sort_keys=True).encode()
    return hashlib.sha256(bloque_str).hexdigest()

def crear_bloque_genesis():
    bloque = {
        "index": 0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "transacciones": [
            {
                "de": "CoinBase",
                "para": "Bautista",
                "monto": 50
            }
        ],
        "prev_hash": "0"*64,
        "nonce": 0
    }
    bloque["hash"] = calcular_hash(bloque)
    return bloque

def guardar_bloque(bloque):
    with open(BLOCKCHAIN_PATH, "w") as f:
        f.write(json.dumps([bloque], indent=4))

def inicializar_blockchain():
    if not os.path.exists(BLOCKCHAIN_PATH):
        print("[🧱] No se encontró blockchain. Generando bloque génesis...")
        genesis = crear_bloque_genesis()
        guardar_bloque(genesis)
    else:
        print("[✅] Blockchain ya existe.")

inicializar_blockchain()
