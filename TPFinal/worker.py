import os
import requests
import time
import subprocess
import json
import tempfile

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

        print(f"[WORKER] Iniciando minero C++ para la tarea...")

        with tempfile.NamedTemporaryFile(mode='w+', delete=True, suffix='.json') as tmpfile:
            json.dump(tarea, tmpfile)
            tmpfile.flush()

            print(f"[WORKER] Archivo JSON temporal: {tmpfile.name}")
            print(f"[WORKER] Ejecutable minero: {MINERO_EJECUTABLE}")
            print(f"[WORKER] Comando completo: {[MINERO_EJECUTABLE, tmpfile.name, str(start_nonce), str(end_nonce)]}")
            print(f"[WORKER] Exists minero? {os.path.exists(MINERO_EJECUTABLE)}")
            print(f"[WORKER] Es ejecutable? {os.access(MINERO_EJECUTABLE, os.X_OK)}")

            resultado_proceso = subprocess.run(
                [MINERO_EJECUTABLE, tmpfile.name, str(start_nonce), str(end_nonce)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                text=True,
                check=True,
                timeout=300
            )

        salida_completa = resultado_proceso.stdout.strip()

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
        print(f"[WORKER] Log del minero:\n{e.output}")
        return {"status": "miner_execution_error", "return_code": e.returncode, "stderr": e.output.strip()}
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
