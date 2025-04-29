import cv2
import numpy as np
import os
import time

def sobel(imagen):
    sobelx = cv2.Sobel(imagen, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(imagen, cv2.CV_64F, 0, 1, ksize=3)
    magnitud = cv2.magnitude(sobelx, sobely)
    resultado = cv2.convertScaleAbs(magnitud)
    return resultado

def main():
    worker_id = int(os.getenv("WORKER_ID", -1))
    if worker_id == -1:
        print("WORKER_ID no definido")
        return

    path = f"output/chunk_{worker_id}.jpg"
    while not os.path.exists(path):
        time.sleep(0.5)

    imagen = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    resultado = sobel(imagen)
    cv2.imwrite(f"output/result_{worker_id}.jpg", resultado)
    print(f"Worker {worker_id} procesó su parte.")

if __name__ == "__main__":
    main()
