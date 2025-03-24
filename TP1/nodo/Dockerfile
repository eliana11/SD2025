# Usamos una imagen base de Java
FROM openjdk:17-jdk-slim

# Copiar el código fuente
WORKDIR /app
COPY Nodo.java .

# Compilar el programa Java
RUN javac Nodo.java

# Ejecutar el programa Java cuando se inicie el contenedor
CMD ["java", "Nodo"]
