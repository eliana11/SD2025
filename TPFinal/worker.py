import os
import requests
import time
import subprocess # Para ejecutar comandos externos
import json       # Para manejar datos JSON

COORDINADOR_URL = "http://coordinador:5000"

TIPO_MINERO = os.getenv("TIPO_MINERO", "cpu") 

if TIPO_MINERO == "cpu":
    MINERO_EJECUTABLE = "./HashMD5CPU" 
elif TIPO_MINERO == "gpu":
    MINERO_EJECUTABLE = "./HashFuerzaBrutaconLimites" 
else:
    print(f"[WORKER] Advertencia: Tipo de minero desconocido '{TIPO_MINERO}'. Usando el de CPU por defecto.")
    MINERO_EJECUTABLE = "./HashMD5CPU" 

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
    
def enviar_resultado_al_coordinador(resultado_minado):
    try:
        resp = requests.post(f"{COORDINADOR_URL}/solucion", json=resultado_minado)
        resp.raise_for_status() # Lanza una excepción si la respuesta no es 2xx
        print(f"[WORKER] Resultado enviado al Coordinador. Respuesta: {resp.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WORKER] Error al enviar resultado al Coordinador: {e}")
        # Si la respuesta del Coordinador es un error, muestra el contenido para depuración
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WORKER] Respuesta del Coordinador (ERROR): {e.response.text}")
        return False
    except Exception as e:
        print(f"[WORKER] Error inesperado al enviar resultado: {e}")
        return False
    
def ejecutar_minero_cuda(tarea):  
    try:
        # Convertimos la tarea (un diccionario Python) a una cadena JSON.
        tarea_json_str = json.dumps(tarea)

        print(f"[WORKER] Iniciando minero C++/CUDA para la tarea ID: {tarea.get('mining_tasks', 'N/A')}...")
        print(f"[WORKER] Enviando al minero: {tarea_json_str[:200]}..." ) # Imprimir un extracto para depuración

     
        # Ejemplo de comando: ./tu_minero_ejecutable "{'previous_hash': '...', 'difficulty': '00', 'transactions': [...]}"
        comando = [MINERO_EJECUTABLE, tarea_json_str]
        
        resultado_proceso = subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            check=True 
        )
        
        salida_minero = resultado_proceso.stdout.strip()
        # print(f"[WORKER] Salida STDERR del minero (si hay): {resultado_proceso.stderr.strip()}") # Para depuración
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
        print(f"[WORKER] Salida STDERR del minero: {e.stderr}")
        return {"status": "miner_execution_error", "return_code": e.returncode, "stderr": e.stderr.strip()}
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
        if tarea:
            print(f"[WORKER] Tarea recibida (PrevHash: {tarea.get('prev_hash', 'N/A')[:8]}..., Dificultad: {tarea.get('dificultad', 'N/A')}).")

            # Ejecutamos el minero C++/CUDA con la tarea recibida
            resultado_minero = ejecutar_minero_cuda(tarea)
            
            if resultado_minero:
                # Ahora usamos el campo 'status' del resultado del minero
                if resultado_minero.get("status") == "solution_found":
                    print(f"[WORKER] ¡SOLUCIÓN ENCONTRADA! Nonce: {resultado_minero.get('nonce_found')}, Hash: {resultado_minero.get('block_hash_result')[:8]}...")
                    enviar_resultado_al_coordinador(resultado_minero) # <--- ¡NUEVO! Enviar la solución
                elif resultado_minero.get("status") == "no_solution_found":
                    print("[WORKER] Minero finalizó rango sin encontrar solución.")
                    # Opcional: También podrías enviar esto al coordinador si quieres que registre el intento fallido
                    # enviar_resultado_al_coordinador(resultado_minero) 
                else:
                    print(f"[WORKER] Minero retornó estado desconocido o error: {resultado_minero.get('status')}")
                    # En este caso, el 'resultado_minero' ya contiene los detalles del error
                    enviar_resultado_al_coordinador(resultado_minero) # Reportar el error al Coordinador

            else:
                print("[WORKER] Fallo al obtener un resultado válido del minero.")
            
            # Pausa para evitar sobrecargar la CPU/Coordinador en un bucle apretado.
            time.sleep(1) 
        else:
            print("[WORKER] Sin tareas disponibles del Coordinador. Esperando...")
            time.sleep(5) # Pausa más larga cuando no hay tareas disponibles

if __name__ == "__main__":
    bucle_principal_worker()