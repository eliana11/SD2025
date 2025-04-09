FROM alpine/java:22-jdk
WORKDIR /app
COPY bin/ /app/bin/src/
COPY lib/json-20250107.jar /app/lib/json-20250107.jar
EXPOSE 8001
CMD ["java", "-cp", "/app/bin:/app/lib/json-20250107.jar", "src.Tarea"]