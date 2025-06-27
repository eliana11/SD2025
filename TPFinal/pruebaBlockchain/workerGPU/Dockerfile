FROM nvidia/cuda:12.0.0-devel-ubuntu22.04

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    libssl-dev \
    libffi-dev \
    pkg-config \
    ca-certificates \
    python3 \
    python3-pip \
    python3-dev \
    libcurl4-openssl-dev \
    python3 python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
   

WORKDIR /usr/local/src
RUN wget https://www.openssl.org/source/openssl-3.1.2.tar.gz && \
    tar xvf openssl-3.1.2.tar.gz && \
    cd openssl-3.1.2 && \
    ./config no-shared && \
    make && make install

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar código fuente
COPY MineroMD5.cu .
COPY json.hpp .
COPY workerGPU.py .
COPY Usuario.py .

# Instalar dependencias de Python necesarias
RUN pip3 install --no-cache-dir \
    cryptography \
    requests \
    ntplib

# Compilar el ejecutable CUDA
RUN nvcc -o MineroMD5 MineroMD5.cu \
    -lcurl -lstdc++fs \
    -I/usr/local/cuda/include -L/usr/local/cuda/lib64 -lcudart \
    -arch=sm_75

# Ejecutar el worker Python
ENTRYPOINT ["python3", "workerGPU.py"]

CMD ["201", "http://35.192.66.105:80"]



