Desarrollamos un sistema cliente-servidor para la ejecución de tareas genéricas utilizando tecnología HTTP y contenedores Docker

Diseño de Arquitectura

El sistema se compone de tres partes principales:

    Cliente: Interfaz que consulta tareas disponibles y ejecuta una seleccionada.

    Servidor: Recibe la solicitud, levanta un contenedor Docker con la tarea y delega la ejecución.

    Servicio Tarea: Imagen Docker con un servidor web que ejecuta la lógica de una tarea.

Implementación del Servidor

    Implementado en Java utilizando com.sun.net.httpserver.*

    Corre en el puerto 8000.

    Expuestos dos endpoints:

/getRemoteTask

    Método: POST

    Entrada: JSON con nombreTarea y parametros.

    Procesos:

        Determina el puerto interno y la imagen Docker.

        Lanza el contenedor si no está corriendo (usando docker run con nombre dinámico, imagen, y red tp2_red-tareas).

        Envía la solicitud HTTP al contenedor (puerto 8080).

        Devuelve la respuesta al cliente.

/tareasDisponibles

    Método: GET

    Consulta a Docker Hub por imágenes publicadas por bautista222221 con el prefijo tarea-.

    Devuelve un JSON con la lista de tareas disponibles.

Este diseño desacopla completamente al servidor de las tareas específicas, permitiendo agregar nuevas sin modificar su lógica.

Para levantar el servidor:

docker compose build, docker compose up, sobre la ruta SD2025/TP2/

Una vez levantado, este va a esperar peticiones POST de http de la forma:

curl -X POST http://localhost:8000/getRemoteTask -H "Content-Type: application/json" -d "{\"nombreTarea\": \"sumar\", \"parametros\": [10, 20, 30]}"

Esta se puede editar para cambiar el nombre de la tarea (solamente hay dos disponibles: "sumar" y "multiplicar"), y los parametros (entre [], puede recibir n cualquiera de las dos tareas).

Para facilitar toda esta tarea, se creó el programa Cliente.py, que al tener un servidor ejecutandose, y usar este programa, informará al usuario que tareas se encuentras disponibles, para que elija una e ingrese los parametros.

Cliente

    Script en Python: Cliente.py

    Funcionalidades:

        Obtener tareas disponibles (GET /tareasDisponibles)

        Enviar tarea a ejecutar (POST /getRemoteTask con JSON)

El cliente guía al usuario:

    Muestra tareas disponibles.

    Pide nombre de tarea y parámetros.

    Muestra resultado.

Desarrollo del Servicio Tarea

    Cada tarea está empaquetada como una imagen Docker distinta (por ejemplo, bautista222221/tarea-sumar:v1).

    Corre un servidor HTTP en el puerto 8080.

    Expuesto el endpoint /ejecutarTarea:

        Recibe un JSON con parámetros.

        Ejecuta la tarea.

        Devuelve el resultado en JSON.

    Publicadas en Docker Hub para que puedan ser levantadas por el servidor dinámicamente.

**Posible mejora**:
- Se pueden hacer mas tareas.

(Nota: El servidor obtiene las tareas disponibles por medio de una peticion http a docker, obteniendo aquellas que se encuentran subidas por bautista222221, filtrando por todos los contenedores que inicien por tarea-..., por lo que para crear alguna tarea nueva tiene realizarla bautista)
