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

# HIT 2: Sobel con Offloading en la Nube

## Objetivo General

Implementar una solución elástica para aplicar el filtro Sobel sobre imágenes, utilizando infraestructura en la nube que se escala dinámicamente mediante Terraform. El objetivo es construir un sistema híbrido donde los nodos de procesamiento se crean sólo cuando hay trabajo que ejecutar, y se destruyen automáticamente al finalizar.

---

## Estructura del Repositorio

/tp3-sistemas-distribuidos/
├── coordinador/  
├── terraform/  
├── worker/  
├── imágenes/  
├── scripts/  
├── .github/workflows/  
├── docker-compose.yml  
├── README.md  
└── informe-final.pdf  

---

## 1. Diseño de Arquitectura

El sistema está compuesto por:

- **Coordinador (local o remoto)**: Recibe la imagen, la divide y gestiona la ejecución de tareas.
- **Terraform**: Despliega dinámicamente nodos EC2 en la nube para realizar el procesamiento.
- **Workers efímeros**: Ejecutan la tarea Sobel en contenedores Docker dentro de instancias creadas al momento.
- **Almacenamiento temporal (opcional)**: Para compartir resultados si no hay comunicación directa con el coordinador.

## 2. Provisionamiento Automático con Terraform

Terraform se encarga de:

- Crear instancias EC2 configuradas con:
  - Docker
  - Python
  - Utilidades necesarias para correr el filtro Sobel
- Ejecutar un `user_data` que:
  - Instala dependencias automáticamente
  - Descarga la imagen Docker del worker desde Docker Hub
  - Ejecuta el contenedor con los parámetros adecuados
  - Conecta el worker al cluster o sistema de mensajería

---

## 3. Ejecución del Filtro Sobel

1. El coordinador detecta la necesidad de procesar una imagen.
2. Se activa Terraform para desplegar nuevos workers.
3. Cada worker ejecuta su parte de la tarea en contenedor.
4. Los resultados se consolidan en el coordinador.
5. Las instancias EC2 se eliminan automáticamente al finalizar.

---

## 4. Arquitectura Escalable Híbrida

Esta arquitectura permite escalar horizontalmente de forma automática según la demanda. No se requieren nodos de procesamiento activos permanentemente, lo que representa un ahorro de recursos y mayor eficiencia.

Se eligió una solución **híbrida** porque:
- Permite mantener un coordinador fijo (local o remoto).
- Crea infraestructura temporal en la nube para procesamiento intensivo.

---

## 5. Consideraciones Técnicas

- El filtro Sobel se encuentra empaquetado en una imagen Docker publicada en Docker Hub.
- Las instancias EC2 son configuradas mediante `user_data` para su autoaprovisionamiento.
- El sistema puede ampliarse para utilizar colas de trabajo (RabbitMQ) o almacenamiento compartido si se desea mayor desacoplamiento.

---

## 6. Resultados

- El sistema fue probado con múltiples imágenes, generando instancias bajo demanda que ejecutan la tarea correctamente.
- Se verificó la elasticidad: los nodos se crean sólo cuando hay tarea, y se destruyen automáticamente luego.
- La solución demostró ser eficiente, reproducible y escalable.

---
