FROM debian:bullseye-slim

# Instalar herramientas básicas y dependencias del sistema
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
    && apt-get clean

# Descargar y compilar OpenSSL estáticamente (versión 3.1.2)
WORKDIR /usr/local/src
RUN wget https://www.openssl.org/source/openssl-3.1.2.tar.gz && \
    tar xvf openssl-3.1.2.tar.gz && \
    cd openssl-3.1.2 && \
    ./config no-shared && \
    make && make install

# Copiar todo el código fuente (usa . para copiar todo desde el contexto)
WORKDIR /app
COPY . .

# Instalar dependencias de Python requeridas
RUN pip3 install --no-cache-dir \
    cryptography \
    requests \
    ntplib

# Compilar el minero C++ de forma estática
RUN g++ MineroCPU.cpp -o MineroMD5CPU -static -static-libgcc -static-libstdc++ \
    -I/usr/local/include -L/usr/local/lib -lcrypto

# Comando de entrada: ejecuta el worker con argumento
CMD ["python3", "worker.py", "101", "http://host.docker.internal:5000"]
