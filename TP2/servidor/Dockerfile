FROM alpine/java:22-jdk
WORKDIR /app
COPY bin/src/ /app/bin/src/
COPY lib/json-20250107.jar /app/lib/json-20250107.jar
EXPOSE 8000
CMD ["java", "-cp", "/app/bin:/app/lib/json-20250107.jar", "src.Servidor"]