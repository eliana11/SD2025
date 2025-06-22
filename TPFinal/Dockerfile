FROM debian:bullseye-slim

# Instalar herramientas para compilar y Python + pip
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    libssl-dev \
    pkg-config \
    ca-certificates \
    python3 \
    python3-pip

# Descargar y compilar OpenSSL estáticamente
WORKDIR /usr/local/src
RUN wget https://www.openssl.org/source/openssl-3.1.2.tar.gz && \
    tar xvf openssl-3.1.2.tar.gz && \
    cd openssl-3.1.2 && \
    ./config no-shared && \
    make && make install

# Copiar código fuente C++ y worker Python
WORKDIR /app
COPY HashMD5CPU.cpp .
COPY worker.py .
COPY json.hpp .

# Instalar dependencias Python necesarias
RUN pip3 install --no-cache-dir requests

# Compilar el minero estático
RUN g++ HashMD5CPU.cpp -o MineroMD5CPU -static -static-libgcc -static-libstdc++ -I/usr/local/include -L/usr/local/lib -lcrypto

# Ejecutar el worker Python (que invoca el minero cuando corresponde)
CMD ["python3", "worker.py"]
