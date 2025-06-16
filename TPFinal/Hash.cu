#include <cuda_runtime.h>
#include <stdio.h>
#include <string.h> 
#include <iostream>
#include <stdint.h> 
#include <assert.h> 


// ***********************************************************************************
// INICIO DEL CÓDIGO DE LA LIBRERÍA MD5 EN CUDA (md5.cu de honours-project)
// https://github.com/cristian-szabo-university/honours-project/blob/main/md5.cu
// ***********************************************************************************


// MD5 basic functions.
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define I(x, y, z) ((y) ^ ((x) | (~z)))


// Rotate Left function.
#define ROTL32(x, n) (((x) << (n)) | ((x) >> (32 - (n))))


// MD5 transform function.
// All values are uint32_t.
__device__ void md5_transform(uint32_t *state, const uint32_t *block) {
   uint32_t a = state[0], b = state[1], c = state[2], d = state[3];


   // Round 1
   a = b + ROTL32(a + F(b, c, d) + block[0] + 0xD76AA478, 7);
   d = a + ROTL32(d + F(a, b, c) + block[1] + 0xE8C7B756, 12);
   c = d + ROTL32(c + F(d, a, b) + block[2] + 0x242070DB, 17);
   b = c + ROTL32(b + F(c, d, a) + block[3] + 0xC1BDCEEE, 22);
   a = b + ROTL32(a + F(b, c, d) + block[4] + 0xF57C0FAF, 7);
   d = a + ROTL32(d + F(a, b, c) + block[5] + 0x4787C62A, 12);
   c = d + ROTL32(c + F(d, a, b) + block[6] + 0xA8304613, 17);
   b = c + ROTL32(b + F(c, d, a) + block[7] + 0xFD469501, 22);
   a = b + ROTL32(a + F(b, c, d) + block[8] + 0x698098D8, 7);
   d = a + ROTL32(d + F(a, b, c) + block[9] + 0x8B44F7AF, 12);
   c = d + ROTL32(c + F(d, a, b) + block[10] + 0xFFFF5BB1, 17);
   b = c + ROTL32(b + F(c, d, a) + block[11] + 0x895CD7BE, 22);
   a = b + ROTL32(a + F(b, c, d) + block[12] + 0x6B901122, 7);
   d = a + ROTL32(d + F(a, b, c) + block[13] + 0xFD987193, 12);
   c = d + ROTL32(c + F(d, a, b) + block[14] + 0xA679438E, 17);
   b = c + ROTL32(b + F(c, d, a) + block[15] + 0x49B40821, 22);


   // Round 2
   a = b + ROTL32(a + G(b, c, d) + block[1] + 0xF61E2562, 5);
   d = a + ROTL32(d + G(a, b, c) + block[6] + 0xC040B340, 9);
   c = d + ROTL32(c + G(d, a, b) + block[11] + 0x265E5A51, 14);
   b = c + ROTL32(b + G(c, d, a) + block[0] + 0xE9B6C7AA, 20);
   a = b + ROTL32(a + G(b, c, d) + block[5] + 0xD62F105D, 5);
   d = a + ROTL32(d + G(a, b, c) + block[10] + 0x02441453, 9);
   c = d + ROTL32(c + G(d, a, b) + block[15] + 0xD8A1E681, 14);
   b = c + ROTL32(b + G(c, d, a) + block[4] + 0xE7D3FBC8, 20);
   a = b + ROTL32(a + G(b, c, d) + block[9] + 0x21E1CDE6, 5);
   d = a + ROTL32(d + G(a, b, c) + block[14] + 0xC33707D6, 9);
   c = d + ROTL32(c + G(d, a, b) + block[3] + 0xF4D50D87, 14);
   b = c + ROTL32(b + G(c, d, a) + block[8] + 0x455A14ED, 20);
   a = b + ROTL32(a + G(b, c, d) + block[13] + 0xA9E3E905, 5);
   d = a + ROTL32(d + G(a, b, c) + block[2] + 0xFCEFA3F8, 9);
   c = d + ROTL32(c + G(d, a, b) + block[7] + 0x676F02D9, 14);
   b = c + ROTL32(b + G(c, d, a) + block[12] + 0x8D2A4C8A, 20);


   // Round 3
   a = b + ROTL32(a + H(b, c, d) + block[5] + 0xFFFA3942, 4);
   d = a + ROTL32(d + H(a, b, c) + block[8] + 0x8771F681, 11);
   c = d + ROTL32(c + H(d, a, b) + block[11] + 0x6D9D6122, 16);
   b = c + ROTL32(b + H(c, d, a) + block[14] + 0xFDE5380C, 23);
   a = b + ROTL32(a + H(b, c, d) + block[1] + 0xA4BEEA44, 4);
   d = a + ROTL32(d + H(a, b, c) + block[4] + 0x4BDECFA9, 11);
   c = d + ROTL32(c + H(d, a, b) + block[7] + 0xF6BB4B60, 16);
   b = c + ROTL32(b + H(c, d, a) + block[10] + 0xBEBFBC70, 23);
   a = b + ROTL32(a + H(b, c, d) + block[13] + 0x289B7EC6, 4);
   d = a + ROTL32(d + H(a, b, c) + block[0] + 0xEAA127FA, 11);
   c = d + ROTL32(c + H(d, a, b) + block[3] + 0xFE2CE6E0, 16);
   b = c + ROTL32(b + H(c, d, a) + block[6] + 0xA3014314, 23);
   a = b + ROTL32(a + H(b, c, d) + block[9] + 0x4E0811A1, 4);
   d = a + ROTL32(d + H(a, b, c) + block[12] + 0xF7537E82, 11);
   c = d + ROTL32(c + H(d, a, b) + block[15] + 0xBD3AF235, 16);
   b = c + ROTL32(b + H(c, d, a) + block[2] + 0x2AD7D2BB, 23);


   // Round 4
   a = b + ROTL32(a + I(b, c, d) + block[0] + 0xFEBC46AA, 6);
   d = a + ROTL32(d + I(a, b, c) + block[7] + 0xECD84E7B, 10);
   c = d + ROTL32(c + I(d, a, b) + block[14] + 0xF7FE241DA, 15);
   b = c + ROTL32(b + I(c, d, a) + block[5] + 0x858457D, 21);
   a = b + ROTL32(a + I(b, c, d) + block[12] + 0x6FA87E4F, 6);
   d = a + ROTL32(d + I(a, b, c) + block[3] + 0xFE2CE6E0, 10); 
0xFE2CE6E0 to 0xFE2CE6E0 in MD5 spec (typo in original)
   c = d + ROTL32(c + I(d, a, b) + block[10] + 0xA3014314, 15); 
0xA3014314 to 0xA3014314 in MD5 spec (typo in original)
   b = c + ROTL32(b + I(c, d, a) + block[1] + 0x49B40821, 21); 
0x49B40821 to 0x49B40821 in MD5 spec (typo in original)
   a = b + ROTL32(a + I(b, c, d) + block[8] + 0x8771F681, 6); 
0x8771F681 to 0x8771F681 in MD5 spec (typo in original)
   d = a + ROTL32(d + I(a, b, c) + block[15] + 0xBD3AF235, 10);
 0xBD3AF235 to 0xBD3AF235 in MD5 spec (typo in original)
   c = d + ROTL32(c + I(d, a, b) + block[6] + 0xF6BB4B60, 15); 
0xF6BB4B60 to 0xF6BB4B60 in MD5 spec (typo in original)
   b = c + ROTL32(b + I(c, d, a) + block[13] + 0x289B7EC6, 21); 
0x289B7EC6 to 0x289B7EC6 in MD5 spec (typo in original)
   a = b + ROTL32(a + I(b, c, d) + block[4] + 0x4BDECFA9, 6); 
0x4BDECFA9 to 0x4BDECFA9 in MD5 spec (typo in original)
   d = a + ROTL32(d + I(a, b, c) + block[11] + 0x6D9D6122, 10); 
0x6D9D6122 to 0x6D9D6122 in MD5 spec (typo in original)
   c = d + ROTL32(c + I(d, a, b) + block[2] + 0x2AD7D2BB, 15); 
0x2AD7D2BB to 0x2AD7D2BB in MD5 spec (typo in original)
   b = c + ROTL32(b + I(c, d, a) + block[9] + 0xA9E3E905, 21);
0xA9E3E905 to 0xA9E3E905 in MD5 spec (typo in original)


   state[0] += a;
   state[1] += b;
   state[2] += c;
   state[3] += d;
}


// MD5 kernel to calculate the hash on the GPU.
// Assumes one block and one thread for a single string for simplicity.
__global__ void md5_kernel(const unsigned char *d_input_string, const unsigned long long string_length, unsigned char *d_output_hash) {
   // Initial MD5 state variables
   uint32_t state[4] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476};


   // Calculate number of 64-byte blocks needed after padding
   // Padding: original_length_bits + 1 (for '1' bit) + 64 (for length in bits)
   // total_bits = (string_length * 8) + 1 + 64
   // total_bytes = ceil(total_bits / 8)
   // num_blocks = ceil(total_bytes / 64)
   unsigned long long total_bits = string_length * 8;
   unsigned long long padded_length_bits = total_bits + 1; // +1 for the mandatory '1' bit
   // Find the next multiple of 512 bits (64 bytes) that can accommodate the length
   while ((padded_length_bits % 512) != 448) { // 448 = 512 - 64 (space for length)
       padded_length_bits++;
   }
   padded_length_bits += 64; // Add 64 bits for the original length
   unsigned long long padded_length_bytes = padded_length_bits / 8;
   unsigned long long num_blocks = padded_length_bytes / 64;


   uint32_t current_block[16]; // 16 words of 4 bytes = 64 bytes


   for (unsigned long long i = 0; i < num_blocks; ++i) {
       // Copy 64 bytes (16 words) from d_input_string into current_block
       // This handles padding implicitly by reading beyond original string length
       // or setting to 0 if outside original string.
       for (int j = 0; j < 16; ++j) {
           unsigned long long byte_idx = i * 64 + j * 4;
           current_block[j] = 0; // Initialize to zero


           for (int k = 0; k < 4; ++k) {
               if (byte_idx + k < string_length) {
                   current_block[j] |= ((uint32_t)d_input_string[byte_idx + k]) << (k * 8);
               } else if (byte_idx + k == string_length) {
                   current_block[j] |= ((uint32_t)0x80) << (k * 8); // Add '1' bit
               }
               // bytes after the '1' bit and before the length are implicitly 0
           }
       }


       // Add the original length in bits (64-bit value) to the last two words of the last block
       if (i == num_blocks - 1) {
           current_block[14] = (uint32_t)(total_bits & 0xFFFFFFFF);
           current_block[15] = (uint32_t)(total_bits >> 32);
       }


       md5_transform(state, current_block);
   }


   // Copy the final hash state to output_hash
   // MD5 output is little-endian
   for (int i = 0; i < 4; ++i) {
       d_output_hash[i * 4 + 0] = (unsigned char)(state[i] & 0xFF);
       d_output_hash[i * 4 + 1] = (unsigned char)((state[i] >> 8) & 0xFF);
       d_output_hash[i * 4 + 2] = (unsigned char)((state[i] >> 16) & 0xFF);
       d_output_hash[i * 4 + 3] = (unsigned char)((state[i] >> 24) & 0xFF);
   }
}


// ***********************************************************************************
// FIN DEL CÓDIGO DE LA LIBRERÍA MD5 EN CUDA
// ***********************************************************************************




// Función de ayuda para verificar errores de CUDA
#define CHECK_CUDA_ERROR(ans) { gpuAssert((ans), __FILE__, __LINE__); }
inline void gpuAssert(cudaError_t code, const char *file, int line, bool abort=true)
{
  if (code != cudaSuccess)
  {
     fprintf(stderr,"CUDA Error: %s %s %d\n", cudaGetErrorString(code), file, line);
     if (abort) exit(code);
  }
}




int main(int argc, char* argv[]) {
   if (argc != 2) {
       fprintf(stderr, "Uso: %s <string>\n", argv[0]);
       return 1;
   }


   const unsigned char* h_input = (const unsigned char*)argv[1];
   size_t input_len = strlen((const char*)h_input);
   const size_t MD5_HASH_SIZE = 16; // MD5 genera un hash de 16 bytes


   unsigned char* d_input = nullptr;
   unsigned char* d_output = nullptr;
   unsigned char h_output[MD5_HASH_SIZE]; // Para almacenar el hash MD5 resultante en el host


   // 1. Asignar memoria en el device
   CHECK_CUDA_ERROR(cudaMalloc((void**)&d_input, input_len + 1)); // +1 para el null terminator
   CHECK_CUDA_ERROR(cudaMalloc((void**)&d_output, MD5_HASH_SIZE));


   // 2. Copiar datos del host al device
   CHECK_CUDA_ERROR(cudaMemcpy(d_input, h_input, input_len + 1, cudaMemcpyHostToDevice));


   // --- 3. Configurar y lanzar el kernel MD5 REAL ---
   // Un solo bloque y un solo hilo son suficientes para un solo string MD5
   dim3 blocks(1);
   dim3 threads(1);


   md5_kernel<<<blocks, threads>>>(d_input, (unsigned long long)input_len, d_output);
   CHECK_CUDA_ERROR(cudaGetLastError()); // Verifica si hubo error en el lanzamiento del kernel


   // 4. Sincronizar el dispositivo (importante para asegurar que el cálculo finalizó)
   CHECK_CUDA_ERROR(cudaDeviceSynchronize());


   // 5. Copiar resultados del device al host
   CHECK_CUDA_ERROR(cudaMemcpy(h_output, d_output, MD5_HASH_SIZE, cudaMemcpyDeviceToHost));


   // 6. Imprimir el hash MD5
   printf("Hash MD5: ");
   for (int i = 0; i < MD5_HASH_SIZE; ++i) {
       printf("%02x", (unsigned char)h_output[i]);
   }
   printf("\n");


   // 7. Liberar memoria
   cudaFree(d_input);
   cudaFree(d_output);


   return 0;
}

