
FROM openjdk:17
WORKDIR /app

COPY src/ src/
COPY lib/json.jar lib/

RUN javac -cp lib/json.jar src/Tarea.java -d . && cp src/*.class .
CMD ["java", "-cp", ".:lib/json.jar", "Tarea"]
