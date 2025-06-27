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
MINERO_EJECUTABLE = "./MineroMD5"
START_NONCE = 0
END_NONCE = -1

usuario = None
configuracion = None
hora_ntp_cache = None
momento_local_cache = None
    
def obtener_estado_coordinador():
    try:
        resp = requests.get(f"{COORDINADOR_URL}/estado")
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[WORKER] Error al obtener estado del coordinador: {resp.status_code}, {resp.text}")
            sys.stdout.flush()
            return None
    except Exception as e:
        print(f"[WORKER] Excepción al consultar /estado: {e}")
        sys.stdout.flush()
        return None
    
def esperar_y_obtener_estado(objetivo="ventana_tareas"):
    if not configuracion:
        print("[SYNC] No hay configuración. Esperando antes de reintentar...")
        sys.stdout.flush()
        time.sleep(5)
        return "desconocido"

    print(f"[SYNC] Esperando cambio a '{objetivo}'...")
    sys.stdout.flush()
    while True:
        estado = obtener_estado_coordinador()
        if not estado:
            print("[SYNC] No se pudo obtener estado del coordinador. Reintentando en 5s...")
            sys.stdout.flush()
            time.sleep(5)
            continue

        estado_actual = estado.get("estado")
        tiempo_restante = estado.get("tiempo_restante", 0)

        if estado_actual == objetivo:
            print(f"[SYNC] Estado alcanzado: '{objetivo}' ✅")
            sys.stdout.flush()
            return objetivo

        print(f"[SYNC] Estado actual: '{estado_actual}'. Esperando a '{objetivo}' ({tiempo_restante:.2f}s restantes)...")
        sys.stdout.flush()
        # Esperar de forma más granular (máx s)
        time.sleep(min(5, tiempo_restante))

def obtener_configuracion():
    try:
        resp = requests.get(f"{COORDINADOR_URL}/configuracion")
        print("[WORKER] Respuesta /configuracion:", resp.status_code, resp.text)  # <- Añadido para debug
        sys.stdout.flush()
        if resp.status_code == 200:
            global configuracion
            configuracion = resp.json()
        else:
            print("[WORKER] Error al obtener configuración del Coordinador:", resp.status_code, resp.text)
            sys.stdout.flush()
            configuracion = None
    except Exception as e:
        print("[WORKER] Excepción al obtener configuración:", e)
        sys.stdout.flush()
        configuracion = None

def obtener_tarea():
    estado = esperar_y_obtener_estado("ventana_tareas")  # Espera garantizada
    if estado != "ventana_tareas":
        sys.stdout.flush()
        print("[WORKER] Aún no es la ventana de tareas. Reintentando más tarde...")
        return None
    try:
        resp = requests.get(f"{COORDINADOR_URL}/tarea")
        print("[WORKER] Respuesta /tarea:", resp.status_code, resp.text)
        sys.stdout.flush()
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print("Error al obtener tarea:", e)
        sys.stdout.flush()
    return None

    
def enviar_resultado_al_coordinador(tarea_original, resultado_minado): 
    try:
        if resultado_minado.get("status") != "solution_found":
            print(f"[WORKER] No se envía bloque. Estado: {resultado_minado.get('status')}")
            sys.stdout.flush()
            return False

        esperar_y_obtener_estado("ventana_resultados")

        bloque_final = tarea_original.copy()
        bloque_final["nonce"] = resultado_minado.get("nonce_found")
        bloque_final["hash"] = resultado_minado.get("block_hash_result")
        bloque_final["direccion"] = usuario.direccion

        resp = requests.post(f"{COORDINADOR_URL}/resultado", json=bloque_final)
        resp.raise_for_status()
        print(f"[WORKER] Bloque enviado exitosamente. Respuesta: {resp.json()}")
        sys.stdout.flush()
        return True

    except requests.exceptions.RequestException as e:
        print(f"[WORKER] Error al enviar resultado: {e}")
        sys.stdout.flush()
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WORKER] Respuesta del Coordinador (ERROR): {e.response.text}")
            sys.stdout.flush()
        return False
    except Exception as e:
        print(f"[WORKER] Error inesperado al enviar resultado: {e}")
        sys.stdout.flush()
        return False

    
def ejecutar_minero_cuda(tarea):
    try:
        start_nonce = START_NONCE
        end_nonce = END_NONCE

        print(f"[WORKER] Iniciando minero C++ con rango nonce [{start_nonce}, {end_nonce}]...")
        sys.stdout.flush()
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=True) as tmp_json:
            json.dump(tarea, tmp_json)
            tmp_json.flush()

            if not os.path.exists(MINERO_EJECUTABLE):
                print(f"[WORKER] Error: Ejecutable no encontrado en '{MINERO_EJECUTABLE}'")
                sys.stdout.flush()
                return {"status": "miner_not_found"}

            if not os.access(MINERO_EJECUTABLE, os.X_OK):
                print(f"[WORKER] Error: Ejecutable sin permisos de ejecución: '{MINERO_EJECUTABLE}'")
                sys.stdout.flush()
                return {"status": "miner_no_exec_permission"}

            cmd = [os.path.abspath(MINERO_EJECUTABLE), tmp_json.name, str(start_nonce), str(end_nonce)]
            print(f"[WORKER] Ejecutando comando: {cmd}")
            sys.stdout.flush()
            resultado = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300
            )

            salida = resultado.stdout.strip()
            print(f"[WORKER] LOG completo del minero:\n{salida}")
            sys.stdout.flush()

            # Buscar la última línea que sea un JSON válido
            lineas = salida.splitlines()
            posibles_jsons = [l for l in lineas if l.strip().startswith('{') and l.strip().endswith('}')]
            if not posibles_jsons:
                print("[WORKER] No se encontró JSON válido en la salida del minero.")
                sys.stdout.flush()
                return {"status": "invalid_json_output", "details": salida}

            ultima_linea = posibles_jsons[-1].strip()
            print(f"[WORKER] Intentando parsear JSON:\n{ultima_linea}")
            sys.stdout.flush()
            salida_json = json.loads(ultima_linea)

            if "status" in salida_json:
                return salida_json
            else:
                return {"status": "malformed_miner_output", "details": ultima_linea}

    except subprocess.TimeoutExpired:
        print("[WORKER] Error: Tiempo de ejecución del minero excedido.")
        sys.stdout.flush()
        return {"status": "timeout"}
    except FileNotFoundError:
        print(f"[WORKER] Error: No se encontró el ejecutable '{MINERO_EJECUTABLE}'.")
        sys.stdout.flush()
        return {"status": "miner_not_found"}
    except Exception as e:
        print(f"[WORKER] Error inesperado al ejecutar el minero: {e}")
        sys.stdout.flush()
        return {"status": "unexpected_error", "details": str(e)}

# --- Bucle Principal del Worker ---
def bucle_principal_worker():
    print("[WORKER] Worker de minería iniciado. Conectando al Coordinador en", COORDINADOR_URL)
    sys.stdout.flush()
    while True:
        tarea = obtener_tarea()

        if tarea and all(k in tarea for k in ["prev_hash", "transacciones", "index", "dificultad"]):
            print(f"[WORKER] Tarea recibida: {tarea}")
            sys.stdout.flush()
            resultado_minero = ejecutar_minero_cuda(tarea)

            if resultado_minero:
                if resultado_minero.get("status") == "solution_found":
                    print(f"[WORKER] ¡SOLUCIÓN ENCONTRADA! Nonce: {resultado_minero.get('nonce_found')}, Hash: {resultado_minero.get('block_hash_result')[:8]}...")
                    sys.stdout.flush()
                    enviar_resultado_al_coordinador(tarea, resultado_minero)
                elif resultado_minero.get("status") == "no_solution_found":
                    print("[WORKER] Minero finalizó sin encontrar solución.")
                    sys.stdout.flush()
                else:
                    print(f"[WORKER] Error del minero: {resultado_minero.get('status')} ({resultado_minero.get('details', 'N/A')})")
                    sys.stdout.flush()
            else:
                print("[WORKER] Resultado inválido del minero.")
                sys.stdout.flush()
        else:
            print("[WORKER] Sin tareas válidas o fuera de ventana. Esperando...")
            sys.stdout.flush()
            time.sleep(5)  # Espera antes de volver a intentar obtener una tarea


def main():
    if len(sys.argv) < 3:
        print("Uso: python worker.py <NOMBRE_WORKER> <URL_COORDINADOR>")
        sys.stdout.flush()
        sys.exit(1)

    global usuario, COORDINADOR_URL, configuracion
    nombre_worker = sys.argv[1]
    COORDINADOR_URL = sys.argv[2]

    usuario = UsuarioBlockchain(nombre=nombre_worker)
    print(f"[WORKER] Worker '{nombre_worker}' registrado con dirección {usuario.direccion}.")
    sys.stdout.flush()
    print("[WORKER] Obteniendo configuración de la blockchain...")
    sys.stdout.flush()
    obtener_configuracion()

    bucle_principal_worker()

if __name__ == "__main__":
    main()