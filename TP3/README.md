# Trabajo Práctico N.º 3 - Computación en la Nube (Kubernetes / RabbitMQ)

## Objetivo General

Diseñar e implementar una solución distribuida basada en contenedores que permita ejecutar tareas genéricas de forma remota. En este caso, la tarea implementada consiste en aplicar un **filtro Sobel** a una imagen de entrada, dividiendo el trabajo entre varios contenedores y utilizando RabbitMQ para coordinar el procesamiento paralelo. Se utilizaron tecnologías como Docker, Python, RabbitMQ, y Docker Compose.

## Estructura del Repositorio

```
TP3/
├── sobel-app/
│   ├── sobel.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
├── sobel-distribuido/
│   ├── coordinador/
│   ├── worker/
│   ├── images/
│   ├── rabbitmq.conf
│   ├── docker-compose.yml
├── informe-final.pdf
├── README.md
```

## 1. Diseño de Arquitectura

La arquitectura está compuesta por tres componentes principales:

* **Coordinador**: recibe una imagen de entrada, la divide en partes y las envía a los workers por medio de una cola de RabbitMQ llamada "tareas" en formato Base64 para que pueda ser interpretada como texto, junto a la imagen se envia un respectivo Chunk ID, para poder identificarlo a la hora de reconstruir la imagen.
* **Workers**: cada uno se suscribe a la cola "tareas" de RabbitMQ, donde recibe una porción de imagen, la decodifica, aplica el filtro Sobel y publica el resultado en una base de datos Redis, identificandola con el ID del Chunk (Tambien codificado en base 64).
* **RabbitMQ**: actúa como broker de mensajes para comunicar coordinador y workers.
* **Redis**: actúa como almacenamiento de los chunks de imagen, con un par ChunkId:Valor, donde el ChunkID es el identificador respectivo a cada trozo de la imagen, y valor es el resultado en Base 64 de la aplicacion del filtro Sobel.

Los componentes están contenerizados y orquestados mediante `docker-compose`. El paso de parámetros y resultados se realiza vía colas de RabbitMQ y bases de datos Redis.

## 2. Implementación del Servidor (Coordinador)

* Lenguaje: Python 3
* Ejecuta el archivo `coordinador.py`.
* Recibe una imagen, la divide en partes y las coloca en una cola de RabbitMQ.
* Espera los resultados procesados por los workers leyendo la base de datos Redis hasta encontrar todas las partes de la imagen, momento en que reconstruye la imagen final.

## 3. Desarrollo del Servicio Tarea (Worker)

* Lenguaje: Python 3
* Ejecuta el archivo `worker.py` dentro de un contenedor Docker.
* Espera mensajes con partes de la imagen en una cola RabbitMQ a la que se suscribe, decodifica la imagen, aplica el filtro Sobel, codifica nuevamente, y publica el resultado en redis.

## 4. Compilación y Ejecución

1. Clonar el repositorio

```bash
git clone <repo-url>
cd tp2-sistemas-distribuidos/sobel-distribuido
```

2. En este punto, si se quisiera cambiar la imagen a la que se le aplica el filtro de sobel, se debe modificar el archivo docker-compose.yml, en la linea 23:
```bash
command: ["images/logos.jpg", "images/output/salidaLogos.jpg", "${NUM_WORKERS}"]  # imagen, salida, cantidad de workers
```
Donde el primer parametro es la ruta a la imagen a la que se le aplica el filtro, el segundo la ruta de salida donde se guarda la imagen resultado, y el tercero el numero de workers en los que se ditribuye la imagen, este parametro se guarda y modifica en el archivo .env.

3. Ejecutar con Docker Compose

```bash
docker-compose up --build
```

4. La imagen procesada estará en la ruta indicada como segundo parametro en el docker-compose.


Nota: El repositorio ya viene con algunas imagenes de prueba.

## 6. Video Explicativo

Creamos un video explicativo del funcionamiento general del programa con una demostracion del resultado final del procesamiento de una imagen.

https://drive.google.com/file/d/1pdLQDNIgUK5oxtYfljEDU0AEpukmDo6I/view?usp=sharing

El funcionamiento del programa se modificará lo menos posible a fin de posibilitar que los siguientes hits operen de la misma forma, en caso de que se realice algun cambio se detallará lo realizado y el nuevo funcionamiento.