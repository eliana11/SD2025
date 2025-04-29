import cv2
import numpy as np
import sys
import os
import time

def dividir_imagen(imagen, n):
    alto = imagen.shape[0]
    partes = []
    paso = alto // n
    for i in range(n):
        inicio = i * paso
        fin = (i + 1) * paso if i != n - 1 else alto
        partes.append(imagen[inicio:fin])
    return partes

def unir_imagenes(partes):
    return np.vstack(partes)

def guardar_partes(partes):
    for idx, parte in enumerate(partes):
        cv2.imwrite(f"output/chunk_{idx}.jpg", parte)

def esperar_resultados(n):
    partes_procesadas = []
    for i in range(n):
        path = f"output/result_{i}.jpg"
        while not os.path.exists(path):
            time.sleep(0.5)
        parte = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        partes_procesadas.append(parte)
    return partes_procesadas

def main():
    if len(sys.argv) < 4:
        print("Uso: python coordinador.py <input> <output> <n_procesos>")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    n = int(sys.argv[3])

    os.makedirs("output", exist_ok=True)

    img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    partes = dividir_imagen(img, n)
    guardar_partes(partes)
    print("Partes guardadas. Esperando resultados...")

    partes_filtradas = esperar_resultados(n)
    resultado = unir_imagenes(partes_filtradas)
    cv2.imwrite(output_path, resultado)
    print(f"Imagen final guardada como {output_path}")

if __name__ == "__main__":
    main()
