# SD2025
Desarrollo de los TP de Sistemas Distribuidos


## Proyecto Cliente-Servidor con Docker Compose

Este proyecto incluye un servidor y un cliente, ambos implementados en Java y ejecutados en contenedores Docker. Usamos Docker Compose para gestionar los contenedores de manera eficiente.

## Estructura del Proyecto

- El directorio `cliente` contiene los archivos fuente de la aplicación cliente y su propio `Dockerfile`.
- El directorio `servidor` contiene los archivos fuente de la aplicación servidor y su propio `Dockerfile`.
- El archivo `docker-compose.yml` define los servicios que componen la aplicación.

## Construcción y Ejecución

1. **Clona el repositorio**

2. **Construir y levantar los contenedores con Docker Compose:** 

- docker compose build

- En este hit se pide unir los programas cliente y servidor, los parametros de direcciones ip y puertos de cada nodo se encuentran en el archivo docker compose, para ejecutar este hit se debe realizar un docker compose up, de manera que se levanten ambos servicios, o iniciarlos por separado con un docker compose up nodoN (siendo N el numero del nodo que se desee levantar)

3. **Acceso a la aplicación:**

- El servidor estará esperando conexiones en el puerto 8080 y el cliente intentará conectarse al el.

- El servidor escuchará en el puerto 8080 dentro de su contenedor.

- El cliente, cuando se ejecute, intentará conectarse a servidor:8080 (el servidor dentro del contenedor correspondiente).

- Si ambos servicios están configurados correctamente, el cliente debería poder enviar un mensaje al servidor y recibir una respuesta.

4. **Descripción de los Archivos:**

- docker-compose.yml: Este archivo define los servicios y su configuración, como los puertos, contextos de construcción, etc.

- Dockerfile: Cada servicio tiene su propio Dockerfile que define cómo construir la imagen de Docker para ese servicio. 

- .java: Codigo fuente de cada uno de los servicios que componen la aplicacion.