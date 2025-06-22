import os
import requests
import time
import subprocess # Para ejecutar comandos externos
import json       # Para manejar datos JSON
from subprocess import PIPE

COORDINADOR_URL = "http://localhost:5000"
MINERO_EJECUTABLE = "./MineroMD5CPU.exe"
START_NONCE = 0
END_NONCE = 1000000

def obtener_tarea():
    try:
        resp = requests.get(f"{COORDINADOR_URL}/tarea")
        print("[WORKER] Respuesta /tarea:", resp.status_code, resp.text)  # <- Añadido para debug
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception as e:
        print("Error al obtener tarea:", e)
        return None
    
def enviar_resultado_al_coordinador(tarea_original, resultado_minado): 
    try:
        if resultado_minado.get("status") == "solution_found":
            # Enviar todo el bloque completo, con nonce y hash calculados
            bloque_final = tarea_original.copy()
            bloque_final["nonce"] = resultado_minado.get("nonce_found")
            bloque_final["hash"] = resultado_minado.get("block_hash_result")
        else:
            print(f"[WORKER] No se envía bloque al Coordinador porque el minero no encontró solución o hubo un error: {resultado_minado.get('status')}")
            return False
        
        resp = requests.post(f"{COORDINADOR_URL}/resultado", json=bloque_final)
        resp.raise_for_status()
        print(f"[WORKER] Bloque minado enviado al Coordinador. Respuesta: {resp.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WORKER] Error al enviar resultado (bloque) al Coordinador: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WORKER] Respuesta del Coordinador (ERROR): {e.response.text}")
        return False
    except Exception as e:
        print(f"[WORKER] Error inesperado al enviar resultado (bloque): {e}")
        return False
    
def ejecutar_minero_cuda(tarea):
    try:
        start_nonce = START_NONCE
        end_nonce = END_NONCE

        print(f"[WORKER] Iniciando minero C++/CUDA para la tarea ID: {tarea.get('mining_tasks', 'N/A')}...")
        print(f"[WORKER] Enviando al minero (extracto): {tarea_json_str[:200]}...") # Imprimir un extracto para depuración

        # Ejemplo de comando: ./tu_minero_ejecutable "{'previous_hash': '...', 'difficulty': '00', 'transactions': [...]}"
        comando = [MINERO_EJECUTABLE, tarea_json_str]
        
        # --- CAMBIOS AQUÍ para compatibilidad con Python 3.6 ---
        resultado_proceso = subprocess.run(
            comando, 
            stdout=PIPE,    # Reemplaza capture_output=True
            stderr=PIPE,    # Reemplaza capture_output=True
            check=True,
            timeout=300 
        )
        
        # Decodificamos la salida manualmente, ya que text=True no está disponible o es problemático en 3.6
        salida_minero = resultado_proceso.stdout.decode('utf-8').strip()
        stderr_minero = resultado_proceso.stderr.decode('utf-8').strip()
        # --- FIN DE CAMBIOS ---
        
        # print(f"[WORKER] Salida STDERR del minero (si hay): {stderr_minero}") # Para depuración
        # print(f"[WORKER] Salida STDOUT del minero: {salida_minero}") # Para depuración

        print("🪵 [WORKER] Log completo del minero:\n", salida_completa)

        try:
            minero_resultado = json.loads(salida_completa)
            print("[WORKER] Resultado JSON obtenido:", minero_resultado)
            if "status" in minero_resultado and "block_hash_result" in minero_resultado:
                return minero_resultado
            else:
                print("[WORKER] Advertencia: La salida del minero no contiene 'status' o 'block_hash_result'")
                return {"status": "malformed_miner_output", "details": salida_completa}
        except json.JSONDecodeError:
            print("[WORKER] Error: La salida del minero no es un JSON válido.")
            return {"status": "invalid_json_output", "details": salida_completa}

    except subprocess.CalledProcessError as e:
        print(f"[WORKER] Error al ejecutar el minero (código {e.returncode}): {e}")
        # Aseguramos que el stderr también se decodifique correctamente para el log
        print(f"[WORKER] Log del minero:\n{e.output.decode('utf-8').strip()}")
        return {"status": "miner_execution_error", "return_code": e.returncode, "stderr": e.output.decode('utf-8').strip()}
    except FileNotFoundError:
        print(f"[WORKER] Error: El ejecutable del minero no se encontró en '{MINERO_EJECUTABLE}'.")
        return {"status": "miner_not_found"}
    except Exception as e:
        print(f"[WORKER] Error inesperado: {e}")
        return {"status": "unexpected_error", "details": str(e)}
    
# --- Bucle Principal del Worker ---
def bucle_principal_worker():
    print("[WORKER] Worker de minería iniciado. Conectando al Coordinador en", COORDINADOR_URL)
    while True:
        tarea = obtener_tarea()
        if tarea and all(k in tarea for k in ["prev_hash", "transacciones", "index", "configuracion"]) and "dificultad" in tarea["configuracion"]:
            print(f"[WORKER] Tarea recibida {tarea}).")

            resultado_minero = ejecutar_minero_cuda(tarea)

            if resultado_minero:
                if resultado_minero.get("status") == "solution_found":
                    print(f"[WORKER] ¡SOLUCIÓN ENCONTRADA! Nonce: {resultado_minero.get('nonce_found')}, Hash: {resultado_minero.get('block_hash_result')[:8]}...")
                    enviar_resultado_al_coordinador(tarea, resultado_minero)
                elif resultado_minero.get("status") == "no_solution_found":
                    print("[WORKER] Minero finalizó rango sin encontrar solución.")
                else:
                    print(f"[WORKER] Minero retornó estado desconocido o error: {resultado_minero.get('status')}. Detalles: {resultado_minero.get('details', 'N/A')}")
            else:
                print("[WORKER] Fallo al obtener un resultado válido del minero.")

            time.sleep(1)
        else:
            print("[WORKER] Sin tareas disponibles del Coordinador. Esperando...")
            time.sleep(5)

if __name__ == "__main__":
    bucle_principal_worker()
