# Trabajo Práctico N.º 3 - Computación en la Nube (Kubernetes / RabbitMQ)

## Objetivo General

Diseñar e implementar una solución distribuida basada en contenedores que permita ejecutar tareas genéricas de forma remota. En este caso, la tarea implementada consiste en aplicar un **filtro Sobel** a una imagen de entrada, dividiendo el trabajo entre varios contenedores y utilizando RabbitMQ para coordinar el procesamiento paralelo. Se utilizaron tecnologías como Docker, Python, RabbitMQ, y Docker Compose.

## Estructura del Repositorio

```
TP3/
├── cloud/ 
│   ├── firewalls/
│   │   ├── firewalls.tf
│   │   ├── providers.tf
│   │   ├── variables.tf
│   ├── gke/
│   │   ├── firewalls.tf
│   │   ├── providers.tf
│   │   ├── variables.tf
│   ├── k8s/
│   │   ├── firewalls.tf
│   │   ├── providers.tf
│   │   ├── variables.tf
│   ├── workers/
│   │   ├── firewalls.tf
│   │   ├── providers.tf
│   │   ├── variables.tf
├── README.md
```

# HIT 3 - Sobel contenerizado asincrónico y escalable 

Se busca desplegar en la nube una solución distribuida, escalable y modular que permita el procesamiento paralelo de imágenes utilizando contenedores y servicios orquestados mediante Kubernetes. La tarea específica consiste en aplicar un filtro Sobel sobre una imagen de entrada, fragmentándola para su procesamiento concurrente por múltiples workers, que devuelven sus resultados al coordinador para su reconstrucción.

## 1. Diseño de Arquitectura

La arquitectura está compuesta por cuatro componentes principales:

* **Coordinador**: recibe una imagen de entrada, la divide en partes y las envía a los workers por medio de una cola de RabbitMQ llamada "tareas" en formato Base64 para que pueda ser interpretada como texto, junto a la imagen se envia un respectivo Chunk ID, para poder identificarlo a la hora de reconstruir la imagen.
* **Workers**: cada uno se suscribe a la cola "tareas" de RabbitMQ, donde recibe una porción de imagen, la decodifica, aplica el filtro Sobel y publica el resultado en una base de datos Redis, identificandola con el ID del Chunk (Tambien codificado en base 64).
* **RabbitMQ**: actúa como broker de mensajes para comunicar coordinador y workers.
* **Redis**: actúa como almacenamiento de los chunks de imagen, con un par ChunkId:Valor, donde el ChunkID es el identificador respectivo a cada trozo de la imagen, y valor es el resultado en Base 64 de la aplicacion del filtro Sobel.

* **GKE + Terraform	Clúster** gestionado por Google Cloud para ejecutar servicios en Kubernetes. La infraestructura es desplegada automáticamente con Terraform.

Para este Hit se agrega el offloading en gcp, el cual, para llevarse a cabo requiere de Terraform y Kubernetes.

* Se implementó un cluster en la plataforma cloud de Google (GCP) por medio de Terraform, definiendo el cluster primario donde se cargarán los pods que desarrollan las diferentes tareas (Archivo t/main.tf).

* Con el cluster ya creado, se obtienen las credenciales de kubernetes y se realiza el despliegue de todos los servicios mencionados anteriormente (archivos .yaml en k8s/). 

* Por ultimo, se deben levantar los workers y firewalls, ubicados en sus respectivos directorios.


## 2. Implementación del Servidor (Coordinador)

* Lenguaje: Python 3
* Ejecuta el archivo `coordinador.py`, el cual levanta una web simple, donde se debe cargar la imagen a la cual aplicar el filtro.
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

2. Para ejecutar este hit se debe cumplir una serie de pre-requisitos:
  - Instalar Terraform
  - Obtener el archivo .json que contiene las claves de la cuenta de servicio creada para terraform dentro del proyecto en gcp (La cuenta tiene por nombre terraform-sa) y copiarla en los directorios firewalls/, gke/ y workers/.

3. El paso a paso para realizar la implementacion y despliegue se encuentra en el directorio pipelines/, donde, de forma enumerada, se dan los comandos utilizados para realizar la ejecucion del proyecto.

4. Ingresar a la pagina web del coordinador, subir la imagen e indicar la cantidad de workers a usar (no mas de 3, ya que solo hay 3 maquinas virtuales creadas)

5. La imagen procesada se descargará automaticamente una vez finalizado el proceso.

## 5. Flujo de Ejecución

    * Carga de Imagen (Coordinador)
    Se accede a la interfaz web del Coordinador, sube una imagen y especifica cuántos workers se utilizarán.

    Fragmentación y Envío de Tareas
    La imagen se divide en partes (chunks), que son codificadas en Base64 y enviadas a la cola de tareas en RabbitMQ.

    Procesamiento Concurrente (Workers)
    Cada worker se suscribe a RabbitMQ y toma tareas en paralelo.
    Aplica el filtro Sobel al fragmento recibido.

    Almacenamiento de Resultados (Redis)
    Una vez procesado, el worker codifica el fragmento resultante y lo sube a Redis, utilizando un identificador único para cada fragmento.

    Reconstrucción y Descarga (Coordinador)
    El Coordinador monitorea Redis, descarga los fragmentos procesados y reconstruye la imagen completa, que es devuelta al usuario automáticamente.

## 6. Arquitectura de Despliegue

El despliegue está compuesto por:

    Maquinas Virtuales que utilizan la imagen de workers, para aplicar el filtro de sobel.

    Un clúster GKE en GCP, creado con Terraform.

    Pods de Kubernetes definidos mediante archivos YAML.

    Servicios:

        deployment-coordinador.yaml despliega el Coordinador.

        Servicios para Redis y RabbitMQ incluidos en infra-k8s/.

## 7. Escalabilidad

El sistema está diseñado para escalar horizontalmente agregando más pods de Worker. Esto permite que se distribuyan más tareas concurrentemente, mejorando el rendimiento para imágenes de mayor tamaño, para ello se debe incrementar la cantidad de VMs creadas.

El Coordinador también puede configurarse como un deployment replicable para mejorar tolerancia a fallos.

## 8. Video Explicativo

Creamos un video explicativo del funcionamiento general del programa con una demostracion del resultado final del procesamiento de una imagen.

https://drive.google.com/file/d/1pdLQDNIgUK5oxtYfljEDU0AEpukmDo6I/view?usp=sharing

El funcionamiento del programa se modificará lo menos posible a fin de posibilitar que los siguientes hits operen de la misma forma, en caso de que se realice algun cambio se detallará lo realizado y el nuevo funcionamiento.

## Pipelines de Despliegue

Para facilitar un despliegue reproducible y automatizado de la infraestructura y las aplicaciones, se definieron los siguientes pipelines lógicos:

### Pipeline 1: Construcción del Clúster GKE
- Utiliza Terraform para crear el clúster GKE en Google Cloud Platform.
- Se definen los nodos, reglas de firewall y permisos necesarios.

### Pipeline 1.1: Servicios de Infraestructura
- Despliegue de servicios esenciales mediante archivos YAML:
  - **Redis**: almacenamiento temporal de resultados.
  - **RabbitMQ**: sistema de colas para orquestación.
  - **Coordinador**: recibe imagen, la divide, envía tareas a RabbitMQ y reconstruye el resultado desde Redis.

### Pipeline 1.2: Reglas de Firewall
- Despliegue de regla de firewall para permitir la comunicacion entre nodos internos y externos al cluster.
  


Conclusiones

  - La plataforma responde de forma escalable al aumentar la cantidad de workers.

  - La carga del sistema se distribuye adecuadamente gracias al uso de Redis y RabbitMQ.
