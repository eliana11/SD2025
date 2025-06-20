#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <cstring> // For memcpy, strlen
#include <cstdio>  // For sprintf
#include <algorithm> // For std::reverse
#include <limits.h> // For ULLONG_MAX
#include <stdlib.h> // For strtoull

#include "json.hpp"

using json = nlohmann::json;

// ***********************************************************************************
// CONSTANTES GLOBALES
// ***********************************************************************************
#define MAX_CONCAT_LEN 256
#define MAX_NUMBER_STR_LEN 20

// ***********************************************************************************
// MACROS MD5
// ***********************************************************************************
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z)) // <--- CORRECCIÓN AQUÍ: Quitamos el ')' extra
#define I(x, y, z) ((y) ^ ((x) | (~z)))

#define ROTL32(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

// ***********************************************************************************
// FUNCIONES DE SOPORTE PARA CPU (Adaptadas de las versiones __device__)
// ***********************************************************************************

// MD5 transform function for CPU.
void md5_transform_cpu(uint32_t *state, const uint32_t *block) {
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

// Function to calculate MD5 hash on CPU
void calculate_md5_hash_cpu(const unsigned char *input_data, unsigned long long input_len, unsigned char *output_hash) {
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

        md5_transform_cpu(state, current_block);
    }

    for (int i = 0; i < 4; ++i) {
        output_hash[i * 4 + 0] = (unsigned char)(state[i] & 0xFF);
        output_hash[i * 4 + 1] = (unsigned char)((state[i] >> 8) & 0xFF);
        output_hash[i * 4 + 2] = (unsigned char)((state[i] >> 16) & 0xFF);
        output_hash[i * 4 + 3] = (unsigned char)((state[i] >> 24) & 0xFF);
    }
}

// Helper function to convert unsigned long long to string for CPU
int ulltoa_cpu(unsigned long long value, char* buffer) {
    if (value == 0) {
        buffer[0] = '0';
        buffer[1] = '\0';
        return 1;
    }
    int i = 0;
    char temp_buffer[MAX_NUMBER_STR_LEN]; // Max for ULL is 20 digits + null terminator
    int j = 0;
    unsigned long long temp_val = value;
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

// Helper function to concatenate strings for CPU
int concatenate_cpu(char* dest, const char* s1, int len1, const char* s2, int len2) {
    // Asegurarse de que el destino tiene suficiente espacio
    if (len1 + len2 >= MAX_CONCAT_LEN) {
        // Manejar error o truncar, para este ejemplo, solo imprimir y continuar
        fprintf(stderr, "Error: Buffer de concatenación insuficiente en concatenate_cpu.\n");
        // Opcional: Abortar o manejar el error de forma más robusta
    }
    std::memcpy(dest, s1, len1);
    std::memcpy(dest + len1, s2, len2);
    dest[len1 + len2] = '\0';
    return len1 + len2;
}


// ***********************************************************************************
// FUNCIÓN PRINCIPAL DE CRACKING EN CPU (UN SOLO HILO)
// ***********************************************************************************
bool md5_prefix_cracker_cpu(
    const unsigned char* block_base_string, unsigned long long block_base_string_len, // Nueva cadena base
    const unsigned char* target_prefix_bytes, unsigned int target_prefix_len,
    unsigned char* found_hash, char* found_number_string,
    unsigned long long global_start_range, unsigned long long global_end_range
) {
    // Loop through the assigned range sequentially
    for (unsigned long long current_number = global_start_range; current_number <= global_end_range; ++current_number) {
        // Local buffers
        char concatenated_string_buffer[MAX_CONCAT_LEN];
        char number_str_buffer[MAX_NUMBER_STR_LEN];
        unsigned char current_hash[16];

        int num_str_len = ulltoa_cpu(current_number, number_str_buffer);
        int full_string_len = concatenate_cpu(
            concatenated_string_buffer,
            (const char*)block_base_string, (int)block_base_string_len, // Usar block_base_string
            number_str_buffer, num_str_len
        );


        calculate_md5_hash_cpu((const unsigned char*)concatenated_string_buffer, full_string_len, current_hash);

        bool prefix_matches = true;
        for (unsigned int k = 0; k < target_prefix_len; ++k) {
            if (current_hash[k] != target_prefix_bytes[k]) {
                prefix_matches = false;
                break;
            }
        }

        if (prefix_matches) {
            // Copy results to output parameters
            std::memcpy(found_hash, current_hash, 16);
            std::memcpy(found_number_string, number_str_buffer, num_str_len + 1); // +1 for null terminator
            return true; // Solution found
        }
    }
    return false; // No solution found in range
}


// ***********************************************************************************
// FUNCIONES DE AYUDA DEL HOST (idénticas a las del código CUDA)
// ***********************************************************************************
int hexCharToInt(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int hexStringToBytes(const char* hex_string, unsigned char* byte_array) {
    int len = std::strlen(hex_string);
    if (len % 2 != 0) {
        if (len == 1) {
            int nibble = hexCharToInt(hex_string[0]);
            if (nibble == -1) return -1;
            byte_array[0] = (unsigned char)nibble;
            return 1;
        }
        return -1;
    }
    int byte_len = len / 2;
    for (int i = 0; i < byte_len; ++i) {
        int high_nibble = hexCharToInt(hex_string[i * 2]);
        int low_nibble = hexCharToInt(hex_string[i * 2 + 1]);
        if (high_nibble == -1 || low_nibble == -1) {
            return -1;
        }
        byte_array[i] = (high_nibble << 4) | low_nibble;
    }
    return byte_len;
}

// ***********************************************************************************
// FUNCIÓN MAIN PARA CPU
// ***********************************************************************************
int main(int argc, char* argv[]) {
    // Se espera 1 argumento: la cadena JSON de la tarea
    if (argc != 2) {
        fprintf(stderr, "Uso: %s <tarea_json_string>\n", argv[0]);
        fprintf(stderr, "Ejemplo: %s '{\"prev_hash\": \"000...\", \"transacciones\": \"[{\"de\":\"A\"...}]\", \"dificultad\": \"00\", \"start_nonce\": 0, \"end_nonce\": 1000000}'\n", argv[0]);
        return 1;
    }

    // --- 1. Leer y parsear el JSON de la tarea ---
    std::string task_json_string = argv[1];
    json task_data;
    try {
        task_data = json::parse(task_json_string);
    } catch (const json::parse_error& e) {
        fprintf(stderr, "Error al parsear el JSON de la tarea: %s\n", e.what());
        return 1;
    }

    // Extraer datos de la tarea JSON
    std::string prev_hash_str;
    std::string transactions_str; // Las transacciones como una cadena JSON serializada
    std::string difficulty_prefix_str;
    unsigned long long h_start_number;
    unsigned long long h_end_number;

    try {
        prev_hash_str = task_data.at("prev_hash").get<std::string>();
        transactions_str = task_data.at("transacciones").dump(); // Las transacciones son un array JSON, lo serializamos a string
        difficulty_prefix_str = task_data.at("dificultad").get<std::string>();
        h_start_number = task_data.at("start_nonce").get<unsigned long long>();
        h_end_number = task_data.at("end_nonce").get<unsigned long long>();
    } catch (const json::exception& e) {
        fprintf(stderr, "Error: Falta un campo requerido en el JSON de la tarea o formato incorrecto: %s\n", e.what());
        return 1;
    }

    // Construir la cadena base del bloque para el hash (prev_hash + transacciones_serializadas)
    // El formato del bloque para el hash es: hash_anterior + json_transacciones + nonce
    // Así que la cadena base es: hash_anterior + json_transacciones
    std::string block_base_string_std = prev_hash_str + transactions_str;
    const unsigned char* h_block_base_string = (const unsigned char*)block_base_string_std.c_str();
    unsigned long long block_base_string_len = block_base_string_std.length(); // Usar .length() para std::string

    // Verificar si la cadena base más el nonce excederán el buffer
    if (block_base_string_len + MAX_NUMBER_STR_LEN >= MAX_CONCAT_LEN) {
        fprintf(stderr, "Error: La longitud de la cadena base del bloque (%llu) más el nonce exceden el buffer (%d). Aumente MAX_CONCAT_LEN o revise los datos.\n", block_base_string_len, MAX_CONCAT_LEN);
        return 1;
    }

    unsigned char h_target_prefix_bytes[16]; // Max MD5 hash size
    // Convertir el prefijo de dificultad hexadecimal a bytes
    int target_prefix_len = hexStringToBytes(difficulty_prefix_str.c_str(), h_target_prefix_bytes);

    if (target_prefix_len == -1 || target_prefix_len == 0 || target_prefix_len > 16) {
        fprintf(stderr, "Error: El prefijo de dificultad (%s) es inválido o su longitud no es adecuada (max 32 caracteres hex / 16 bytes). Longitud de bytes: %d\n", difficulty_prefix_str.c_str(), target_prefix_len);
        return 1;
    }
    
    if (h_start_number > h_end_number) {
        fprintf(stderr, "Error: El número de inicio del nonce (%llu) no puede ser mayor que el número de fin (%llu).\n", h_start_number, h_end_number);
        return 1;
    }
    
    unsigned long long total_numbers_to_search;
    if (h_end_number < h_start_number) {
        total_numbers_to_search = 0;
    } else {
        total_numbers_to_search = h_end_number - h_start_number + 1;
    }

    if (total_numbers_to_search == 0) {
        // En este caso, el Worker no debería haber enviado una tarea así, pero lo manejamos.
        json result_json;
        result_json["status"] = "no_solution_found";
        result_json["reason"] = "Rango de nonce vacío.";
        std::cout << result_json.dump() << std::endl; // Imprime JSON a stdout
        return 0; // Termina con éxito, pero sin solución
    }

    unsigned char h_final_hash[16];
    char h_final_number_string[MAX_NUMBER_STR_LEN];
    bool found_solution = false;

    // Impresión de estado (para depuración, se puede quitar en producción)
    fprintf(stderr, "Iniciando minado para hash previo: '%s', dificultad: '%s'\n", prev_hash_str.c_str(), difficulty_prefix_str.c_str());
    fprintf(stderr, "Rango de nonce: desde %llu hasta %llu\n", h_start_number, h_end_number);
    fprintf(stderr, "Longitud del prefijo a comparar (en bytes): %d\n", target_prefix_len);
    fprintf(stderr, "Espacio de búsqueda total en este rango: %llu nonces\n", total_numbers_to_search);
    fprintf(stderr, "--- Minando (CPU), por favor espere ---\n");

    auto start_time = std::chrono::high_resolution_clock::now();

    found_solution = md5_prefix_cracker_cpu(
        h_block_base_string, block_base_string_len,
        h_target_prefix_bytes, target_prefix_len,
        h_final_hash, h_final_number_string,
        h_start_number, h_end_number
    );

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end_time - start_time;

    json result_json; // Objeto JSON para la salida

    if (found_solution) {
        // Convertir el hash binario a string hexadecimal para la salida JSON
        char final_hash_hex_str[33]; // 16 bytes * 2 chars/byte + null terminator
        for (int i = 0; i < 16; ++i) {
            sprintf(&final_hash_hex_str[i*2], "%02x", (unsigned char)h_final_hash[i]);
        }
        final_hash_hex_str[32] = '\0'; // Asegura el null terminator

        result_json["status"] = "solution_found";
        result_json["nonce_found"] = std::stoull(h_final_number_string); // Convierte string a ULL
        result_json["block_hash_result"] = std::string(final_hash_hex_str);
        result_json["elapsed_time_ms"] = duration.count();

        fprintf(stderr, "\n--- SOLUCIÓN ENCONTRADA (CPU) ---\n");
        fprintf(stderr, "Nonce: %s\n", h_final_number_string);
        fprintf(stderr, "Hash MD5 resultante: %s\n", final_hash_hex_str);
        fprintf(stderr, "Tiempo de ejecución: %.2f ms\n", duration.count());

    } else {
        result_json["status"] = "no_solution_found";
        result_json["elapsed_time_ms"] = duration.count();
        result_json["reason"] = "No se encontró un nonce en el rango especificado que cumpla con la dificultad.";
        fprintf(stderr, "\n--- No se encontró una solución en el rango [%llu - %llu] (CPU) ---\n", h_start_number, h_end_number);
        fprintf(stderr, "Tiempo de ejecución: %.2f ms\n", duration.count());
    }

    // Imprimir el resultado JSON a la salida estándar
    std::cout << result_json.dump() << std::endl;

    return 0;
}