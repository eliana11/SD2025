# Usar una imagen con OpenJDK y Maven
FROM openjdk:17-jdk-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar los archivos del proyecto (incluido pom.xml)
COPY /target/nodo.jar /app/nodo.jar
COPY /lib/gson-2.12.1.jar /app/gson.jar

# Exponer el puerto 8080
EXPOSE 8080

# Ejecutar el programa Java
CMD ["java", "-cp", "nodo.jar:gson.jar", "NodoD", "8080"]