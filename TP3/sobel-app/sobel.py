import cv2
import sys

def aplicar_sobel(imagen_path, salida_path):
    img = cv2.imread(imagen_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"No se pudo leer la imagen: {imagen_path}")
        sys.exit(1)

    sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=5)
    sobel = cv2.magnitude(sobelx, sobely)

    # Escalar a 0–255 para guardar como imagen visible
    sobel = cv2.convertScaleAbs(sobel)

    cv2.imwrite(salida_path, sobel)
    print(f"Imagen procesada guardada en: {salida_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python sobel.py imagen_entrada.jpg imagen_salida.jpg")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]

    aplicar_sobel(input_path, output_path)
