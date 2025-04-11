Desarrollamos un sistema cliente-servidor para la ejecución de tareas genéricas utilizando tecnología HTTP y contenedores Docker

El servidor fue implementado en Java, utilizando el paquete com.sun.net.httpserver.* para crear un servidor HTTP que escucha en el puerto 8000.

Tiene dos endpoints:

    /getRemoteTask:

        Recibe solicitudes POST con los parámetros y nombre de la tarea.

        Determina el puerto interno y la imagen Docker que se necesita.

        Lanza un contenedor (si no está ya corriendo) con:

            Nombre dinámico (instancia_nombreTarea)

            Imagen correspondiente (bautista222221/tarea-nombre:v1)

            Red de Docker compartida para comunicación (tp2_red-tareas)

        Envía una solicitud al servicio tarea 

        Espera la respuesta del contenedor y la devuelve al cliente.

    /tareasDisponibles:

        Realiza una consulta a la API de Docker Hub sobre el repositorio del grupo.

        Filtra las imágenes que comienzan con tarea-.

        Devuelve un listado de tareas disponibles en formato JSON.

Este diseño desacopla completamente al servidor de las tareas específicas, permitiendo agregar nuevas sin modificar su lógica.

Para levantar el servidor:

docker compose build, docker compose up, sobre la ruta SD2025/TP2/

Una vez levantado, este va a esperar peticiones POST de http de la forma:

curl -X POST http://localhost:8000/getRemoteTask -H "Content-Type: application/json" -d "{\"nombreTarea\": \"sumar\", \"parametros\": [10, 20, 30]}"

Esta se puede editar para cambiar el nombre de la tarea (solamente hay dos disponibles: "sumar" y "multiplicar"), y los parametros (entre [], puede recibir n cualquiera de las dos tareas).

Para facilitar toda esta tarea, se creó el programa Cliente.py, que al tener un servidor ejecutandose, y usar este programa, informará al usuario que tareas se encuentras disponibles, para que elija una e ingrese los parametros.

El cliente tiene dos funcionalidades:

    Obtener las tareas disponibles: Consulta al servidor el listado de imágenes Docker publicadas en Docker Hub con prefijo "tarea-". Esto se hace a través del endpoint /tareasDisponibles.

    Enviar una tarea para su ejecución: Mediante una solicitud POST al endpoint /getRemoteTask, se envían:

        El nombre de la tarea (por ejemplo "sumar" o "multiplicar").

        Los parámetros necesarios (una lista de números).

Todo esto se empaqueta en formato JSON, cumpliendo con la consigna dada.

Cada tarea está empaquetada como una imagen Docker separada. Estas imágenes:

    Corren un servidor web que escucha en el puerto 8080.

    Implementan un endpoint con el nombre de la tarea.

    Reciben parámetros en formato JSON y responden con el resultado.

**Posible mejora**:
- Se pueden hacer mas tareas.

(Nota: El servidor obtiene las tareas disponibles por medio de una peticion http a docker, obteniendo aquellas que se encuentran subidas por bautista222221, filtrando por todos los contenedores que inicien por tarea-..., por lo que para crear alguna tarea nueva tiene realizarla bautista)
