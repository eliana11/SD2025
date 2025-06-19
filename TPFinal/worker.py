import requests

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
    
while True:
    tarea = obtener_tarea()
    if tarea:
        print("[WORKER] Tarea recibida:", tarea)
        # Iniciar minado con esa tarea
    else:
        print("[WORKER] Sin tareas. Esperando...")
        time.sleep(2)