import pika
import json
import threading
import base64
import ntplib
import time
import hashlib
import redis
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from datetime import datetime, timedelta

app = Flask(__name__)
#transacciones_pendientes = []

print("[INIT] Conectando a RabbitMQ...")
rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = rabbit_connection.channel()
channel.queue_declare(queue='mining_tasks')
print("[OK] Conectado a RabbitMQ y cola declarada.")

print("[INIT] Conectando a Redis...")
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
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
    "curva": "secp384r1",                           # Curva elíptica utilizada para las firmas
    "alg": "md5",                                   # Algoritmo de hash utilizado
    "coins": 21000000,                              # Cantidad total de monedas en la blockchain
    "dificultad_inicial": "00",                     # Dificultad inicial de la minería
    "tiempo_ronda_seg": 45,                         # Ventana para obtener tareas de minería
    "tiempo_resultados_seg": 15,                    # Ventana para recibir resultados de mineria
    "tiempo_espera_seg": 5,                        # Tiempo de espera entre rondas
    "max_intentos_mineria": 3,                      # Máximo de veces que se reintenta una tarea si no se obtiene resultado
    "premio_minado": 500,                           # Recompensa por minar un bloque
    "ntp_server": "ar.pool.ntp.org"                 # Servidor NTP utilizado para sincronizar la hora
}

# Cargadas desde Redis o con valores por defecto
configuracion_blockchain = {} # Se cargará al inicio

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
        print("[❌] Transacción incompleta: falta transaccion, clave_publica o firma")
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
        print("[🔐] Firma verificada correctamente.")
    except InvalidSignature:
        print("[❌] Firma inválida")
        return jsonify({"error": "Firma inválida"}), 400
    except Exception as e:
        print("[❌] Error en la validación:", e)
        return jsonify({"error": f"Error en la validación: {str(e)}"}), 400

    # Guardar transacción pendiente
    entrada_pendiente = {
        "transaccion": transaccion,
        "firma": firma_b64,
        "clave_publica": clave_publica_pem
    }

    redis_client.rpush("transacciones_pendientes", firma_b64)
    redis_client.set(f"transaccion:{firma_b64}", json.dumps(entrada_pendiente))
    print("[🧾] Transacción pendiente encolada en Redis:", transaccion)

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

# Endpoint para lectura de la blockchain
@app.route("/blockchain", methods=["GET"])
def obtener_blockchain():
    bloques = [json.loads(b) for b in redis_client.lrange("blockchain", 0, -1)]
    return jsonify(bloques), 200

# Endpoint para obtener la configuración de la blockchain
@app.route("/configuracion", methods=["GET"])
def obtener_configuracion():
    config_json = redis_client.get("configuracion_blockchain")
    if not config_json:
        print("[❌] No se encontró configuración de la blockchain.")
        return jsonify({"error": "Configuración no encontrada"}), 404
    config = json.loads(config_json)
    return jsonify(config), 200

@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    global tarea_mineria_actual_global, total_workers_en_ronda

    if estado_actual() != 'ventana_tareas':
        print("[⏸️] No es el momento de solicitar tareas. Ventana actual:", estado_actual())
        return jsonify({"mensaje": "No es el momento de solicitar tareas"}), 403
    print("[⛏️] Buscando tarea en cola de minería...")

    if tarea_mineria_actual_global:
        total_workers_en_ronda += 1
        print(f"[WORKER_COUNT] Workers que han solicitado tarea en esta ronda: {total_workers_en_ronda}")
        print("[📤] Tarea de minería entregada:", tarea_mineria_actual_global)
        return jsonify(tarea_mineria_actual_global), 200
    else:
        method_frame, header_frame, body = channel.basic_get(queue='mining_tasks', auto_ack=False)
        if method_frame:
            tarea_mineria_actual_global = json.loads(body)
            total_workers_en_ronda = 1
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)

            print(f"[WORKER_COUNT] Primer worker de la ronda.")
            print("[📤] Tarea de minería entregada y eliminada de la cola:", tarea_mineria_actual_global)
            return jsonify(tarea_mineria_actual_global), 200
        else:
            print("[🟡] No hay tareas disponibles.")
            return jsonify({"mensaje": "No hay tareas disponibles"}), 204

@app.route('/resultado', methods=['POST'])
def recibir_resultado_mineria():
    global primer_bloque_encontrado_global, tarea_mineria_actual_global, soluciones_exitosas_en_ronda, configuracion_blockchain
    
    if estado_actual() != 'ventana_resultados':
        print("[⏸️] No es el momento de publicar resultados. Ventana actual:", estado_actual())
        return jsonify({"mensaje": "No es el momento de publicar resultados"}), 403

    bloque = request.get_json()
    print("Recibiendo resultado de minería: ", bloque)

    if not bloque or 'hash' not in bloque or 'nonce' not in bloque or 'direccion' not in bloque:
        print("Bloque inválido o incompleto")
        return jsonify({"error": "Bloque inválido o incompleto, falta clave_publica, hash o nonce"}), 400

    clave_publica = bloque["direccion"]

    # Obtener el bloque original desde Redis (basado en el index)
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

    dificultad = redis_client.get("dificultad_actual")
    if not bloque["hash"].startswith("0" * len(dificultad)):
        print("Hash no cumple la dificultad.")
        return jsonify({"error": f"No cumple la dificultad ({dificultad})"}), 400

    soluciones_exitosas_en_ronda += 1
    print(f"Soluciones exitosas recibidas en esta ronda: {soluciones_exitosas_en_ronda}")

    if primer_bloque_encontrado_global is None:
        # Este es el primer resultado válido recibido, lo aceptamos

        bloque_final_para_guardar = bloque_guardado.copy()
        bloque_final_para_guardar["hash"] = bloque["hash"]

        primer_bloque_encontrado_global = {
            "bloque_validado": bloque_final_para_guardar,
            "hash_final": bloque_final_para_guardar["hash"],
            "clave_publica_minero": clave_publica
        }

        return jsonify({"mensaje": "Primer bloque válido agregado y recompensa asignada"}), 200

    else:
        # No es el primer resultado, validar pero no guardar ni recompensar
        print(f"Resultado válido recibido para bloque index {bloque_original_id}, pero no es el primero, no se guarda ni recompensa.")
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
        print("[⚠️] No se configuró una recompensa para el minado de bloques.")
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

def obtener_dificultad_inicial(): 
    return CONFIG.get("dificultad_inicial", "00")

def ajustar_dificultad():
    global total_workers_en_ronda, soluciones_exitosas_en_ronda
    dificultad_actual = redis_client.get("dificultad_actual")
    
    # Calcular la tasa de éxito
    tasa_exito = 0.0
    if total_workers_en_ronda > 0:
        tasa_exito = soluciones_exitosas_en_ronda / total_workers_en_ronda

    print(f"[DIFICULTAD] Resumen de ronda: {soluciones_exitosas_en_ronda} soluciones exitosas de {total_workers_en_ronda} workers (Tasa: {tasa_exito:.2f})")

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
        
        print(f"[DIFICULTAD] Tasa de éxito del 0%. Dificultad reducida de '{dificultad_actual}' a '{nueva_dificultad}'.")
    elif tasa_exito >= 0.90:
        nueva_dificultad = dificultad_actual + "00"
        print(f"[DIFICULTAD] Tasa de éxito del >=90%. Dificultad aumentada de '{dificultad_actual}' a '{nueva_dificultad}'.")
    elif tasa_exito >= 0.20: 
        print(f"[DIFICULTAD] Tasa de éxito ~20-90%. Dificultad se mantiene en '{dificultad_actual}'.")
    else:
        print(f"[DIFICULTAD] Tasa de éxito entre 0% y 20% (excl. 0%). Dificultad se mantiene en '{dificultad_actual}'.")

    if nueva_dificultad != dificultad_actual:
        redis_client.set("dificultad_actual", nueva_dificultad)
        print(f"[DIFICULTAD] Nueva dificultad '{nueva_dificultad}' guardada en Redis.")
    else:
        print("[DIFICULTAD] Dificultad no ha cambiado.")

        # Resetear contadores para la próxima ronda
    total_workers_en_ronda = 0
    soluciones_exitosas_en_ronda = 0

def crear_bloque_genesis():
    print("[🌱] Creando bloque génesis...")
    transaccion_origen = {
        "de": "0" * 64,                                       # No hay origen en el bloque génesis
        "para": "CoinBase",                                   # Cuenta encargada de dar recompensas
        "monto": CONFIG["coins"],                             # Monto total de monedas en la blockchain
    }
    hora = obtener_hora_ntp().strftime("%Y-%m-%d %H:%M:%S")   # Hora de creación del bloque génesis
    bloque = {
        "index": 0,
        "transacciones": [transaccion_origen],
        "prev_hash": "0" * 64,
        "nonce": 0,
        "configuracion": CONFIG,
        "dificultad": CONFIG.get("dificultad_inicial", "00"), # Dificultad inicial
        "timestamp": hora                                     # Timestamp de creación de la tarea
    }
    return bloque

def enviar_a_minar(bloque):
    print("[📤] Enviando bloque a minar...")

    # Guardar número de intento en Redis
    redis_client.set(f"intentos:{bloque['index']}", 1)
    redis_client.set(f"tarea_bloque:{bloque['index']}", json.dumps(bloque))

    channel.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(bloque))
    print("[🚀] Bloque enviado a minar:", bloque)

def procesar_bloque_encontrado(datos_primer_bloque):
    
    bloque_verificado = datos_primer_bloque["bloque_validado"]
    clave_publica_minero = datos_primer_bloque["clave_publica_minero"] # No usada en esta iteración
    hash_final = datos_primer_bloque["hash_final"]

    # No se añade recompensa en esta iteración.
    
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
            print(f"[*] Transacción sin 'firma' (CoinBase). No eliminada del mempool. Transacción: {tx}")

    print("[🥳] Bloque minado con éxito y agregado a la blockchain, recompensa entragada al minero.")

def manejar_cambio_a_resultados():
    global tarea_mineria_actual_global
    print(f"[🏁] Cambio a ventana de resultados para bloque {tarea_mineria_actual_global['index'] if tarea_mineria_actual_global else 'N/A'}.")

def manejar_cambio_a_tareas():
    global total_workers_en_ronda, soluciones_exitosas_en_ronda
    total_workers_en_ronda = 0
    soluciones_exitosas_en_ronda = 0

def manejar_cambio_a_espera():
    global tarea_mineria_actual_global, primer_bloque_encontrado_global
    global total_workers_en_ronda, soluciones_exitosas_en_ronda

    print("\n[⏱️] Cambio detectado a ventana de espera. Procesando estado de minería...")

    if tarea_mineria_actual_global:
        bloque_index = tarea_mineria_actual_global["index"]
        print(f"[🔎] Evaluando estado del bloque {bloque_index}...")

        if primer_bloque_encontrado_global:
            print("[✅] Se encontró un bloque válido durante la ronda. Procesando...")
            procesar_bloque_encontrado(primer_bloque_encontrado_global)
            primer_bloque_encontrado_global = None
            redis_client.delete(f"tarea_bloque:{bloque_index}")
            redis_client.delete(f"intentos:{bloque_index}")
            tarea_mineria_actual_global = None
        else:
            print("[❌] Ningún minero resolvió la tarea. Evaluando reintento...")
            redis_client.incr(f"intentos:{bloque_index}")
            intentos_str = redis_client.get(f"intentos:{bloque_index}")
            intentos = int(intentos_str or 0)

            print(f"[🔁] Intento actual: {intentos}/{CONFIG['max_intentos_mineria']}")

            if intentos > configuracion_blockchain["max_intentos_mineria"]:
                print(f"[🛑] Máximo de intentos alcanzado para bloque {bloque_index}. Se descarta definitivamente.")
                redis_client.delete(f"tarea_bloque:{bloque_index}")
                redis_client.delete(f"intentos:{bloque_index}")
                tarea_mineria_actual_global = None
            else:
                print(f"[📤] Reenviando tarea {bloque_index} a la cola de minería (intento {intentos})...")
                channel.basic_publish(
                    exchange='', routing_key='mining_tasks', body=json.dumps(tarea_mineria_actual_global)
                )

    else:
        print("[⚠️] No había tarea de minería activa al comenzar esta ventana.")

    print("[⚙️] Ajustando dificultad en función de los resultados...")
    ajustar_dificultad()

    if not tarea_mineria_actual_global:
        print("[🚀] Preparando nueva tarea desde las transacciones pendientes...")
        crear_tarea_desde_pendientes()
    else:
        print("[🕒] Tarea aún en curso. No se crea una nueva tarea.")

def crear_tarea_desde_pendientes():
    print("[📥] Recuperando transacciones pendientes para nuevo bloque...")
    transacciones = []

    while redis_client.llen("transacciones_pendientes") > 0:
        firma = redis_client.lpop("transacciones_pendientes")
        if firma:
            t_json = redis_client.get(f"transaccion:{firma}")
            if t_json:
                transacciones.append(json.loads(t_json))
                print(f"[➕] Transacción recuperada: {firma}")

    if not transacciones:
        print("[🟡] No hay transacciones suficientes para crear un nuevo bloque.")
        return

    print(f"[📦] {len(transacciones)} transacciones listas para minar. Creando bloque...")
    crear_nueva_tarea(transacciones)

def crear_nueva_tarea(transacciones=None): 
    global tarea_mineria_actual_global, contador_intentos_mineria_global, tiempo_inicio_mineria_global, primer_bloque_encontrado_global
    print("[🧱] Creando nueva tarea de minería...")

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

    print(f"[🔧] Nueva tarea creada: índice {prox_indice}, dificultad {dificultad_actual}, {len(transacciones)} transacciones.")

    redis_client.set("bloque_en_curso", json.dumps(new_block))
    enviar_a_minar(new_block)
    primer_bloque_encontrado_global = None
    print("[📤] Tarea enviada a la cola de minería.")
    return new_block

def cargar_configuracion_blockchain():
    global configuracion_blockchain, CICLO_TOTAL
    config_json = redis_client.get("configuracion_blockchain")
    print("[⚙️] Cargando configuración de la blockchain desde Redis.")
    CICLO_TOTAL = CONFIG["tiempo_ronda_seg"] + CONFIG["tiempo_resultados_seg"] + CONFIG["tiempo_espera_seg"]
    configuracion_blockchain = json.loads(config_json)

def crear_configuracion():    
    config = CONFIG.copy()  # Copia la configuración por defecto
    redis_client.set("configuracion_blockchain", json.dumps(config))
    print("[⚙️] Configuración almacenada en Redis.")
    global CICLO_TOTAL
    redis_client.set("dificultad_actual", CONFIG["dificultad_inicial"]) # Inicializar dificultad
    CICLO_TOTAL = CONFIG["tiempo_ronda_seg"] + CONFIG["tiempo_resultados_seg"] + CONFIG["tiempo_espera_seg"]
    return config

def inicializar_blockchain():
    global tarea_mineria_actual_global
    print("[🔧] Inicializando blockchain...")
    if redis_client.llen("blockchain") == 0:
        print("[🧱] No se encontró blockchain. Generando configuración y bloque génesis...")
        crear_configuracion()
        bloque_genesis = crear_bloque_genesis()
        enviar_a_minar(bloque_genesis)
        print("[🌱] Bloque génesis preparado para minar y ronda iniciada.")
    else:
        print("[✅] Blockchain ya existe.")
        cargar_configuracion_blockchain()

if __name__ == "__main__":
    inicializar_blockchain()
    threading.Thread(target=ciclo_monitor, daemon=True).start()
    print("[🚀] Coordinador ejecutándose en http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)