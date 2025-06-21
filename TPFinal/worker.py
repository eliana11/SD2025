import os
import requests
import time
import subprocess # Para ejecutar comandos externos
import json       # Para manejar datos JSON
from subprocess import PIPE

COORDINADOR_URL = "http://localhost:5000"

MINERO_EJECUTABLE = "./MineroMD5CPU" 


def obtener_tarea():
    try:
        resp = requests.get(f"{COORDINADOR_URL}/tarea")
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
            bloque_final = {
                "index": tarea_original.get("index"),
                "transacciones": tarea_original.get("transacciones"),
                "prev_hash": tarea_original.get("prev_hash"),
                "timestamp": tarea_original.get("timestamp"), # Usamos el timestamp de la tarea original
                "nonce": resultado_minado.get("nonce_found"), # El nonce encontrado por el minero
                "hash": resultado_minado.get("block_hash_result") # El hash resultante del bloque
            }
        else:
            print(f"[WORKER] No se envía bloque al Coordinador porque el minero no encontró una solución o hubo un error: {resultado_minado.get('status')}")
            return False
        resp = requests.post(f"{COORDINADOR_URL}/resultado", json=bloque_final)
        resp.raise_for_status() # Lanza una excepción si la respuesta no es 2xx
        print(f"[WORKER] Bloque minado enviado al Coordinador. Respuesta: {resp.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WORKER] Error al enviar resultado (bloque) al Coordinador: {e}")
        # Si la respuesta del Coordinador es un error, muestra el contenido para depuración
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WORKER] Respuesta del Coordinador (ERROR): {e.response.text}")
        return False
    except Exception as e:
        print(f"[WORKER] Error inesperado al enviar resultado (bloque): {e}")
        return False
    
def ejecutar_minero_cuda(tarea):  
    try:
        # Convertimos la tarea (un diccionario Python) a una cadena JSON.
        tarea_json_str = json.dumps(tarea)

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

       
        try:
            minero_resultado = json.loads(salida_minero)
            # Asegurarse de que los campos esperados estén presentes
            if "status" in minero_resultado and "block_hash_result" in minero_resultado:
                return minero_resultado
            else:
                print(f"[WORKER] Advertencia: La salida del minero no contiene el campo 'status'. Salida: {salida_minero}")
                return {"status": "malformed_miner_output", "details": salida_minero} # Devolvemos un error estructurado
        except json.JSONDecodeError:
            print(f"[WORKER] Error: La salida del minero C++/CUDA no es un JSON válido: {salida_minero}")
            return {"status": "invalid_json_output", "details": salida_minero}


    except subprocess.CalledProcessError as e:
        print(f"[WORKER] Error al ejecutar el minero C++/CUDA (código {e.returncode}): {e}")
        # Aseguramos que el stderr también se decodifique correctamente para el log
        print(f"[WORKER] Salida STDERR del minero: {e.stderr.decode('utf-8').strip()}")
        return {"status": "miner_execution_error", "return_code": e.returncode, "stderr": e.stderr.decode('utf-8').strip()}
    except FileNotFoundError:
        print(f"[WORKER] Error: El ejecutable del minero no se encontró en la ruta '{MINERO_EJECUTABLE}'.")
        return {"status": "miner_not_found"}
    except Exception as e:
        print(f"[WORKER] Error inesperado en 'ejecutar_minero_cuda': {e}")
        return {"status": "unexpected_error", "details": str(e)}
    
# --- Bucle Principal del Worker ---
def bucle_principal_worker():
    print("[WORKER] Worker de minería iniciado. Conectando al Coordinador en", COORDINADOR_URL)
    while True:
        tarea = obtener_tarea()
        if "bloque" in tarea:
            tarea = tarea["bloque"]  # Asegurarse de que estamos trabajando con el bloque correcto
            if not all(k in tarea for k in ["prev_hash", "transacciones", "dificultad", "start_nonce", "end_nonce"]):
                print(f"[WORKER] Tarea recibida incompleta o con formato inesperado. Saltando. Tarea: {tarea}")
                time.sleep(1)
                continue

            print(f"[WORKER] Tarea recibida (Index: {tarea.get('index')}, PrevHash: {tarea.get('prev_hash', 'N/A')[:8]}..., Dificultad: {tarea.get('dificultad', 'N/A')}).")

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

