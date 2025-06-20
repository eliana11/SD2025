import requests
import time
import subprocess # Para ejecutar comandos externos
import json       # Para manejar datos JSON


def obtener_tarea():
    try:
        resp = requests.get("http://coordinador:5000/tarea")
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception as e:
        print("Error al obtener tarea:", e)
        return None
    
#while True:
    tarea = obtener_tarea()
    if tarea:
        print("[WORKER] Tarea recibida:", tarea)
        # Iniciar minado con esa tarea
    else:
        print("[WORKER] Sin tareas. Esperando...")
        time.sleep(2)


def ejecutar_minero_cuda(tarea):  
    try:
        # Convertimos la tarea (un diccionario Python) a una cadena JSON.
        tarea_json_str = json.dumps(tarea)

        # Comando para ejecutar tu minero C++/CUDA.
     
        # Ejemplo de comando: ./tu_minero_ejecutable "{'previous_hash': '...', 'difficulty': '00', 'transactions': [...]}"
        comando = [MINER_EXECUTABLE, tarea_json_str]
        
        print(f"[WORKER] Iniciando minero C++/CUDA para la tarea ID: {tarea.get('mining_task_id', 'N/A')}...")
        
        # Ejecutamos el minero y capturamos su salida
        # 'check=True' hará que Python genere un error si el minero C++/CUDA devuelve un código de salida distinto de 0
        resultado_proceso = subprocess.run(comando, capture_output=True, text=True, check=True)
        
        # El output de tu minero C++/CUDA (lo que imprima a la consola)
        salida_minero = resultado_proceso.stdout.strip()
        print(f"[WORKER] Salida del minero C++/CUDA: {salida_minero}")

        # PARSEAR la salida de tu minero C++/CUDA.
        # Por ejemplo, si tu minero C++/CUDA imprime un JSON como: {"nonce_found": 123, "block_hash_result": "000abc123..."}
        try:
            minero_resultado = json.loads(salida_minero)
            # Asegurarse de que los campos esperados estén presentes
            if "nonce_found" in minero_resultado and "block_hash_result" in minero_resultado:
                return minero_resultado
            else:
                print(f"[WORKER] Advertencia: El minero no retornó los campos esperados en JSON. Salida: {salida_minero}")
                return None
        except json.JSONDecodeError:
            print(f"[WORKER] Error: La salida del minero C++/CUDA no es un JSON válido: {salida_minero}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"[WORKER] Error al ejecutar el minero C++/CUDA (código {e.returncode}): {e}")
        print(f"[WORKER] Salida STDERR del minero: {e.stderr}")
        return None
    except Exception as e:
        print(f"[WORKER] Error inesperado en 'ejecutar_minero_cuda': {e}")
        return None

# --- Bucle Principal del Worker ---
def bucle_principal_worker():
    while True:
        tarea = obtener_tarea()
        if tarea:
            # Ejecutamos el minero C++/CUDA con la tarea recibida
            resultado_minero = ejecutar_minero_cuda(tarea)
            
            if resultado_minero:
                
                print(f"[WORKER] Solución encontrada: Nonce={resultado_minero.get('nonce_found')}, Hash={resultado_minero.get('block_hash_result')}")
                
            else:
                print("[WORKER] El minero no encontró una solución para esta tarea o hubo un error durante su ejecución.")
            
            # Después de intentar minar, con o sin éxito, esperamos un poco antes de pedir otra tarea.
            time.sleep(1) # Pequeña pausa para no sobrecargar el Coordinador con peticiones
        else:
            print("[WORKER] Sin tareas. Esperando...")
            time.sleep(2) # Pausa más larga cuando no hay tareas disponibles

if __name__ == "__main__":
    bucle_principal_worker()

