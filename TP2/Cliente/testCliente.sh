#!/bin/bash

curl -X POST http://localhost:8000/getRemoteTask \
  -H "Content-Type: application/json" \
  -d '{
    "nombreTarea": "sumar",
    "parametros": [10, 20],
    "delayMs": 1000,
    "imagenDocker": "user/tarea",
    "credenciales": {
        "usuario": "test",
        "password": "test123"
    }
}'
