Para levantar el servidor:

javac -cp .\TP2\servidor\lib\json-20250107.jar -d .\TP2\servidor\bin .\TP2\servidor\src\Servidor.java

java -cp ".\TP2\servidor\bin;.\TP2\servidor\lib\json-20250107.jar" src.Servidor

Una vez levantado, este va a esperar peticiones POST de http de la forma:

curl -X POST http://localhost:8000/getRemoteTask -H "Content-Type: application/json" -d "{\"nombreTarea\": \"sumar\", \"parametros\": [10, 20, 30]}"

Esta se puede editar para cambiar el nombre de la tarea (solamente hay dos disponibles: "sumar" y "multiplicar"), y los parametros (entre [], puede recibir n cualquiera de las dos tareas).


**Falta**:
- El servidor tambien tiene que dockerizarse.
- Se pueden hacer mas tareas.