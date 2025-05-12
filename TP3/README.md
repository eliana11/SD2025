# Trabajo Práctico N.º 3 - Computación en la Nube (Kubernetes / RabbitMQ)

## Nota Importante

Es muy posible que este hit no funcione a la hora de intentar levantarlo, esto se debe a que las imagenes de docker utilizadas estan subidas a docker hub, y automaticamente descarga la version :latest, por lo que a futuro, si la forma de operar estas se modifica, el funcionamiento de este despliegue cloud se vera comprometido.
En caso que no funcione el despliegue, el programa puede ejecutarse de la misma manera que el hit anterior (docker compose).

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

## 1. Diseño de Arquitectura

La arquitectura está compuesta por cuatro componentes principales:

* **Coordinador**: recibe una imagen de entrada, la divide en partes y las envía a los workers por medio de una cola de RabbitMQ llamada "tareas" en formato Base64 para que pueda ser interpretada como texto, junto a la imagen se envia un respectivo Chunk ID, para poder identificarlo a la hora de reconstruir la imagen.
* **Workers**: cada uno se suscribe a la cola "tareas" de RabbitMQ, donde recibe una porción de imagen, la decodifica, aplica el filtro Sobel y publica el resultado en una base de datos Redis, identificandola con el ID del Chunk (Tambien codificado en base 64).
* **RabbitMQ**: actúa como broker de mensajes para comunicar coordinador y workers.
* **Redis**: actúa como almacenamiento de los chunks de imagen, con un par ChunkId:Valor, donde el ChunkID es el identificador respectivo a cada trozo de la imagen, y valor es el resultado en Base 64 de la aplicacion del filtro Sobel.

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
  - Obtener el archivo .json que contiene las claves de la cuenta de servicio creada para terraform dentro del proyecto en gcp (La cuenta tiene por nombre terraform-sa).

3. En el directorio terraform/, ejecutar:

```bash
terraform init
terraform apply
```
Para crear la estructura y recursos necesarios (Cluster y nodepool)

4. Con esto creado, ejecutar en el mismo directorio el comando:

```bash
gcloud container clusters get-credentials simple-gke-cluster --region us-central1-a --project the-program-457617-r1
```
Para obtener las credenciales de kubernetes del cluster, con esto hecho, ya se puede iniciar el despliegue de los servicios ubicados en k8s/, para ello, volver un directorio (hasta TP3/) y ejecutar:

```bash
kubectl apply -f k8s/
```
Esto creará los servicios necesarios.

5. Por ultimo, se debe obtener la direccion ip asignada por google al servicio del coordinador, esto puede hacerse con el comando:

```bash
kubectl get services
```
Con esta ip, se puede acceder por medio del buscador a la web del coordinador, donde se cargara la imagen a la que se desea aplicar sobel.

6. La imagen procesada se descargará automaticamente una vez finalizado el proceso.

## 5. Video Explicativo

Creamos un video explicativo del funcionamiento general del programa con una demostracion del resultado final del procesamiento de una imagen.

https://drive.google.com/file/d/1pdLQDNIgUK5oxtYfljEDU0AEpukmDo6I/view?usp=sharing

El funcionamiento del programa se modificará lo menos posible a fin de posibilitar que los siguientes hits operen de la misma forma, en caso de que se realice algun cambio se detallará lo realizado y el nuevo funcionamiento.

## Modificaciones al funcionamiento:

- Ahora el coordinador no recibe como parametros la imagen, salida y workers a utilizar, sino que levanta un servicio web muy simple, donde se puede cargar la imagen e indicar la cantidad de workers, esta web opera en el puerto 80, en la direccion ip asignada por gcp, el resto del funcionamiento se mantiene igual.

## Pipelines de Despliegue

Para facilitar un despliegue reproducible y automatizado de la infraestructura y las aplicaciones, se definieron los siguientes pipelines lógicos:

### Pipeline 1: Construcción del Clúster GKE
- Utiliza Terraform para crear el clúster GKE en Google Cloud Platform.
- Se definen los nodos, reglas de firewall y permisos necesarios.

### Pipeline 1.1: Servicios de Infraestructura
- Despliegue de servicios esenciales mediante archivos YAML:
  - **Redis**: almacenamiento temporal de resultados.
  - **RabbitMQ**: sistema de colas para orquestación.

### Pipeline 1.2: Aplicaciones del Sistema
- Despliegue de contenedores para:
  - **Coordinador**: recibe imagen, la divide, envía tareas a RabbitMQ y reconstruye el resultado desde Redis.
  - **Workers**: aplican el filtro Sobel sobre fragmentos de imagen.

## Análisis de Desempeño Bajo Carga

Este análisis evalúa el comportamiento de la plataforma desarrollada en HIT3 al someterla a distintas combinaciones de carga

Variable	Descripción
V1 - Tamaño de los datos	Imágenes de 1 KB, 10 KB, 1 MB, 10 MB y 100 MB
V2 - Peticiones concurrentes	1, 5, 10, 25, 50 solicitudes simultáneas
V3 - Cantidad de workers	1, 2, 5, 10 VMs procesando

Resultados
Tamaño Imagen (V1)	Concurrencia (V2)	Workers (V3)	Tiempo Promedio (ms)	Tiempo Máx (ms)
1 KB	1	1	120	130
10 KB 10 2 860 1170
1 MB	10	3	800	900
10 MB	10	1	4000	5500
100 MB	5	2	7000	8500

Conclusiones

    La plataforma responde de forma escalable al aumentar la cantidad de workers.

    La carga del sistema se distribuye adecuadamente gracias al uso de Redis y RabbitMQ.

    El tamaño de los datos tiene impacto lineal en la latencia, pero el sistema soporta cargas altas sin caídas.
