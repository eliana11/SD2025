import pika
import json
import threading
import base64
import ntplib
import time
import hashlib
import redis
import os
import logging
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from datetime import datetime, timedelta

app = Flask(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

print(f"[INIT] Conectando a Redis en {REDIS_HOST}...")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
print("[OK] Conectado a Redis.")

tarea_mineria_actual_global = None     # Almacena el bloque que se está minando actualmente
primer_bloque_encontrado_global = None # Variable para almacenar el primer resultado encontrado
total_workers_en_ronda = 0
soluciones_exitosas_en_ronda = 0
hora_ntp_cache = None                  # Para evitar múltiples llamadas a NTP
momento_local_cache = None             # Para evitar múltiples llamadas a hora local
duracion_cache_segundos = 60           # Duración del cache en segundos

CICLO_TOTAL = None
MARGEN_TOLERANCIA = 0.5                # Margen de tolerancia para el ciclo de tiempo

CONFIG = {
    "curva": "SECP256K1",                           # Curva elíptica utilizada para las firmas
    "alg": "md5",                                   # Algoritmo de hash utilizado
    "coins": 21000000,                              # Cantidad total de monedas en la blockchain
    "dificultad_inicial": "00",                     # Dificultad inicial de la minería
    "tiempo_ronda_seg": 45,                         # Ventana para obtener tareas de minería
    "tiempo_resultados_seg": 15,                    # Ventana para recibir resultados de mineria
    "tiempo_espera_seg": 5,                         # Tiempo de espera entre rondas
    "max_intentos_mineria": 10,                     # Máximo de veces que se reintenta una tarea si no se obtiene resultado
    "premio_minado": 500,                           # Recompensa por minar un bloque
    "ntp_server": "ar.pool.ntp.org"                 # Servidor NTP utilizado para sincronizar la hora
}

# Cargadas desde Redis o con valores por defecto
configuracion_blockchain = {} # Se cargará al inicio

logging.basicConfig(level=logging.INFO)
# Ajustar el nivel de logs para librerías externas para reducir ruido
logging.getLogger("pika").setLevel(logging.WARNING)       # Solo warnings o errores de Pika
logging.getLogger("werkzeug").setLevel(logging.WARNING)   # Solo warnings o errores del servidor Flask

def ciclo_monitor():
    while True:
        estado = estado_actual()
        print(f"[⏳] Estado actual: {estado}")

        ahora = obtener_hora_ntp().timestamp()
        tiempo_genesis_str = CONFIG.get("time")
        tiempo_genesis = datetime.strptime(tiempo_genesis_str, "%Y-%m-%d %H:%M:%S").timestamp()

        desde_genesis = ahora - tiempo_genesis
        en_ciclo = desde_genesis % CICLO_TOTAL

        t_ronda = CONFIG.get("tiempo_ronda_seg")
        t_resultados = CONFIG.get("tiempo_resultados_seg")
        t_espera = CONFIG.get("tiempo_espera_seg")

        if estado == "ventana_tareas":
            manejar_cambio_a_tareas()
            tiempo_restante = t_ronda - en_ciclo
        elif estado == "ventana_resultados":
            manejar_cambio_a_resultados()
            tiempo_restante = t_ronda + t_resultados - en_ciclo
        else:
            manejar_cambio_a_espera()
            tiempo_restante = CICLO_TOTAL - en_ciclo

        print(f"[🕐] Esperando {max(0, round(tiempo_restante, 2))} segundos hasta próximo cambio de estado...")
        time.sleep(max(0, tiempo_restante))

def obtener_hora_ntp():
    global hora_ntp_cache, momento_local_cache
    ahora_local = time.time()

    # Usar caché si no venció
    if hora_ntp_cache and momento_local_cache:
        if ahora_local - momento_local_cache < duracion_cache_segundos:
            diferencia = ahora_local - momento_local_cache
            return hora_ntp_cache + timedelta(seconds=diferencia)

    ntp_server = CONFIG.get("ntp_server")
    if not ntp_server:
        print("[❌] No se configuró un servidor NTP. Usando hora local.")
        return datetime.now()
    try:
        client = ntplib.NTPClient()
        response = client.request(ntp_server, version=3)

        # Actualizar caché
        hora_ntp_cache = datetime.fromtimestamp(response.tx_time)
        momento_local_cache = ahora_local

        print(f"[NTP] Hora sincronizada con {ntp_server}")
        return hora_ntp_cache

    except Exception as e:
        print(f"[NTP] Error al obtener hora NTP: {e}")
        return datetime.now()  # Fallback a la hora local

CONFIG["time"] = obtener_hora_ntp().strftime("%Y-%m-%d %H:%M:%S")

# Endpoint para obtener estado del coordinador
@app.route('/estado', methods=['GET'])
def obtener_estado():
    estado = estado_actual()
    tiempo_genesis_str = CONFIG.get("time")
    tiempo_genesis = datetime.strptime(tiempo_genesis_str, "%Y-%m-%d %H:%M:%S").timestamp()
    ahora = obtener_hora_ntp().timestamp()
    desde_genesis = ahora - tiempo_genesis
    en_ciclo = desde_genesis % CICLO_TOTAL

    t_ronda = CONFIG.get("tiempo_ronda_seg")
    t_resultados = CONFIG.get("tiempo_resultados_seg")
    t_espera = CONFIG.get("tiempo_espera_seg")

    return jsonify({
        "estado": estado,
        "tiempo_restante": max(0, round(CICLO_TOTAL - en_ciclo, 2)),
        "tiempo_ronda": t_ronda,
        "tiempo_resultados": t_resultados,
        "tiempo_espera": t_espera
    }), 200

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

    # Validar campos requeridos
    if not datos or 'transaccion' not in datos or 'clave_publica' not in datos or 'firma' not in datos:
        logging.error("[❌] Transacción incompleta: falta transaccion, clave_publica o firma")
        return jsonify({"error": "Faltan campos requeridos: transaccion, clave_publica, firma"}), 400

    transaccion = datos["transaccion"]
    clave_publica_pem = datos["clave_publica"]
    firma_b64 = datos["firma"]

    # Verificar firma digital
    try:
        mensaje = json.dumps(transaccion, sort_keys=True).encode()
        firma = base64.b64decode(firma_b64)
        clave_publica = serialization.load_pem_public_key(clave_publica_pem.encode())
        clave_publica.verify(firma, mensaje, ec.ECDSA(hashes.SHA256()))
        logging.info("[🔐] Firma verificada correctamente.")
    except InvalidSignature:
        logging.error("[❌] Firma inválida")
        return jsonify({"error": "Firma inválida"}), 400
    except Exception as e:
        logging.error(f"[❌] Error en la validación: {e}")
        return jsonify({"error": f"Error en la validación: {str(e)}"}), 400

    # Guardar transacción pendiente
    entrada_pendiente = {
        "transaccion": transaccion,
        "firma": firma_b64,
        "clave_publica": clave_publica_pem
    }

    redis_client.rpush("transacciones_pendientes", firma_b64)
    redis_client.set(f"transaccion:{firma_b64}", json.dumps(entrada_pendiente))
    logging.info(f"[🧾] Transacción pendiente encolada en Redis: {transaccion}")

    return jsonify({
        "mensaje": "Transacción válida y encolada para la próxima ronda.",
        "transaccion": transaccion
    }), 202

# Endpoint para ver todas las transacciones pendientes (opcional)
@app.route('/transacciones', methods=['GET'])
def ver_transacciones():
    print("[🔍] Consultando transacciones pendientes...")
    firmas = redis_client.lrange("transacciones_pendientes", 0, -1)
    transacciones = [json.loads(redis_client.get(f"transaccion:{firma}")) for firma in firmas]
    return jsonify(transacciones), 200

@app.route("/blockchain", methods=["GET"])
def obtener_blockchain():
    try:
        hashes = redis_client.lrange("blockchain", 0, -1)
        bloques = []

        for hash_bloque in hashes:
            if isinstance(hash_bloque, bytes):
                hash_bloque = hash_bloque.decode("utf-8")

            clave_bloque = f"bloque:{hash_bloque}"
            bloque_json = redis_client.get(clave_bloque)

            if not bloque_json:
                logging.warning(f"[⚠️] No se encontró bloque con hash: {hash_bloque}")
                continue

            if isinstance(bloque_json, bytes):
                bloque_json = bloque_json.decode("utf-8")

            try:
                bloque = json.loads(bloque_json)
                bloques.append(bloque)
            except json.JSONDecodeError:
                logging.warning(f"[⚠️] JSON inválido para bloque {hash_bloque}: {bloque_json}")
                continue

        return jsonify(bloques), 200

    except Exception as e:
        logging.exception("[❌] Error al obtener blockchain")
        return jsonify({"error": "Error al obtener blockchain"}), 500


# Endpoint para obtener la configuración de la blockchain
@app.route("/configuracion", methods=["GET"])
def obtener_configuracion():
    config_json = redis_client.get("configuracion_blockchain")
    if not config_json:
        logging.info("[❌] No se encontró configuración de la blockchain.")
        return jsonify({"error": "Configuración no encontrada"}), 404
    config = json.loads(config_json)
    return jsonify(config), 200

@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    global tarea_mineria_actual_global, total_workers_en_ronda

    if estado_actual() != 'ventana_tareas':
        logging.info("[⏸️] No es el momento de solicitar tareas. Ventana actual: %s", estado_actual())
        return jsonify({"mensaje": "No es el momento de solicitar tareas"}), 403

    logging.info("[⛏️] Buscando tarea en cola de minería...")

    if tarea_mineria_actual_global:
        total_workers_en_ronda += 1
        logging.info("[WORKER_COUNT] Workers que han solicitado tarea en esta ronda: %d", total_workers_en_ronda)
        logging.info("[📤] Tarea de minería entregada: %s", tarea_mineria_actual_global)
        return jsonify(tarea_mineria_actual_global), 200
    else:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            temp_channel = connection.channel()
            temp_channel.queue_declare(queue='mining_tasks', durable=True)
            method_frame, header_frame, body = temp_channel.basic_get(queue='mining_tasks', auto_ack=False)
            if method_frame:
                tarea_mineria_actual_global = json.loads(body)
                total_workers_en_ronda = 1
                temp_channel.basic_ack(delivery_tag=method_frame.delivery_tag)

                logging.info("[WORKER_COUNT] Primer worker de la ronda.")
                logging.info("[📤] Tarea de minería entregada y eliminada de la cola: %s", tarea_mineria_actual_global)
                return jsonify(tarea_mineria_actual_global), 200
            else:
                logging.warning("[🟡] No hay tareas disponibles.")
                return jsonify({"mensaje": "No hay tareas disponibles"}), 204
        except Exception as e:
            logging.exception("❌ Error al intentar obtener tarea de RabbitMQ: %s", str(e))
            return jsonify({"error": "Error al obtener tarea"}), 500
        finally:
            if 'connection' in locals() and connection.is_open:
                connection.close()

@app.route('/resultado', methods=['POST'])
def recibir_resultado_mineria():
    global primer_bloque_encontrado_global, tarea_mineria_actual_global, soluciones_exitosas_en_ronda, configuracion_blockchain

    if estado_actual() != 'ventana_resultados':
        logging.info("[⏸️] No es el momento de publicar resultados. Ventana actual: %s", estado_actual())
        return jsonify({"mensaje": "No es el momento de publicar resultados"}), 403

    bloque = request.get_json()
    logging.info("Recibiendo resultado de minería: %s", bloque)

    if not bloque or 'hash' not in bloque or 'nonce' not in bloque or 'direccion' not in bloque:
        logging.warning("Bloque inválido o incompleto")
        return jsonify({"error": "Bloque inválido o incompleto, falta clave_publica, hash o nonce"}), 400

    clave_publica = bloque["direccion"]

    bloque_original_id = bloque.get("index")
    if bloque_original_id is None:
        return jsonify({"error": "Falta el index del bloque para verificar el hash"}), 400

    bloque_guardado_str = redis_client.get(f"tarea_bloque:{bloque_original_id}")
    if not bloque_guardado_str:
        return jsonify({"error": "Bloque original no encontrado en Redis"}), 400

    bloque_guardado = json.loads(bloque_guardado_str)
    bloque_guardado["nonce"] = bloque["nonce"]

    hash_calculado = calcular_hash(bloque_guardado)

    if hash_calculado != bloque["hash"]:
        logging.warning("Hash inválido. Calculado: %s | Recibido: %s", hash_calculado, bloque["hash"])
        return jsonify({"error": "Hash inválido"}), 400

    dificultad = redis_client.get("dificultad_actual")
    if not bloque["hash"].startswith("0" * len(dificultad)):
        logging.warning("Hash no cumple la dificultad (%s)", dificultad)
        return jsonify({"error": f"No cumple la dificultad ({dificultad})"}), 400

    soluciones_exitosas_en_ronda += 1
    logging.info("Soluciones exitosas recibidas en esta ronda: %d", soluciones_exitosas_en_ronda)

    if primer_bloque_encontrado_global is None:
        bloque_final_para_guardar = bloque_guardado.copy()
        bloque_final_para_guardar["hash"] = bloque["hash"]

        primer_bloque_encontrado_global = {
            "bloque_validado": bloque_final_para_guardar,
            "hash_final": bloque_final_para_guardar["hash"],
            "clave_publica_minero": clave_publica
        }

        logging.info("✅ Primer bloque válido agregado: %s", primer_bloque_encontrado_global)
        return jsonify({"mensaje": "Primer bloque válido agregado y recompensa asignada"}), 200
    else:
        logging.info("Resultado válido recibido para bloque index %s, pero no es el primero, no se guarda ni recompensa.", bloque_original_id)
        return jsonify({"mensaje": "Resultado válido pero bloque ya encontrado por otro minero"}), 200

def estado_actual():
    ahora = obtener_hora_ntp().timestamp()

    tiempo_genesis_str = CONFIG.get("time")
    tiempo_genesis = datetime.strptime(tiempo_genesis_str, "%Y-%m-%d %H:%M:%S").timestamp()

    desde_genesis = ahora - tiempo_genesis
    en_ciclo = desde_genesis % CICLO_TOTAL

    t_ronda = CONFIG.get("tiempo_ronda_seg")
    t_resultados = CONFIG.get("tiempo_resultados_seg")
    t_espera = CONFIG.get("tiempo_espera_seg")

    if en_ciclo < t_ronda - MARGEN_TOLERANCIA:
        return "ventana_tareas"
    elif en_ciclo < t_ronda + t_resultados - MARGEN_TOLERANCIA:
        return "ventana_resultados"
    else:
        return "ventana_espera"

def enviar_recompensa(clave_publica):
    recompensa = CONFIG.get("premio_minado", 0)

    if recompensa <= 0:
        logging.info("[⚠️] No se configuró una recompensa para el minado de bloques.")
        return
    hora = obtener_hora_ntp().strftime("%Y-%m-%d %H:%M:%S")
    transaccion_recompensa = {
        "de": "CoinBase",  # Origen ficticio para la recompensa
        "para": clave_publica,
        "monto": recompensa,
    }
    bloque = {
        "index": redis_client.llen("blockchain"),
        "transacciones": [transaccion_recompensa],
        "prev_hash": obtener_ultimo_hash(),
        "timestamp": hora,  # Hora de creación del bloque
    }
    bloque["hash"] = calcular_hash(bloque)

    guardar_bloque_en_redis(bloque)

def calcular_hash(bloque):
    bloque_str = json.dumps(bloque, sort_keys=True, separators=(',', ':'))
    logging.info("[DEBUG] Calculando hash sobre la siguiente cadena JSON ordenada:")
    logging.info(bloque_str)
    return hashlib.md5(bloque_str.encode()).hexdigest()

def guardar_bloque_en_redis(bloque):
    logging.info("[💾] Guardando bloque en Redis...")
    hash_bloque = bloque["hash"]
    bloque_id = str(bloque.get("index", 0))

    # Guardar el bloque como JSON completo
    redis_client.set(f"bloque:{hash_bloque}", json.dumps(bloque))

    # Relacionar el index con el hash
    redis_client.set(f"bloque_id:{bloque_id}", hash_bloque)

    # Agregar a la lista principal de la blockchain
    redis_client.rpush("blockchain", hash_bloque)
    logging.info("[📦] Bloque guardado con hash:", hash_bloque)

def obtener_ultimo_hash():
    if redis_client.llen("blockchain") == 0:
        return "0" * 64
    ultimo = redis_client.lindex("blockchain", -1)
    bloque_json = redis_client.get(f"bloque:{ultimo}")
    bloque = json.loads(bloque_json)
    return bloque["hash"]

def obtener_dificultad_inicial(): 
    return CONFIG.get("dificultad_inicial", "00")

def ajustar_dificultad():
    global total_workers_en_ronda, soluciones_exitosas_en_ronda
    dificultad_actual = redis_client.get("dificultad_actual")
    
    # Calcular la tasa de éxito
    tasa_exito = 0.0
    if total_workers_en_ronda > 0:
        tasa_exito = soluciones_exitosas_en_ronda / total_workers_en_ronda

    logging.info(f"[DIFICULTAD] Resumen de ronda: {soluciones_exitosas_en_ronda} soluciones exitosas de {total_workers_en_ronda} workers (Tasa: {tasa_exito:.2f})")

    nueva_dificultad = dificultad_actual

    if tasa_exito == 0:
        if len(dificultad_actual) > 0: 
            if len(dificultad_actual) % 2 != 0:
                nueva_dificultad = dificultad_actual[:-1] 
                if not nueva_dificultad: # Si queda vacía (ej: de '0' a '')
                    nueva_dificultad = "00"
            if len(nueva_dificultad) >= 2: # No reducir a menos de '00'
                nueva_dificultad = nueva_dificultad[:-2] # Quitar dos ceros (un byte completo)
                if not nueva_dificultad: # Si se vuelve vacía, establecer la mínima
                    nueva_dificultad = "00" # O la dificultad inicial que consideres mínima
            else: # Caso para '0' o vacía, no se puede reducir más
                nueva_dificultad = "00" # Mantener en la dificultad mínima
        else: # Si ya era "", establecer a "00"
            nueva_dificultad = "00" # Dificultad mínima por defecto
        
        logging.info(f"[DIFICULTAD] Tasa de éxito del 0%. Dificultad reducida de '{dificultad_actual}' a '{nueva_dificultad}'.")
    elif tasa_exito >= 0.90:
        nueva_dificultad = dificultad_actual + "00"
        logging.info(f"[DIFICULTAD] Tasa de éxito del >=90%. Dificultad aumentada de '{dificultad_actual}' a '{nueva_dificultad}'.")
    elif tasa_exito >= 0.20: 
        logging.info(f"[DIFICULTAD] Tasa de éxito ~20-90%. Dificultad se mantiene en '{dificultad_actual}'.")
    else:
        logging.info(f"[DIFICULTAD] Tasa de éxito entre 0% y 20% (excl. 0%). Dificultad se mantiene en '{dificultad_actual}'.")

    if nueva_dificultad != dificultad_actual:
        redis_client.set("dificultad_actual", nueva_dificultad)
        logging.info(f"[DIFICULTAD] Nueva dificultad '{nueva_dificultad}' guardada en Redis.")
    else:
        logging.info("[DIFICULTAD] Dificultad no ha cambiado.")

        # Resetear contadores para la próxima ronda
    total_workers_en_ronda = 0
    soluciones_exitosas_en_ronda = 0

def crear_bloque_genesis():
    logging.info("[🌱] Creando bloque génesis...")
    transaccion_origen = {
        "de": "0" * 64,                                       # No hay origen en el bloque génesis
        "para": "CoinBase",                                   # Cuenta encargada de dar recompensas
        "monto": CONFIG["coins"],                             # Monto total de monedas en la blockchain
    }
    hora = obtener_hora_ntp().strftime("%Y-%m-%d %H:%M:%S")   # Hora de creación del bloque génesis
    bloque = {
        "index": 0,
        "transacciones": [transaccion_origen],
        "hash": "0" * 64,                                     # Hash del bloque génesis (todo ceros)
        "nonce": 0,
        "configuracion": CONFIG,
        "dificultad": CONFIG.get("dificultad_inicial", "00"), # Dificultad inicial
        "timestamp": hora                                     # Timestamp de creación de la tarea
    }
    return bloque

def enviar_a_minar(bloque):
    logging.info("[📤] Enviando bloque a minar...")

    redis_client.set(f"intentos:{bloque['index']}", 1)
    redis_client.set(f"tarea_bloque:{bloque['index']}", json.dumps(bloque))

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue='mining_tasks', durable=True)
        channel.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(bloque))
        logging.info("[🚀] Bloque enviado a minar: %s", bloque)
    except Exception as e:
        logging.exception("❌ Error al enviar bloque a RabbitMQ: %s", str(e))
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()

def procesar_bloque_encontrado(datos_primer_bloque):
    
    bloque_verificado = datos_primer_bloque["bloque_validado"]
    clave_publica_minero = datos_primer_bloque["clave_publica_minero"] # No usada en esta iteración
    hash_final = datos_primer_bloque["hash_final"]
    
    bloque_final = bloque_verificado
    bloque_final["hash"] = hash_final

    guardar_bloque_en_redis(bloque_final)
    enviar_recompensa(clave_publica_minero)
    # Limpieza mempool
    redis_client.delete(f"intentos:{bloque_final['index']}")
    for tx in bloque_verificado["transacciones"]:
        if "id" in tx:
            redis_client.delete(f"transaccion:{tx['firma']}")
            redis_client.lrem("mempool", 0, tx["firma"])
        else:
            logging.info(f"[*] Transacción sin 'firma' (CoinBase). No eliminada del mempool. Transacción: {tx}")

    logging.info("[🥳] Bloque minado con éxito y agregado a la blockchain, recompensa entragada al minero.")

def manejar_cambio_a_resultados():
    global tarea_mineria_actual_global
    logging.info(f"[🏁] Cambio a ventana de resultados para bloque {tarea_mineria_actual_global['index'] if tarea_mineria_actual_global else 'N/A'}.")

def manejar_cambio_a_tareas():
    global total_workers_en_ronda, soluciones_exitosas_en_ronda
    total_workers_en_ronda = 0
    soluciones_exitosas_en_ronda = 0

def manejar_cambio_a_espera():
    global tarea_mineria_actual_global, primer_bloque_encontrado_global
    global total_workers_en_ronda, soluciones_exitosas_en_ronda

    logging.info("\n[⏱️] Cambio detectado a ventana de espera. Procesando estado de minería...")

    if tarea_mineria_actual_global:
        bloque_index = tarea_mineria_actual_global["index"]
        logging.info(f"[🔎] Evaluando estado del bloque {bloque_index}...")

        if primer_bloque_encontrado_global:
            logging.info("[✅] Se encontró un bloque válido durante la ronda. Procesando...")
            procesar_bloque_encontrado(primer_bloque_encontrado_global)
            primer_bloque_encontrado_global = None
            redis_client.delete(f"tarea_bloque:{bloque_index}")
            redis_client.delete(f"intentos:{bloque_index}")
            logging.info("[🗑️] Tarea de minería eliminada de Redis y RabbitMQ.")
            tarea_mineria_actual_global = None
        else:
            logging.warning("[❌] Ningún minero resolvió la tarea. Evaluando reintento...")
            redis_client.incr(f"intentos:{bloque_index}")
            intentos_str = redis_client.get(f"intentos:{bloque_index}")
            intentos = int(intentos_str or 0)

            logging.info(f"[🔁] Intento actual: {intentos}/{CONFIG['max_intentos_mineria']}")

            if intentos > CONFIG["max_intentos_mineria"]:
                logging.error(f"[🛑] Máximo de intentos alcanzado para bloque {bloque_index}. Se descarta definitivamente.")
                redis_client.delete(f"tarea_bloque:{bloque_index}")
                redis_client.delete(f"intentos:{bloque_index}")
                tarea_mineria_actual_global = None
            else:
                logging.info(f"[📤] Reenviando tarea {bloque_index} a la cola de minería (intento {intentos})...")
    else:
        logging.warning("[⚠️] No había tarea de minería activa al comenzar esta ventana.")

    logging.info("[⚙️] Ajustando dificultad en función de los resultados...")
    ajustar_dificultad()

    if not tarea_mineria_actual_global:
        logging.info("[🚀] Preparando nueva tarea desde las transacciones pendientes...")
        crear_tarea_desde_pendientes()
    else:
        logging.info("[🕒] Tarea aún en curso. No se crea una nueva tarea.")

def crear_tarea_desde_pendientes():
    logging.info("[📥] Recuperando transacciones pendientes para nuevo bloque...")
    transacciones = []

    while redis_client.llen("transacciones_pendientes") > 0:
        firma = redis_client.lpop("transacciones_pendientes")
        if firma:
            t_json = redis_client.get(f"transaccion:{firma}")
            if t_json:
                transacciones.append(json.loads(t_json))
                logging.info(f"[➕] Transacción recuperada: {firma}")

    if not transacciones:
        logging.warning("[🟡] No hay transacciones suficientes para crear un nuevo bloque.")
        return

    logging.info(f"[📦] {len(transacciones)} transacciones listas para minar. Creando bloque...")
    crear_nueva_tarea(transacciones)

def crear_nueva_tarea(transacciones=None): 
    global tarea_mineria_actual_global, contador_intentos_mineria_global, tiempo_inicio_mineria_global, primer_bloque_encontrado_global
    logging.info("[🧱] Creando nueva tarea de minería...")

    prox_indice = redis_client.llen("blockchain")        
    hora = obtener_hora_ntp().strftime("%Y-%m-%d %H:%M:%S")
    dificultad_actual = redis_client.get("dificultad_actual")

    new_block = {
        "index": prox_indice,
        "transacciones": transacciones,
        "prev_hash": obtener_ultimo_hash(),
        "nonce": 0,
        "dificultad": dificultad_actual,
        "timestamp": hora
    }

    logging.info(f"[🔧] Nueva tarea creada: índice {prox_indice}, dificultad {dificultad_actual}, {len(transacciones)} transacciones.")

    redis_client.set("bloque_en_curso", json.dumps(new_block))
    enviar_a_minar(new_block)
    primer_bloque_encontrado_global = None
    logging.info("[📤] Tarea enviada a la cola de minería.")
    return new_block

def cargar_configuracion_blockchain():
    global configuracion_blockchain, CICLO_TOTAL
    config_json = redis_client.get("configuracion_blockchain")
    logging.info("[⚙️] Cargando configuración de la blockchain desde Redis.")
    CICLO_TOTAL = CONFIG["tiempo_ronda_seg"] + CONFIG["tiempo_resultados_seg"] + CONFIG["tiempo_espera_seg"]
    configuracion_blockchain = json.loads(config_json)

def crear_configuracion():    
    config = CONFIG.copy()  # Copia la configuración por defecto
    redis_client.set("configuracion_blockchain", json.dumps(config))
    logging.info("[⚙️] Configuración almacenada en Redis.")
    global CICLO_TOTAL
    redis_client.set("dificultad_actual", CONFIG["dificultad_inicial"]) # Inicializar dificultad
    CICLO_TOTAL = CONFIG["tiempo_ronda_seg"] + CONFIG["tiempo_resultados_seg"] + CONFIG["tiempo_espera_seg"]
    return config

def inicializar_blockchain():
    global tarea_mineria_actual_global
    logging.info("[🔧] Inicializando blockchain...")
    if redis_client.llen("blockchain") == 0:
        logging.info("[🧱] No se encontró blockchain. Generando configuración y bloque génesis...")
        crear_configuracion()
        bloque_genesis = crear_bloque_genesis()
        guardar_bloque_en_redis(bloque_genesis)
        logging.info("[🌱] Bloque génesis creado.")
    else:
        logging.info("[✅] Blockchain ya existe.")
        cargar_configuracion_blockchain()

if __name__ == "__main__":
    inicializar_blockchain()
    threading.Thread(target=ciclo_monitor, daemon=True).start()
    print("[🚀] Coordinador ejecutándose en http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)