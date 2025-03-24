# Usa una imagen base con Java preinstalado
FROM openjdk:17


# Establece el directorio de trabajo en el contenedor
WORKDIR /app


# Copia el archivo JAR al contenedor
COPY . /app


# Compila el archivo Java
RUN javac Cliente.java


# Especifica el comando para ejecutar el JAR
CMD ["java", "Cliente"]
