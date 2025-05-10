# Trabajo Práctico N.º 3 - Computación en la Nube (Kubernetes / RabbitMQ)

## Objetivo General

Diseñar e implementar una solución distribuida basada en contenedores que permita ejecutar tareas genéricas de forma remota. En este caso, la tarea implementada consiste en aplicar un **filtro Sobel** a una imagen de entrada, dividiendo el trabajo entre varios contenedores y utilizando RabbitMQ para coordinar el procesamiento paralelo. Se utilizaron tecnologías como Docker, Python, RabbitMQ, y Docker Compose.

## Estructura del Repositorio

```
TP3/
├── sobel-distribuido/
│   ├── coordinador/
│   ├── worker/
│   ├── images/
│   ├── rabbitmq.conf
│   ├── docker-compose.yml
├── sobel-app/
│   ├── sobel.py
│   ├── Dockerfile
├── informe-final.pdf
├── README.md
```

## 1. Diseño de Arquitectura

La arquitectura está compuesta por tres componentes principales:

* **Coordinador**: recibe una imagen de entrada, la divide en partes y las envía a los workers usando RabbitMQ.
* **Workers**: cada uno recibe una porción de imagen, aplica el filtro Sobel y devuelve el resultado.
* **RabbitMQ**: actúa como broker de mensajes para comunicar coordinador y workers.

Los componentes están contenerizados y orquestados mediante `docker-compose`. El paso de parámetros y resultados se realiza vía mensajes JSON y colas de RabbitMQ.

## 2. Implementación del Servidor (Coordinador)

* Lenguaje: Python 3
* Ejecuta el archivo `coordinador.py`.
* Recibe una imagen, la divide en partes y las coloca en una cola de RabbitMQ.
* Espera los resultados procesados por los workers y reconstruye la imagen final.

## 3. Desarrollo del Servicio Tarea (Worker)

* Lenguaje: Python 3
* Ejecuta el archivo `worker.py` dentro de un contenedor Docker.
* Espera mensajes con partes de la imagen, aplica el filtro Sobel, y envía el resultado.
* El filtro Sobel está implementado en el módulo `sobel-app/sobel.py`.

##  4. Cliente

* El cliente está implícito en la acción del coordinador, quien inicia el proceso completo.
* Se puede lanzar el sistema completo con Docker Compose.
* La imagen procesada se guarda en `images/output/`.


## 5. Compilación y Ejecución

1. Clonar el repositorio

```bash
git clone <repo-url>
cd tp2-sistemas-distribuidos/sobel-distribuido
```

2. Ejecutar con Docker Compose

```bash
docker-compose up --build
```

3. La imagen procesada estará en: `images/output/salidaLogos.jpg`
