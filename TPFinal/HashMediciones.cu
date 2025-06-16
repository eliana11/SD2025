#include <cuda_runtime.h>
#include <stdio.h>
#include <string.h>
#include <iostream>
#include <stdint.h>
#include <assert.h>
#include <limits.h>
#include <chrono> // <-- Asegúrate de tener este include

// ***********************************************************************************
// INICIO DEL CÓDIGO DE LA LIBRERÍA MD5 EN CUDA (md5.cu de honours-project)
// (CORREGIDO DE ERRORES DE SINTAXIS)
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
    c = d + ROTL32(c + I(d, a, b) + block[14] + 0x242070DB, 15);
    b = c + ROTL32(b + I(c, d, a) + block[5] + 0x858457D, 21);
    a = b + ROTL32(a + I(b, c, d) + block[12] + 0x6FA87E4F, 6);
    d = a + ROTL32(d + I(a, b, c) + block[3] + 0xFE2CE6E0, 10);
    c = d + ROTL32(c + I(d, a, b) + block[10] + 0xA3014314, 15);
    b = c + ROTL32(b + I(c, d, a) + block[1] + 0x49B40821, 21);
    a = b + ROTL32(a + I(b, c, d) + block[8] + 0x8771F681, 6);
    d = a + ROTL32(d + I(a, b, c) + block[15] + 0xBD3AF235, 10);
    c = d + ROTL32(c + I(d, a, b) + block[6] + 0xF6BB4B60, 15);
    b = c + ROTL32(b + I(c, d, a) + block[13] + 0x289B7EC6, 21);
    a = b + ROTL32(a + I(b, c, d) + block[4] + 0x4BDECFA9, 6);
    d = a + ROTL32(d + I(a, b, c) + block[11] + 0x6D9D6122, 10);
    c = d + ROTL32(c + I(d, a, b) + block[2] + 0x2AD7D2BB, 15);
    b = c + ROTL32(b + I(c, d, a) + block[9] + 0xA9E3E905, 21);

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}

// Function to calculate MD5 hash on GPU (adapted from original md5_kernel)
// This will be called from within the main cracking kernel.
__device__ void calculate_md5_hash_on_device(const unsigned char *input_data, unsigned long long input_len, unsigned char *output_hash) {
    uint32_t state[4] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476};

    unsigned long long total_bits = input_len * 8;
    unsigned long long padded_length_bits = total_bits + 1;
    while ((padded_length_bits % 512) != 448) {
        padded_length_bits++;
    }
    padded_length_bits += 64;
    unsigned long long padded_length_bytes = padded_length_bits / 8;
    unsigned long long num_blocks = padded_length_bytes / 64;

    uint32_t current_block[16];

    for (unsigned long long i = 0; i < num_blocks; ++i) {
        for (int j = 0; j < 16; ++j) {
            unsigned long long byte_idx = i * 64 + j * 4;
            current_block[j] = 0;

            for (int k = 0; k < 4; ++k) {
                if (byte_idx + k < input_len) {
                    current_block[j] |= ((uint32_t)input_data[byte_idx + k]) << (k * 8);
                } else if (byte_idx + k == input_len) {
                    current_block[j] |= ((uint32_t)0x80) << (k * 8);
                }
            }
        }

        if (i == num_blocks - 1) {
            current_block[14] = (uint32_t)(total_bits & 0xFFFFFFFF);
            current_block[15] = (uint32_t)(total_bits >> 32);
        }

        md5_transform(state, current_block);
    }

    for (int i = 0; i < 4; ++i) {
        output_hash[i * 4 + 0] = (unsigned char)(state[i] & 0xFF);
        output_hash[i * 4 + 1] = (unsigned char)((state[i] >> 8) & 0xFF);
        output_hash[i * 4 + 2] = (unsigned char)((state[i] >> 16) & 0xFF);
        output_hash[i * 4 + 3] = (unsigned char)((state[i] >> 24) & 0xFF);
    }
}

// ***********************************************************************************
// FIN DEL CÓDIGO DE LA LIBRERÍA MD5 EN CUDA
// ***********************************************************************************

// --- NUEVAS FUNCIONES Y KERNEL PARA LA BÚSQUEDA ---

// Helper function to convert unsigned long long to string on device
// Returns length of the string
__device__ int ulltoa_device(unsigned long long value, char* buffer) {
    if (value == 0) {
        buffer[0] = '0';
        buffer[1] = '\0';
        return 1;
    }
    int i = 0;
    char temp_buffer[20]; // Max for ULL is 20 digits + null terminator
    int j = 0;
    unsigned long long temp_val = value; // Use a temp variable for calculation
    while (temp_val > 0) {
        temp_buffer[j++] = (temp_val % 10) + '0';
        temp_val /= 10;
    }
    // Reverse the string
    while (j > 0) {
        buffer[i++] = temp_buffer[--j];
    }
    buffer[i] = '\0';
    return i;
}

// Helper function to concatenate strings on device
__device__ int concatenate_device(char* dest, const char* s1, int len1, const char* s2, int len2) {
    for (int i = 0; i < len1; ++i) {
        dest[i] = s1[i];
    }
    for (int i = 0; i < len2; ++i) {
        dest[len1 + i] = s2[i];
    }
    dest[len1 + len2] = '\0';
    return len1 + len2;
}

// Maximum length for the concatenated string (base_string + number_string)
// Assuming base_string max 200 chars, number max 10^18 (19 chars), plus null terminator
#define MAX_CONCAT_LEN 256
// Max length for the number string (e.g., 10^18 is 19 digits)
#define MAX_NUMBER_STR_LEN 20

// Kernel para la búsqueda del prefijo MD5
// d_base_string: cadena base en la GPU
// base_string_len: longitud de la cadena base
// d_target_prefix_bytes: prefijo MD5 objetivo en bytes
// target_prefix_len: longitud del prefijo objetivo en bytes
// d_found_flag: puntero a una bandera atómica (1 si se encontró, 0 en otro caso)
// d_found_hash: puntero a donde almacenar el hash encontrado
// d_found_number_string: puntero a donde almacenar el número encontrado como string
// start_num_offset: número inicial para la búsqueda del hilo (offset para el ID del hilo)
// max_attempts_per_thread: máximo de números que cada hilo intentará
__global__ void md5_prefix_cracker_kernel(
    const unsigned char* d_base_string, unsigned long long base_string_len,
    const unsigned char* d_target_prefix_bytes, unsigned int target_prefix_len,
    volatile int* d_found_flag,
    unsigned char* d_found_hash,
    char* d_found_number_string,
    unsigned long long start_num_offset,
    unsigned long long max_attempts_per_thread)
{
    unsigned long long thread_id = blockIdx.x * blockDim.x + threadIdx.x;

    // Local buffer for the concatenated string
    char concatenated_string_buffer[MAX_CONCAT_LEN];
    char number_str_buffer[MAX_NUMBER_STR_LEN];
    unsigned char current_hash[16]; // To store the hash calculated by this thread

    // Each thread starts its search from a unique number and iterates
    // This allows many threads to search in parallel
    for (unsigned long long i = 0; i < max_attempts_per_thread; ++i) {
        // Check if a solution has already been found by another thread.
        // A volatile read is sufficient here for early exit for performance.
        if (*d_found_flag == 1) {
             return; // Another thread found it, so this thread exits
        }

        unsigned long long current_number = start_num_offset + (thread_id * max_attempts_per_thread) + i;

        // Convert number to string
        int num_str_len = ulltoa_device(current_number, number_str_buffer);

        // Concatenate base_string and number_string
        int full_string_len = concatenate_device(
            concatenated_string_buffer,
            (const char*)d_base_string, (int)base_string_len, // Cast to int for concatenate_device
            number_str_buffer, num_str_len
        );

        // Calculate MD5 hash for the concatenated string
        calculate_md5_hash_on_device((const unsigned char*)concatenated_string_buffer, full_string_len, current_hash);

        // Compare the calculated hash prefix with the target prefix
        bool prefix_matches = true;
        for (unsigned int k = 0; k < target_prefix_len; ++k) {
            if (current_hash[k] != d_target_prefix_bytes[k]) {
                prefix_matches = false;
                break;
            }
        }

        // If prefix matches, atomically update found_flag and store results
        if (prefix_matches) {
            // Use atomicCAS to ensure only the first thread to find a match writes the result
            if (atomicCAS((int*)d_found_flag, 0, 1) == 0) { // If it was 0, set to 1 (this thread is the first)
                // Copy the found hash
                for (int k = 0; k < 16; ++k) {
                    d_found_hash[k] = current_hash[k];
                }
                // Copy the found number string
                int str_idx = 0;
                while(number_str_buffer[str_idx] != '\0' && str_idx < MAX_NUMBER_STR_LEN) {
                    d_found_number_string[str_idx] = number_str_buffer[str_idx];
                    str_idx++;
                }
                d_found_number_string[str_idx] = '\0'; // Null terminate
            }
            return; // Exit kernel for this thread after finding/confirming a match
        }
    }
}


// --- FUNCIONES DE AYUDA DEL HOST ---

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

// Converts a hexadecimal character to its integer value
int hexCharToInt(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1; // Invalid hex char
}

// Converts a hexadecimal string to a byte array
// Returns the number of bytes written to byte_array, or -1 on error
int hexStringToBytes(const char* hex_string, unsigned char* byte_array) {
    int len = strlen(hex_string);
    if (len % 2 != 0) {
        // Hex string must have an even number of characters
        // Or if it's a single hex digit, convert it to 0X style
        if (len == 1) { // Handle "1" becoming "01"
            int nibble = hexCharToInt(hex_string[0]);
            if (nibble == -1) return -1;
            byte_array[0] = (unsigned char)nibble; // Will be 0X
            return 1;
        }
        return -1;
    }
    int byte_len = len / 2;
    for (int i = 0; i < byte_len; ++i) {
        int high_nibble = hexCharToInt(hex_string[i * 2]);
        int low_nibble = hexCharToInt(hex_string[i * 2 + 1]);
        if (high_nibble == -1 || low_nibble == -1) {
            return -1; // Invalid hex character
        }
        byte_array[i] = (high_nibble << 4) | low_nibble;
    }
    return byte_len;
}


int main(int argc, char* argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Uso: %s <hash_prefix_hex> <base_string>\n", argv[0]);
        return 1;
    }

    const char* h_hash_prefix_hex = argv[1];
    const unsigned char* h_base_string = (const unsigned char*)argv[2];

    unsigned char h_target_prefix_bytes[16]; // Max MD5 hash size
    int target_prefix_len = hexStringToBytes(h_hash_prefix_hex, h_target_prefix_bytes);

    if (target_prefix_len == -1 || target_prefix_len == 0 || target_prefix_len > 16) {
        fprintf(stderr, "Error: El prefijo del hash hexadecimal es inválido o su longitud no es adecuada (max 32 caracteres hex / 16 bytes). Recibido: %s, Longitud de bytes: %d\n", h_hash_prefix_hex, target_prefix_len);
        return 1;
    }
    
    unsigned long long base_string_len = strlen((const char*)h_base_string);
    if (base_string_len + MAX_NUMBER_STR_LEN >= MAX_CONCAT_LEN) {
        fprintf(stderr, "Error: La longitud de la cadena base (%llu) más el número exceden el buffer (%d). Aumente MAX_CONCAT_LEN o reduzca la cadena base.\n", base_string_len, MAX_CONCAT_LEN);
        return 1;
    }

    // --- Variables en el Host (punteros a memoria del Device) ---
    unsigned char* d_base_string = nullptr;
    unsigned char* d_target_prefix_bytes = nullptr;
    volatile int* d_found_flag = nullptr; // Bandera para indicar si se encontró el hash
    unsigned char* d_found_hash = nullptr; // Hash encontrado
    char* d_found_number_string = nullptr; // Número (como string) que generó el hash

    // --- Parámetros de Configuración del Kernel ---
    // Puedes ajustar estos valores para más o menos hilos/intentos.
    // Cuanto más largo el prefijo o más "raro", más intentos necesitará.
    const unsigned int NUM_BLOCKS = 128; // Número de bloques
    const unsigned int THREADS_PER_BLOCK = 256; // Hilos por bloque
    // Este valor determina cuántos números consecutivos probará CADA hilo.
    // Multiplicado por NUM_BLOCKS * THREADS_PER_BLOCK da el espacio total de búsqueda.
    const unsigned long long MAX_ATTEMPTS_PER_THREAD = 10000; // Máximo de números a probar por CADA hilo
    const unsigned long long TOTAL_SEARCH_SPACE = (unsigned long long)NUM_BLOCKS * THREADS_PER_BLOCK * MAX_ATTEMPTS_PER_THREAD; // <-- CORREGIDO NUM_BLOCKs a NUM_BLOCKS

    printf("Iniciando búsqueda de prefijo MD5: '%s' para la cadena base '%s'\n", h_hash_prefix_hex, h_base_string);
    printf("Longitud del prefijo a comparar (en bytes): %d\n", target_prefix_len);
    printf("Espacio de búsqueda total (aproximado): %llu números\n", TOTAL_SEARCH_SPACE);
    printf("--- Por favor, espere, esto puede tardar ---\n");


    // 1. Asignar memoria en el device
    CHECK_CUDA_ERROR(cudaMalloc((void**)&d_base_string, base_string_len + 1));
    CHECK_CUDA_ERROR(cudaMalloc((void**)&d_target_prefix_bytes, target_prefix_len));
    CHECK_CUDA_ERROR(cudaMalloc((void**)&d_found_flag, sizeof(int)));
    CHECK_CUDA_ERROR(cudaMalloc((void**)&d_found_hash, 16)); // MD5 hash es de 16 bytes
    CHECK_CUDA_ERROR(cudaMalloc((void**)&d_found_number_string, MAX_NUMBER_STR_LEN));

    // 2. Copiar datos del host al device
    CHECK_CUDA_ERROR(cudaMemcpy(d_base_string, h_base_string, base_string_len + 1, cudaMemcpyHostToDevice));
    CHECK_CUDA_ERROR(cudaMemcpy(d_target_prefix_bytes, h_target_prefix_bytes, target_prefix_len, cudaMemcpyHostToDevice));
    CHECK_CUDA_ERROR(cudaMemset((void*)d_found_flag, 0, sizeof(int)));

    // 3. Configurar y lanzar el kernel de búsqueda
    dim3 blocks(NUM_BLOCKS);
    dim3 threads(THREADS_PER_BLOCK);

    // El número inicial para el primer hilo (0) es 0. Cada hilo calcula su propio offset.
    unsigned long long start_num_for_kernel = 0;

    // --- INICIO MEDICIÓN DE TIEMPO ---
    auto start_time = std::chrono::high_resolution_clock::now();

    md5_prefix_cracker_kernel<<<blocks, threads>>>(
        d_base_string, base_string_len,
        d_target_prefix_bytes, target_prefix_len,
        d_found_flag, d_found_hash, d_found_number_string,
        start_num_for_kernel, MAX_ATTEMPTS_PER_THREAD
    );
    CHECK_CUDA_ERROR(cudaGetLastError()); // Verifica si hubo error en el lanzamiento del kernel

    // 4. Sincronizar el dispositivo y finalizar la medición
    CHECK_CUDA_ERROR(cudaDeviceSynchronize()); // Espera a que todos los hilos terminen
    auto end_time = std::chrono::high_resolution_clock::now();
    // --- FIN MEDICIÓN DE TIEMPO ---

    std::chrono::duration<double, std::milli> duration = end_time - start_time; // Duración en milisegundos

    // 5. Verificar si se encontró una solución y copiar resultados
    int h_found_flag = 0;
    CHECK_CUDA_ERROR(cudaMemcpy(&h_found_flag, (const void*)d_found_flag, sizeof(int), cudaMemcpyDeviceToHost));

    if (h_found_flag == 1) {
        unsigned char h_final_hash[16];
        char h_final_number_string[MAX_NUMBER_STR_LEN];
        CHECK_CUDA_ERROR(cudaMemcpy(h_final_hash, d_found_hash, 16, cudaMemcpyDeviceToHost));
        CHECK_CUDA_ERROR(cudaMemcpy(h_final_number_string, d_found_number_string, MAX_NUMBER_STR_LEN, cudaMemcpyDeviceToHost));

        printf("\n--- SOLUCIÓN ENCONTRADA ---\n");
        printf("Número encontrado: %s\n", h_final_number_string);
        printf("Cadena probada: %s%s\n", (const char*)h_base_string, h_final_number_string);
        printf("Hash MD5 resultante: ");
        for (int i = 0; i < 16; ++i) {
            printf("%02x", (unsigned char)h_final_hash[i]);
        }
        printf("\n");
        printf("Tiempo de ejecución: %.2f ms\n", duration.count()); // Imprimir el tiempo
    } else {
        printf("\n--- No se encontró una solución en el rango de búsqueda especificado (%llu intentos). ---\n", TOTAL_SEARCH_SPACE);
        printf("Intente aumentar MAX_ATTEMPTS_PER_THREAD o NUM_BLOCKS.\n");
        printf("Tiempo de ejecución: %.2f ms\n", duration.count()); // Imprimir el tiempo incluso si no se encontró
    }

    // 6. Liberar memoria
    cudaFree((void*)d_found_flag);
    cudaFree(d_base_string);
    cudaFree(d_target_prefix_bytes);
    cudaFree(d_found_hash);
    cudaFree(d_found_number_string);

    return 0;
}
