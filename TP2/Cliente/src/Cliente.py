import requests
import json

def obtener_tareas_disponibles():
    url = "http://localhost:8000/tareasDisponibles"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        tareas = data.get("tareasDisponibles", [])

        print("🔍 Tareas disponibles en el servidor:")
        for i, tarea in enumerate(tareas):
            print(f"{i + 1}. {tarea}")

        return tareas

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con el servidor: {e}")
        return []
        
def enviar_tarea(nombre_tarea, parametros):
    url = "http://localhost:8000/getRemoteTask"
    payload = {
        "nombreTarea": nombre_tarea,
        "parametros": parametros  # una lista de valores
    }

    print("📤 Petición que se va a enviar:")
    print(f"URL: {url}")
    print("Body:")
    print(json.dumps(payload, indent=4))

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        print("✅ Respuesta del servidor:")
        print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar la tarea: {e}")



if __name__ == "__main__":
    tareas = obtener_tareas_disponibles()

    if tareas:
        opcion = input("🧠 Ingresá el número de la tarea que querés ejecutar: ")

        try:
            indice = int(opcion) - 1
            nombre_tarea = tareas[indice]
        except (ValueError, IndexError):
            print("❌ Opción inválida.")
            exit()

        parametros = []

        if nombre_tarea == "sumar":
            cantidad = int(input("¿Cuántos números querés sumar? "))
            for i in range(cantidad):
                n = int(input(f"Ingresá el número {i + 1}: "))
                parametros.append(n)

        elif nombre_tarea == "multiplicar":
            cantidad = int(input("¿Cuántos números querés multiplicar? "))
            for i in range(cantidad):
                n = int(input(f"Ingresá el número {i + 1}: "))
                parametros.append(n)

        else:
            print("⚠️ Tarea desconocida, se enviará sin parámetros extra.")

        enviar_tarea(nombre_tarea, parametros)
