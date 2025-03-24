# Usar una imagen con OpenJDK y Maven
FROM maven:3.8.1-openjdk-17-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar los archivos del proyecto (incluido pom.xml)
COPY . .

# Construir el proyecto usando Maven
RUN mvn clean install

# Ejecutar el programa Java
CMD ["java", "-cp", "target/tp1-1.0-SNAPSHOT-jar-with-dependencies.jar", "Nodo"]
