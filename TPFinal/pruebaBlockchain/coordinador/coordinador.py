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
import ntplib

from datetime import datetime

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

tarea_mineria_actual_global = None  # Almacena el bloque que se está minando actualmente
tiempo_inicio_mineria_global = None    # Cuándo comenzó la ronda actual
contador_intentos_mineria_global = 0        # Cuántos intentos lleva el bloque actual
timer_ronda_global = None          # Objeto Timer para el timeout de ronda
timer_resultados_global = None        # Objeto Timer para la ventana de resultados
mejor_bloque_encontrado_global = None # Variable para almacenar el mejor resultado encontrado
total_workers_en_ronda = 0
soluciones_exitosas_en_ronda = 0

# Lock global para asegurar que solo una ronda se procesa a la vez
lock_ronda_global = threading.Lock()

# Cargadas desde Redis o con valores por defecto
configuracion_blockchain = {} # Se cargará al inicio

def obtener_hora_ntp():
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', version=3)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        print(f"[NTP] Error al obtener hora NTP: {e}")
        return datetime.now()  # Fallback a la hora local si falla NTP

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

# Endpoint para lectura de la blockchain
@app.route("/blockchain", methods=["GET"])
def obtener_blockchain():
    bloques = [json.loads(b) for b in redis_client.lrange("blockchain", 0, -1)]
    return jsonify(bloques), 200

@app.route("/tarea", methods=["GET"])
def obtener_tarea():
    global tarea_mineria_actual_global, total_workers_en_ronda
    print("[⛏️] Buscando tarea en cola de minería...")

    with lock_ronda_global:
        if tarea_mineria_actual_global:
            total_workers_en_ronda += 1
            print(f"[WORKER_COUNT] Workers que han solicitado tarea en esta ronda: {total_workers_en_ronda}")
            print("[📤] Tarea de minería entregada (desde global):", tarea_mineria_actual_global)
            return jsonify(tarea_mineria_actual_global), 200
        else:
            method_frame, header_frame, body = channel.basic_get(queue='mining_tasks', auto_ack=False)
            if method_frame:
                tarea = json.loads(body)
                
                # ❌ No hacemos ack ni republicamos — el mensaje permanece en la cola

                total_workers_en_ronda += 1
                print(f"[WORKER_COUNT] Workers que han solicitado tarea en esta ronda: {total_workers_en_ronda}")
                print("[📤] Tarea de minería entregada (desde RabbitMQ sin eliminar):", tarea)
                return jsonify(tarea), 200
            else:
                print("[🟡] No hay tareas disponibles.")
                return jsonify({"mensaje": "No hay tareas disponibles"}), 204
        
@app.route('/resultado', methods=['POST'])
def recibir_resultado_mineria():
    global mejor_bloque_encontrado_global, tarea_mineria_actual_global, tiempo_inicio_mineria_global, soluciones_exitosas_en_ronda
    
    bloque = request.get_json()
    print("Recibiendo resultado de minería: ", bloque)

    with lock_ronda_global:
        if not bloque or 'hash' not in bloque or 'nonce' not in bloque or 'direccion' not in bloque:
            print("Bloque inválido o incompleto")
            return jsonify({"error": "Bloque inválido o incompleto, falta clave_publica"}), 400

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

        # Verificar dificultad
        config = json.loads(redis_client.get("configuracion_blockchain"))
        dificultad = config.get("dificultad", "00")
        if not bloque["hash"].startswith("0" * len(dificultad)):
            print("Hash no cumple la dificultad.")
            return jsonify({"error": f"No cumple la dificultad ({dificultad})"}), 400

        soluciones_exitosas_en_ronda += 1
        print(f"Soluciones exitosas recibidas en esta ronda: {soluciones_exitosas_en_ronda}")

        if mejor_bloque_encontrado_global is None:
            # Este es el primer resultado válido recibido, lo aceptamos

            bloque_final_para_guardar = bloque_guardado.copy()
            bloque_final_para_guardar["hash"] = bloque["hash"]

            # Guardar bloque en Redis
            guardar_bloque_en_redis(bloque_final_para_guardar)

            enviar_recompensa(clave_publica)

            # Limpieza mempool
            for tx in bloque_guardado["transacciones"]:
                if "id" in tx:
                    redis_client.delete(f"transaccion:{tx['id']}")
                    redis_client.lrem("mempool", 0, tx["id"])
                else:
                    print(f"[*] Transacción sin 'id' (CoinBase). No eliminada del mempool. Transacción: {tx}")

            mejor_bloque_encontrado_global = {
                "bloque_validado": bloque_final_para_guardar,
                "hash_final": bloque_final_para_guardar["hash"],
                "clave_publica_minero": clave_publica
            }

            # Cancelar timers y finalizar ronda
            global timer_resultados_global, timer_ronda_global
            if timer_ronda_global:
                timer_ronda_global.cancel()
                timer_ronda_global = None
            if timer_resultados_global:
                timer_resultados_global.cancel()
                timer_resultados_global = None

            threading.Thread(target=manejar_fin_ronda).start()

            return jsonify({"mensaje": "Primer bloque válido agregado y recompensa asignada"}), 200

        else:
            # No es el primer resultado, validar pero no guardar ni recompensar
            print(f"Resultado válido recibido para bloque index {bloque_original_id}, pero no es el primero, no se guarda ni recompensa.")
            return jsonify({"mensaje": "Resultado válido pero bloque ya encontrado por otro minero"}), 200

def enviar_recompensa(clave_publica):
    config = json.loads(redis_client.get("configuracion_blockchain"))
    recompensa = config.get("premio_minado", 0)

    if recompensa <= 0:
        print("[⚠️] No se configuró una recompensa para el minado de bloques.")
        return

    transaccion_recompensa = {
        "de": "CoinBase",  # Origen ficticio para la recompensa
        "para": clave_publica,
        "monto": recompensa,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    bloque = {
        "index": redis_client.llen("blockchain"),
        "transacciones": [transaccion_recompensa],
        "prev_hash": obtener_ultimo_hash(),
    }
    bloque["hash"] = calcular_hash(bloque)

    redis_client.set(f"blockchain:{bloque['index']}", json.dumps(bloque))

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
    config_json = redis_client.get("configuracion_blockchain")
    if config_json:
        config = json.loads(config_json)
        return config.get("dificultad_inicial", "00")
    return "00"

def ajustar_dificultad():
    global configuracion_blockchain, total_workers_en_ronda, soluciones_exitosas_en_ronda
    config_blockchain = json.loads(redis_client.get("configuracion_blockchain"))
    dificultad_actual = config_blockchain.get("dificultad", "00")
    
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
        config_blockchain["dificultad"] = nueva_dificultad
        redis_client.set("configuracion_blockchain", json.dumps(config_blockchain))
        print(f"[DIFICULTAD] Nueva dificultad '{nueva_dificultad}' guardada en Redis.")
    else:
        print("[DIFICULTAD] Dificultad no ha cambiado.")

        # Resetear contadores para la próxima ronda
    total_workers_en_ronda = 0
    soluciones_exitosas_en_ronda = 0

def crear_bloque_genesis(config):
    print("[🌱] Creando bloque génesis...")
    transaccion_origen = {
        "de": "0" * 64,                                       # No hay origen en el bloque génesis
        "para": "CoinBase",                                   # Cuenta encargada de dar recompensas
        "monto": config["coins"],                             # Monto total de monedas en la blockchain
    }

    bloque = {
        "index": 0,
        "transacciones": [transaccion_origen],
        "prev_hash": "0" * 64,
        "nonce": 0,
        "configuracion": config,
        "dificultad": config.get("dificultad_inicial", "00"), # Dificultad inicial
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")       # Timestamp de creación de la tarea
    }
    redis_client.set(f"tarea_bloque:{bloque['index']}", json.dumps(bloque))
    return bloque

def enviar_a_minar(bloque):
    global tiempo_inicio_mineria_global

    print("[📤] Enviando bloque a minar...")

    # Guardar número de intento en Redis
    redis_client.set(f"intentos:{bloque['index']}", 1)

    tiempo_inicio_mineria_global = time.time()

    channel.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(bloque))
    print("[🚀] Bloque enviado a minar:", bloque)

def iniciar_timer_ronda():
    global timer_ronda_global, timer_resultados_global
    
    if timer_ronda_global:
        timer_ronda_global.cancel()
    if timer_resultados_global:
        timer_resultados_global.cancel()

    timer_ronda_global = threading.Timer(configuracion_blockchain["tiempo_ronda_seg"], iniciar_ventana_resultados)
    timer_ronda_global.start()
    print(f"[⏱️] Timer de minado de ronda iniciado por {configuracion_blockchain['tiempo_ronda_seg']} segundos.")

def iniciar_ventana_resultados():
    global timer_resultados_global
    with lock_ronda_global:
        if tarea_mineria_actual_global:
            print(f"[⏱️] Ronda de minado para bloque {tarea_mineria_actual_global['index']} finalizada.")
            print(f"[⏱️] Ventana de resultados abierta por {configuracion_blockchain['tiempo_resultados_seg']} segundos.")
            timer_resultados_global = threading.Timer(configuracion_blockchain["tiempo_resultados_seg"], manejar_fin_ronda)
            timer_resultados_global.start()
        else:
            print("[WARN] _iniciar_ventana_resultados llamado sin tarea_mineria_actual_global definida.")
            manejar_fin_ronda()

def manejar_fin_ronda():
    global timer_resultados_global, contador_intentos_mineria_global, tarea_mineria_actual_global, mejor_bloque_encontrado_global, tiempo_inicio_mineria_global
    global total_workers_en_ronda, soluciones_exitosas_en_ronda

    with lock_ronda_global:
        if timer_resultados_global:
            timer_resultados_global.cancel()
            timer_resultados_global = None

        print(f"[🏁] Ronda (incluida ventana de resultados) para bloque {tarea_mineria_actual_global['index'] if tarea_mineria_actual_global else 'N/A'} ha terminado.")
        
        ajustar_dificultad()

        if mejor_bloque_encontrado_global:
            print("[🎉] Se encontró un bloque válido durante la ronda. Procesando el mejor resultado.")
            procesar_bloque_encontrado(mejor_bloque_encontrado_global) # Llama a la nueva función
            tarea_mineria_actual_global = None
            contador_intentos_mineria_global = 0
            mejor_bloque_encontrado_global = None
        else:
            print("[😔] No se encontró ningún bloque válido o a tiempo en esta ronda.")
            contador_intentos_mineria_global += 1
            if contador_intentos_mineria_global <= configuracion_blockchain["max_intentos_mineria"]:
                print(f"[🔁] Reintentando bloque {tarea_mineria_actual_global['index']}. Intento {contador_intentos_mineria_global}.")
                rabbit_connection.basic_publish(exchange='', routing_key='mining_tasks', body=json.dumps(tarea_mineria_actual_global))
                tiempo_inicio_mineria_global = time.time()
                iniciar_timer_ronda()
            else:
                print(f"[❌] Máximo de intentos ({configuracion_blockchain['max_intentos_mineria']}) alcanzado para bloque {tarea_mineria_actual_global['index']}. Generando nuevo bloque.")
                tarea_mineria_actual_global = None
                contador_intentos_mineria_global = 0
                mejor_bloque_encontrado_global = None
                programar_creacion_proxima_ronda()

def programar_creacion_proxima_ronda():
    print(f"[⏸️] Esperando {configuracion_blockchain['cooldown_entre_rondas_seg']} segundos antes de la próxima ronda.")
    threading.Timer(configuracion_blockchain["cooldown_entre_rondas_seg"], crear_nueva_tarea_bloque).start()

def obtener_transacciones_para_bloque():
    ids_transacciones = redis_client.lrange("mempool", 0, -1)
    transacciones = []
    for id_tx in ids_transacciones:
        datos_tx = redis_client.get(f"transaccion:{id_tx}")
        if datos_tx:
            transacciones.append(json.loads(datos_tx))
    return transacciones

def crear_nueva_tarea_bloque(): 
    global tarea_mineria_actual_global, contador_intentos_mineria_global, tiempo_inicio_mineria_global
    with lock_ronda_global:
        print("[🔧] Preparando nuevo bloque para minar...")
        
        last_block_hash = obtener_ultimo_hash()
        next_index = redis_client.llen("blockchain")

        config_blockchain = json.loads(redis_client.get("configuracion_blockchain"))
        transacciones_para_bloque = obtener_transacciones_para_bloque()
        
        new_block = {
            "index": next_index,
            "transacciones": transacciones_para_bloque,
            "prev_hash": last_block_hash,
            "nonce": 0, # Placeholder, minero lo llenará
            "configuracion": config_blockchain,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S") # Timestamp de creación de la tarea
        }

        enviar_a_minar(new_block) # Reutiliza la función existente enviar_a_minar
        iniciar_timer_ronda()
        mejor_bloque_encontrado_global = None

def procesar_bloque_encontrado(datos_mejor_bloque):
    
    bloque_verificado = datos_mejor_bloque["bloque_validado"]
    # clave_publica_minero = datos_mejor_bloque["clave_publica_minero"] # No usada en esta iteración
    hash_final = datos_mejor_bloque["hash_final"]

    # No se añade recompensa en esta iteración.
    
    bloque_final = bloque_verificado
    bloque_final["hash"] = hash_final

    guardar_bloque_en_redis(bloque_final)

    # No se limpia la mempool en esta iteración.

    print("[🥳] Bloque minado con éxito y agregado a la blockchain (sin recompensas/limpieza de mempool por ahora).")
    programar_creacion_proxima_ronda()
    return True, {"mensaje": "Bloque agregado correctamente"}

def cargar_configuracion_blockchain():
    global configuracion_blockchain
    config_json = redis_client.get("configuracion_blockchain")
    print("[⚙️] Cargando configuración de la blockchain desde Redis.")
    configuracion_blockchain = json.loads(config_json)

def crear_configuracion():
    config = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"), # Hora de creación de la configuración
        "curva": "secp384r1",                       # Curva elíptica utilizada para las firmas
        "alg": "md5",                               # Algoritmo de hash utilizado
        "coins": 21000000,                          # Cantidad total de monedas en la blockchain
        "dificultad_inicial": "00",                 # Dificultad inicial de la minería
        "tiempo_ronda_seg": 120,                    # Ventana para obtener tareas de minería
        "tiempo_resultados_seg": 15,                # Ventana para recibir resultados de mineria
        "cooldown_entre_rondas_seg": 5,             # Tiempo de espera entre rondas
        "max_intentos_mineria": 3,                  # Máximo de veces que se reintenta una tarea si no se obtiene resultado
        "premio_minado": 500,                       # Recompensa por minar un bloque
    }
    redis_client.set("configuracion_blockchain", json.dumps(config))
    print("[⚙️] Configuración almacenada en Redis.")
    global configuracion_blockchain
    configuracion_blockchain = config
    return config

def inicializar_blockchain():
    print("[🔧] Inicializando blockchain...")
    if redis_client.llen("blockchain") == 0:
        print("[🧱] No se encontró blockchain. Generando configuración y bloque génesis...")
        config = crear_configuracion()
        bloque_genesis = crear_bloque_genesis(config)
        enviar_a_minar(bloque_genesis)
        iniciar_timer_ronda() 
        print("[🌱] Bloque génesis preparado para minar y ronda iniciada.")
    else:
        print("[✅] Blockchain ya existe.")
        cargar_configuracion_blockchain()
        programar_creacion_proxima_ronda()

if __name__ == "__main__":
    inicializar_blockchain()
    print("[🚀] Coordinador ejecutándose en http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)