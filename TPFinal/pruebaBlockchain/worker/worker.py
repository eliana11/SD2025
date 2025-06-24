import os
import requests
import time
import subprocess
import json
import ntplib
import tempfile
import sys
import math
from Usuario import UsuarioBlockchain
from datetime import datetime, timedelta

COORDINADOR_URL = None
MINERO_EJECUTABLE = "./MineroMD5CPU"
START_NONCE = 0
END_NONCE = -1
MARGEN_SINCRONIZACION = 0.5  # 500ms de tolerancia

usuario = None
configuracion = None
hora_ntp_cache = None
momento_local_cache = None
duracion_cache_segundos = 60  # Cachear durante 60 segundos

def obtener_hora_ntp():
    global hora_ntp_cache, momento_local_cache
    ahora_local = time.time()

    # Usar caché si no venció
    if hora_ntp_cache and momento_local_cache:
        if ahora_local - momento_local_cache < duracion_cache_segundos:
            diferencia = ahora_local - momento_local_cache
            return hora_ntp_cache + timedelta(seconds=diferencia)
    try:
        client = ntplib.NTPClient()
        ntp_server = configuracion.get("ntp_server", "ar.pool.ntp.org")
        response = client.request(ntp_server, version=3)
                
        # Actualizar caché
        hora_ntp_cache = datetime.fromtimestamp(response.tx_time)
        momento_local_cache = ahora_local
        print(f"[NTP] Hora sincronizada con {ntp_server}")

        return hora_ntp_cache
    
    except Exception as e:
        print(f"[NTP] Error al obtener hora NTP: {e}")
        return datetime.now()  # Fallback a la hora local si falla NTP
    
def esperar_y_obtener_estado(objetivo="ventana_tareas"):
    if not configuracion:
        print("[SYNC] No hay configuración, no puedo sincronizar.")
        time.sleep(5)
        return "desconocido"

    while True:
        tiempo_inicio = datetime.strptime(configuracion["time"], "%Y-%m-%d %H:%M:%S").timestamp()
        tiempo_actual = obtener_hora_ntp().timestamp()

        duracion_ronda = int(configuracion["tiempo_ronda_seg"])
        duracion_resultado = int(configuracion["tiempo_resultados_seg"])
        duracion_espera = int(configuracion["tiempo_espera_seg"])
        ciclo = duracion_ronda + duracion_resultado + duracion_espera

        transcurrido = tiempo_actual - tiempo_inicio
        momento_en_ciclo = transcurrido % ciclo

        if objetivo == "ventana_tareas":
            if momento_en_ciclo < duracion_ronda - MARGEN_SINCRONIZACION:
                return "ventana_tareas"
            falta = ciclo - momento_en_ciclo + 0.1

        elif objetivo == "ventana_resultados":
            inicio = duracion_ronda
            fin = duracion_ronda + duracion_resultado
            if inicio <= momento_en_ciclo < fin - MARGEN_SINCRONIZACION:
                return "ventana_resultados"
            elif momento_en_ciclo < inicio:
                falta = inicio - momento_en_ciclo + 0.1
            else:
                falta = ciclo - momento_en_ciclo + inicio + 0.1

        elif objetivo == "ventana_espera":
            inicio = duracion_ronda + duracion_resultado
            if momento_en_ciclo >= inicio - MARGEN_SINCRONIZACION:
                return "ventana_espera"
            else:
                falta = inicio - momento_en_ciclo + 0.1

        else:
            print("[SYNC] Objetivo inválido:", objetivo)
            return "desconocido"

        print(f"[SYNC] Esperando {math.ceil(falta)}s hasta próxima {objetivo}...")
        time.sleep(math.ceil(falta))

def obtener_configuracion():
    try:
        resp = requests.get(f"{COORDINADOR_URL}/configuracion")
        print("[WORKER] Respuesta /configuracion:", resp.status_code, resp.text)  # <- Añadido para debug
        if resp.status_code == 200:
            global configuracion
            configuracion = resp.json()
        else:
            print("[WORKER] Error al obtener configuración del Coordinador:", resp.status_code, resp.text)
            configuracion = None
    except Exception as e:
        print("[WORKER] Excepción al obtener configuración:", e)
        configuracion = None

def obtener_tarea():
    estado = esperar_y_obtener_estado("ventana_tareas")  # Espera garantizada
    if estado != "ventana_tareas":
        print("[WORKER] Aún no es la ventana de tareas. Reintentando más tarde...")
        return None
    try:
        resp = requests.get(f"{COORDINADOR_URL}/tarea")
        print("[WORKER] Respuesta /tarea:", resp.status_code, resp.text)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print("Error al obtener tarea:", e)
    return None

    
def enviar_resultado_al_coordinador(tarea_original, resultado_minado): 
    try:
        if resultado_minado.get("status") != "solution_found":
            print(f"[WORKER] No se envía bloque. Estado: {resultado_minado.get('status')}")
            return False

        # Esperar hasta ventana de resultados
        estado = esperar_y_obtener_estado("ventana_resultados")
        if estado != "ventana_resultados":
            print("[WORKER] Esperando apertura de ventana de resultados...")
            esperar_y_obtener_estado("ventana_resultados")

        bloque_final = tarea_original.copy()
        bloque_final["nonce"] = resultado_minado.get("nonce_found")
        bloque_final["hash"] = resultado_minado.get("block_hash_result")
        bloque_final["direccion"] = usuario.direccion

        resp = requests.post(f"{COORDINADOR_URL}/resultado", json=bloque_final)
        resp.raise_for_status()
        print(f"[WORKER] Bloque enviado exitosamente. Respuesta: {resp.json()}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[WORKER] Error al enviar resultado: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WORKER] Respuesta del Coordinador (ERROR): {e.response.text}")
        return False
    except Exception as e:
        print(f"[WORKER] Error inesperado al enviar resultado: {e}")
        return False

    
def ejecutar_minero_cuda(tarea):
    try:
        start_nonce = START_NONCE
        end_nonce = END_NONCE

        print(f"[WORKER] Iniciando minero C++ con rango nonce [{start_nonce}, {end_nonce}]...")

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=True) as tmp_json:
            json.dump(tarea, tmp_json)
            tmp_json.flush()

            if not os.path.exists(MINERO_EJECUTABLE):
                print(f"[WORKER] Error: Ejecutable no encontrado en '{MINERO_EJECUTABLE}'")
                return {"status": "miner_not_found"}

            if not os.access(MINERO_EJECUTABLE, os.X_OK):
                print(f"[WORKER] Error: Ejecutable sin permisos de ejecución: '{MINERO_EJECUTABLE}'")
                return {"status": "miner_no_exec_permission"}

            cmd = [os.path.abspath(MINERO_EJECUTABLE), tmp_json.name, str(start_nonce), str(end_nonce)]
            print(f"[WORKER] Ejecutando comando: {cmd}")

            resultado = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300
            )

            salida = resultado.stdout.strip()
            print(f"[WORKER] LOG completo del minero:\n{salida}")

            # Buscar la última línea que sea un JSON válido
            lineas = salida.splitlines()
            posibles_jsons = [l for l in lineas if l.strip().startswith('{') and l.strip().endswith('}')]
            if not posibles_jsons:
                print("[WORKER] No se encontró JSON válido en la salida del minero.")
                return {"status": "invalid_json_output", "details": salida}

            ultima_linea = posibles_jsons[-1].strip()
            print(f"[WORKER] Intentando parsear JSON:\n{ultima_linea}")

            salida_json = json.loads(ultima_linea)

            if "status" in salida_json:
                return salida_json
            else:
                return {"status": "malformed_miner_output", "details": ultima_linea}

    except subprocess.TimeoutExpired:
        print("[WORKER] Error: Tiempo de ejecución del minero excedido.")
        return {"status": "timeout"}
    except FileNotFoundError:
        print(f"[WORKER] Error: No se encontró el ejecutable '{MINERO_EJECUTABLE}'.")
        return {"status": "miner_not_found"}
    except Exception as e:
        print(f"[WORKER] Error inesperado al ejecutar el minero: {e}")
        return {"status": "unexpected_error", "details": str(e)}

# --- Bucle Principal del Worker ---
def bucle_principal_worker():
    print("[WORKER] Worker de minería iniciado. Conectando al Coordinador en", COORDINADOR_URL)
    while True:
        tarea = obtener_tarea()

        if tarea and all(k in tarea for k in ["prev_hash", "transacciones", "index", "dificultad"]):
            print(f"[WORKER] Tarea recibida: {tarea}")
            resultado_minero = ejecutar_minero_cuda(tarea)

            if resultado_minero:
                if resultado_minero.get("status") == "solution_found":
                    print(f"[WORKER] ¡SOLUCIÓN ENCONTRADA! Nonce: {resultado_minero.get('nonce_found')}, Hash: {resultado_minero.get('block_hash_result')[:8]}...")
                    enviar_resultado_al_coordinador(tarea, resultado_minero)
                elif resultado_minero.get("status") == "no_solution_found":
                    print("[WORKER] Minero finalizó sin encontrar solución.")
                else:
                    print(f"[WORKER] Error del minero: {resultado_minero.get('status')} ({resultado_minero.get('details', 'N/A')})")
            else:
                print("[WORKER] Resultado inválido del minero.")
        else:
            print("[WORKER] Sin tareas válidas o fuera de ventana. Esperando...")
            time.sleep(5)  # Espera antes de volver a intentar obtener una tarea


def main():
    if len(sys.argv) < 3:
        print("Uso: python worker.py <NOMBRE_WORKER> <URL_COORDINADOR>")
        sys.exit(1)

    global usuario, COORDINADOR_URL, configuracion
    nombre_worker = sys.argv[1]
    COORDINADOR_URL = sys.argv[2]

    usuario = UsuarioBlockchain(nombre=nombre_worker)
    print(f"[WORKER] Worker '{nombre_worker}' registrado con dirección {usuario.direccion}.")

    print("[WORKER] Obteniendo configuración de la blockchain...")
    obtener_configuracion()

    bucle_principal_worker()

if __name__ == "__main__":
    main()

