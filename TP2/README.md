Para levantar el servidor:

docker compose build, docker compose up, sobre la ruta SD2025/TP2/

Una vez levantado, este va a esperar peticiones POST de http de la forma:

curl -X POST http://localhost:8000/getRemoteTask -H "Content-Type: application/json" -d "{\"nombreTarea\": \"sumar\", \"parametros\": [10, 20, 30]}"

Esta se puede editar para cambiar el nombre de la tarea (solamente hay dos disponibles: "sumar" y "multiplicar"), y los parametros (entre [], puede recibir n cualquiera de las dos tareas).

Para facilitar toda esta tarea, se creó el programa Cliente.py, que al tener un servidor ejecutandose, y usar este programa, informará al usuario que tareas se encuentras disponibles, para que elija una e ingrese los parametros.


**Falta**:
- Se pueden hacer mas tareas.

(Nota: El servidor obtiene las tareas disponibles por medio de una peticion http a docker, obteniendo aquellas que se encuentran subidas por bautista222221, filtrando por todos los contenedores que inicien por tarea-..., por lo que para crear alguna tarea nueva tengo que hacerlo yo (bautista))