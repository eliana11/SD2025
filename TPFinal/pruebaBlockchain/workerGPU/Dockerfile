FROM nvidia/cuda:12.0.0-devel-ubuntu22.04


RUN apt-get update && apt-get install -y \
    build-essential \
    libcurl4-openssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app
COPY . .


# Ejemplo con nvcc para compilar C++ y CUDA juntos:
RUN nvcc -o MineroMD5GPU MineroMD5GPU.cpp your_cuda_kernel.cu \
    -lcurl -lstdc++fs \
    -I/usr/local/cuda/include -L/usr/local/cuda/lib64 -lcudart \
    -arch=sm_75 

CMD ["/app/MineroMD5GPU"]
