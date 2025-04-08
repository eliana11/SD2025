FROM openjdk:17
WORKDIR /app
COPY src/ src/
COPY ../lib lib/
RUN javac -cp lib/json-20250107.jar src/Servidor.java -d . && cp src/*.class .
CMD ["java", "-cp", ".:lib/json-20250107.jar", "src.Servidor"]

