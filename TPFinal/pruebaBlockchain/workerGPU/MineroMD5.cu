#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <chrono>
#include <regex> // Para el regex en el host (CPU)
#include <limits.h> // Para ULLONG_MAX
#include <cstring>  // Para memcpy en el host, aunque no se usa directamente ahora
#include <cstdio>   // Para sprintf
#include <algorithm> // Para std::min

// Incluisiones de CUDA
#include <cuda_runtime.h>
#include <device_launch_parameters.h>

// Incluye la librería JSON (nlohmann/json)
#include "json.hpp" 

using json = nlohmann::json;

// --- Helper para errores CUDA ---
template <typename T>
void cudaCheck(T result, const char* call, const char* file, int line) {
    if (result != cudaSuccess) {
        std::cerr << "[CUDA ERROR] " << cudaGetErrorString(result)
                  << " in " << call << " at " << file << ":" << line << std::endl;
        std::exit(EXIT_FAILURE);
    }
}
#define CUDA_CHECK(x) cudaCheck((x), #x, __FILE__, __LINE__)

// --- Constantes Generales ---
enum { MD5_DIGEST_LENGTH = 16, MAX_JSON_LEN = 65536, MAX_ULL_STR = 32 };

// --- IMPLEMENTACIÓN DE MD5 EN CUDA (DEVICE) ---
// Adaptada de varios ejemplos de dominio público. No es altamente optimizada
// para producción, pero es determinista y correcta para el propósito.

typedef unsigned int uint32;

// Funciones F, G, H, I (según la especificación MD5)
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define I(x, y, z) ((y) ^ ((x) | (~z)))



// Rotación izquierda
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

// Constantes de rotación para las 4 rondas de MD5
#define S11 7
#define S12 12
#define S13 17
#define S14 22

#define S21 5
#define S22 9
#define S23 14
#define S24 20

#define S31 4
#define S32 11
#define S33 16
#define S34 23

#define S41 6
#define S42 10
#define S43 15
#define S44 21

// Operaciones para cada ronda (utilizan las Sxx definidas arriba)
#define FF(a, b, c, d, x, s, ac) { \
  (a) += F((b), (c), (d)) + (x) + (uint32)(ac); \
  (a) = ROTATE_LEFT((a), (s)); \
  (a) += (b); \
}
#define GG(a, b, c, d, x, s, ac) { \
  (a) += G((b), (c), (d)) + (x) + (uint32)(ac); \
  (a) = ROTATE_LEFT((a), (s)); \
  (a) += (b); \
}
#define HH(a, b, c, d, x, s, ac) { \
  (a) += H((b), (c), (d)) + (x) + (uint32)(ac); \
  (a) = ROTATE_LEFT((a), (s)); \
  (a) += (b); \
}
#define II(a, b, c, d, x, s, ac) { \
  (a) += I((b), (c), (d)) + (x) + (uint32)(ac); \
  (a) = ROTATE_LEFT((a), (s)); \
  (a) += (b); \
}

// Convertir 4 bytes a un uint32 (little-endian)
__device__ static uint32 bytes_to_uint32(const unsigned char* bytes) {
    return ((uint32)bytes[0]       ) |
           ((uint32)bytes[1] <<  8) |
           ((uint32)bytes[2] << 16) |
           ((uint32)bytes[3] << 24);
}

// Convertir uint32 a 4 bytes (little-endian)
__device__ static void uint32_to_bytes(uint32 val, unsigned char* bytes) {
    bytes[0] = (unsigned char)(val & 0xFF);
    bytes[1] = (unsigned char)((val >> 8) & 0xFF);
    bytes[2] = (unsigned char)((val >> 16) & 0xFF);
    bytes[3] = (unsigned char)((val >> 24) & 0xFF);
}

// Función MD5 real para CUDA device code
__device__ void md5_cuda_device(const unsigned char* data, size_t len, unsigned char* digest) {
    uint32 a_init = 0x67452301;
    uint32 b_init = 0xEFCDAB89;
    uint32 c_init = 0x98BADCFE;
    uint32 d_init = 0x10325476;

    uint32 a = a_init;
    uint32 b = b_init;
    uint32 c = c_init;
    uint32 d = d_init;

    // Calcular longitud de padding
    size_t original_len_bits = len * 8;
    // Añadir bit 1 de padding, luego ceros, y 64 bits para la longitud.
    // len + 1 (para 0x80) + 8 (para longitud de 64 bits)
    // El 63 es para redondear al siguiente múltiplo de 64
    size_t padded_len = (len + 1 + 8 + 63) / 64 * 64; 
    
    // Usar puntero dinámico o __shared__ si MAX_JSON_LEN + 64 es demasiado grande para la pila de hilo.
    // Para simplificar, asumimos que stack suficientemente grande o que el compilador lo optimiza.
    unsigned char padded_data[MAX_JSON_LEN + 64]; 
    
    // Copiar los datos originales
    for (size_t i = 0; i < len; ++i) {
        padded_data[i] = data[i];
    }
    // Añadir el bit 0x80 y rellenar con ceros
    padded_data[len] = 0x80; 
    for (size_t i = len + 1; i < padded_len - 8; ++i) {
        padded_data[i] = 0x00; 
    }
    // Añadir la longitud original en bits (64 bits, little-endian)
    uint32_to_bytes((uint32)(original_len_bits & 0xFFFFFFFF), &padded_data[padded_len - 8]);
    uint32_to_bytes((uint32)(original_len_bits >> 32), &padded_data[padded_len - 4]);

    for (size_t i = 0; i < padded_len; i += 64) {
        uint32 M[16];
        for (int j = 0; j < 16; ++j) {
            M[j] = bytes_to_uint32(&padded_data[i + j * 4]);
        }

        uint32 AA = a, BB = b, CC = c, DD = d;

        // Ronda 1
        FF(a, b, c, d, M[0], S11, 0xD76AA478);
        FF(d, a, b, c, M[1], S12, 0xE8C7B756);
        FF(c, d, a, b, M[2], S13, 0x242070DB);
        FF(b, c, d, a, M[3], S14, 0xC1BDCEEE);
        FF(a, b, c, d, M[4], S11, 0xF57C0FAF);
        FF(d, a, b, c, M[5], S12, 0x4787C62A);
        FF(c, d, a, b, M[6], S13, 0xA8304613);
        FF(b, c, d, a, M[7], S14, 0xFD469501);
        FF(a, b, c, d, M[8], S11, 0x698098D8);
        FF(d, a, b, c, M[9], S12, 0x8B44F7AF);
        FF(c, d, a, b, M[10], S13, 0xFFFF5BB1);
        FF(b, c, d, a, M[11], S14, 0x895CD7BE);
        FF(a, b, c, d, M[12], S11, 0x6B901122);
        FF(d, a, b, c, M[13], S12, 0xFD987193);
        FF(c, d, a, b, M[14], S13, 0xA679438E);
        FF(b, c, d, a, M[15], S14, 0x49B40821);

        // Ronda 2
        GG(a, b, c, d, M[1], S21, 0xF61E2562);
        GG(d, a, b, c, M[6], S22, 0xC040B340);
        GG(c, d, a, b, M[11], S23, 0x265E5A51);
        GG(b, c, d, a, M[0], S24, 0xE9B6C7AA);
        GG(a, b, c, d, M[5], S21, 0xD62F105D);
        GG(d, a, b, c, M[10], S22, 0x02441453);
        GG(c, d, a, b, M[15], S23, 0xD8A1E681);
        GG(b, c, d, a, M[4], S24, 0xE7D3FBC8);
        GG(a, b, c, d, M[9], S21, 0x21E1CDE6);
        GG(d, a, b, c, M[14], S22, 0xC33707D6);
        GG(c, d, a, b, M[3], S23, 0xF4D50D87);
        GG(b, c, d, a, M[8], S24, 0x455A14ED);
        GG(a, b, c, d, M[13], S21, 0xA9E3E905);
        GG(d, a, b, c, M[2], S22, 0xFCEFA3F8);
        GG(c, d, a, b, M[7], S23, 0x676F02D9);
        GG(b, c, d, a, M[12], S24, 0x8D2A4C8A);

        // Ronda 3
        HH(a, b, c, d, M[5], S31, 0xFFFA3942);
        HH(d, a, b, c, M[8], S32, 0x8771F681);
        HH(c, d, a, b, M[11], S33, 0x6D9D6122);
        HH(b, c, d, a, M[14], S34, 0xFDE5380C);
        HH(a, b, c, d, M[1], S31, 0xA4BEEA44);
        HH(d, a, b, c, M[4], S32, 0x4BDECFA9);
        HH(c, d, a, b, M[7], S33, 0xF6BB4B60);
        HH(b, c, d, a, M[10], S34, 0xBEBFBC70);
        HH(a, b, c, d, M[13], S31, 0x289B7EC6);
        HH(d, a, b, c, M[0], S32, 0xEAA127FA);
        HH(c, d, a, b, M[3], S33, 0xD4EF3085);
        HH(b, c, d, a, M[6], S34, 0x04881D05);
        HH(a, b, c, d, M[9], S31, 0xD9D4D039);
        HH(d, a, b, c, M[12], S32, 0xE6DB99E5);
        HH(c, d, a, b, M[15], S33, 0x1FA27CF8);
        HH(b, c, d, a, M[2], S34, 0xC4AC5665);

        // Ronda 4
        II(a, b, c, d, M[0], S41, 0xF4292244);
        II(d, a, b, c, M[7], S42, 0x432AFF97);
        II(c, d, a, b, M[14], S43, 0xAB9423A7);
        II(b, c, d, a, M[5], S44, 0xFC93A039);
        II(a, b, c, d, M[12], S41, 0x655B59C3);
        II(d, a, b, c, M[3], S42, 0x8F0CCC92);
        II(c, d, a, b, M[10], S43, 0xFFEFF47D);
        II(b, c, d, a, M[1], S44, 0x85845DD1);
        II(a, b, c, d, M[8], S41, 0x6FA87E4F);
        II(d, a, b, c, M[15], S42, 0xFE2CE6E0);
        II(c, d, a, b, M[6], S43, 0xA3014314);
        II(b, c, d, a, M[13], S44, 0x4E0811A1);
        II(a, b, c, d, M[4], S41, 0xF7537E82);
        II(d, a, b, c, M[11], S42, 0xBD3AF235);
        II(c, d, a, b, M[2], S43, 0x2AD7D2BB);
        II(b, c, d, a, M[9], S44, 0xEB86D391);

        // Sumar los resultados a los buffers iniciales
        a += AA; b += BB; c += CC; d += DD;
    }
    
    // Almacenar el digest final en el array de salida
    uint32_to_bytes(a, &digest[0]);
    uint32_to_bytes(b, &digest[4]);
    uint32_to_bytes(c, &digest[8]);
    uint32_to_bytes(d, &digest[12]);
}

// --- Convierte unsigned long long a string en device ---
__device__ void ulong_to_str(unsigned long long n, char* str, int& len) {
    len = 0;
    if (n == 0) {
        str[len++] = '0';
        str[len]   = '\0';
        return;
    }
    char tmp[MAX_ULL_STR];
    int  i = 0;
    unsigned long long temp_n = n; 
    while (temp_n > 0 && i < MAX_ULL_STR -1 ) { // Asegurar que no se desborde tmp
        tmp[i++] = char('0' + (temp_n % 10));
        temp_n /= 10;
    }
    // Invertir el string
    while (i > 0 && len < MAX_ULL_STR -1) { // Asegurar que no se desborde str
        str[len++] = tmp[--i];
    }
    str[len] = '\0'; 
}

// --- Estructura de resultados en GPU ---
struct GpuResult {
    unsigned long long found_nonce;
    unsigned char      block_hash[MD5_DIGEST_LENGTH];
    int                solution_found;
};

// --- Kernel de minería ---
__global__ void mineKernel(
    const char* prefix,      int prefix_len,
    const char* suffix,      int suffix_len,
    unsigned long long       start_nonce,
    unsigned long long       end_nonce,
    const unsigned char* target_prefix,
    int                      target_len,
    GpuResult* res_d
) {
    unsigned long long idx   = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned long long nonce = start_nonce + idx;

    // Primer punto de depuración: solo el primer hilo del primer bloque
    // Esto verifica que el kernel se lanza y los argumentos iniciales son correctos.
    if (threadIdx.x == 0 && blockIdx.x == 0 && nonce == start_nonce) { 
        printf("DEBUG GPU: Kernel alcanzado por Nonce %llu\n", nonce); 
    }

    if (nonce > end_nonce) return;
    
    // Si otro hilo ya encontró una solución, este hilo puede terminar temprano.
    if (atomicAdd(&res_d->solution_found, 0) > 0) return; 

    char buffer[MAX_JSON_LEN]; 
    int  pos = 0;

    // Copiar la parte del JSON antes del nonce (incluye "nonce":)
    if (pos + prefix_len >= MAX_JSON_LEN) return; 
    for (int i = 0; i < prefix_len; ++i) buffer[pos++] = prefix[i];

    // Convertir y copiar el nonce como string
    char nstr[MAX_ULL_STR];
    int  nlen;
    ulong_to_str(nonce, nstr, nlen);
    if (pos + nlen >= MAX_JSON_LEN) return; 
    for (int i = 0; i < nlen; ++i) buffer[pos++] = nstr[i];

    // Copiar la parte del JSON después del nonce (el resto de la cadena JSON)
    if (pos + suffix_len >= MAX_JSON_LEN) return; 
    for (int i = 0; i < suffix_len; ++i) buffer[pos++] = suffix[i];

    // Validación final del tamaño
    if (pos >= MAX_JSON_LEN) {
        return; 
    }

    // Segundo punto de depuración: muestra la cadena JSON completa para los primeros nonces
    // Limita la salida para que no sature la consola si el rango es grande
    if (threadIdx.x == 0 && blockIdx.x == 0 && nonce < 100) { 
        printf("GPU (Nonce %llu) Input (len %d): %.*s\n", nonce, pos, pos, buffer);
    }

    unsigned char hash[MD5_DIGEST_LENGTH];
    md5_cuda_device(reinterpret_cast<const unsigned char*>(buffer), pos, hash);

    bool ok = true;
    for (int i = 0; i < target_len; ++i) {
        if (hash[i] != target_prefix[i]) { ok = false; break; }
    }
    if (!ok) return;

    unsigned long long prev_nonce_in_result = atomicCAS(&res_d->found_nonce, ULLONG_MAX, nonce);
    if (prev_nonce_in_result == ULLONG_MAX) { 
        atomicExch(&res_d->solution_found, 1); 
        for (int i = 0; i < MD5_DIGEST_LENGTH; ++i) {
            res_d->block_hash[i] = hash[i];
        }
    }
}

// --- Funciones de Ayuda para el Host (CPU) ---
void log_host(const std::string& msg) {
    std::cerr << "[LOG] " << msg << std::endl;
}

unsigned long long parse_ull(const char* s, const std::string& name) {
    try {
        return std::stoull(s);
    } catch (const std::out_of_range& e) {
        log_host("Error parseando " + name + ": El valor \"" + s + "\" está fuera del rango de unsigned long long. Detalle: " + e.what());
        std::exit(1);
    } catch (const std::invalid_argument& e) {
        log_host("Error parseando " + name + ": El valor \"" + s + "\" no es un número válido. Detalle: " + e.what());
        std::exit(1);
    } catch (...) {
        log_host("Error desconocido parseando " + name + ": \"" + s + "\"");
        std::exit(1);
    }
}

json load_json(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        log_host("Error: No se pudo abrir el archivo JSON: " + path);
        std::exit(1);
    }
    std::stringstream ss;
    ss << in.rdbuf();
    try {
        return json::parse(ss.str());
    } catch (const json::parse_error& e) {
        log_host("Error de parseo JSON en '" + path + "': " + std::string(e.what()));
        std::exit(1);
    }
}

std::string extract_diff(const json& j) {
    if (j.count("configuracion") && j["configuracion"].count("dificultad")) {
        if (j["configuracion"]["dificultad"].is_string()) {
            return j["configuracion"]["dificultad"].get<std::string>();
        } else {
            log_host("Error: El campo 'dificultad' dentro de 'configuracion' no es una cadena.");
            std::exit(1);
        }
    }
    if (j.count("dificultad")) {
        if (j["dificultad"].is_string()) {
            return j["dificultad"].get<std::string>();
        } else {
            log_host("Error: El campo 'dificultad' no es una cadena.");
            std::exit(1);
        }
    }
    log_host("Error: Campo 'dificultad' no encontrado en el JSON. Asegúrate de que exista en 'configuracion' o directamente en la raíz.");
    std::exit(1);
}

int hex2bytes(const std::string& hex, unsigned char* out) {
    if (hex.length() % 2 != 0) {
        log_host("Error: La cadena hexadecimal de dificultad tiene longitud impar (" + std::to_string(hex.length()) + "). Debe ser par.");
        std::exit(1);
    }
    int bl = (int)hex.size()/2;
    for (int i = 0; i < bl; ++i) {
        try {
            out[i] = (unsigned char)std::stoi(hex.substr(2*i,2), nullptr, 16);
        } catch (const std::exception& e) {
            log_host("Error al convertir hex a bytes en '" + hex.substr(2*i,2) + "': " + e.what());
            std::exit(1);
        }
    }
    return bl;
}

// --- Función Principal (Main) del Host ---
int main(int argc, char** argv) {
    std::cerr.sync_with_stdio(true);
    std::cerr << std::unitbuf; 

    // Declaración de variables para el ámbito completo de main
    std::string prefix_str; 
    std::string suffix_str; 

    if (argc != 4) {
        log_host("Uso: MineroMD5CUDA <json_file> <start_nonce> <end_nonce>");
        return 1;
    }
    
    int dev;            
    cudaDeviceProp prop; 

    try {
        log_host("Inicializando ejecución CUDA...");

        CUDA_CHECK(cudaGetDevice(&dev));
        CUDA_CHECK(cudaGetDeviceProperties(&prop, dev));
        log_host(std::string("GPU: ") + prop.name);

        json jb = load_json(argv[1]);
        std::string diff = extract_diff(jb);
        log_host("Dificultad: " + diff);

        unsigned char target[MD5_DIGEST_LENGTH];
        int           tlen = hex2bytes(diff, target);

        // 1. Eliminar el nonce si existe del JSON cargado
        if (jb.count("nonce")) {
            jb.erase("nonce");
        }

        // 2. Crear un nuevo JSON con el orden deseado para el hashing
        // Esto es crucial para que el nonce se inserte en la posición correcta.
        // Copiamos los campos en el orden que queremos para el hash
        json ordered_json;
        if (jb.count("index"))       ordered_json["index"] = jb["index"];
        ordered_json["nonce"] = 0; // Marcador temporal para el nonce
        if (jb.count("dificultad"))  ordered_json["dificultad"] = jb["dificultad"];
        if (jb.count("prev_hash"))   ordered_json["prev_hash"] = jb["prev_hash"];
        if (jb.count("timestamp"))   ordered_json["timestamp"] = jb["timestamp"];
        if (jb.count("transacciones")) ordered_json["transacciones"] = jb["transacciones"];
        // ¡Importante! Si tienes otros campos en tu JSON que no son 'index', 'nonce', 'dificultad',
        // 'prev_hash', 'timestamp' o 'transacciones', deberás añadirlos aquí en el orden correcto
        // para que sean parte del hash. Por ejemplo:
        // if (jb.count("otro_campo")) ordered_json["otro_campo"] = jb["otro_campo"];

        // Ahora, serializamos este JSON ordenado a una cadena compacta
        std::string compact_json_with_placeholder = ordered_json.dump();

        // 3. Encontrar la posición del marcador "nonce":0
        std::string nonce_placeholder = "\"nonce\":0";
        size_t nonce_pos_start = compact_json_with_placeholder.find(nonce_placeholder);

        if (nonce_pos_start == std::string::npos) {
            log_host("Error interno: No se encontró el marcador de nonce en el JSON reconstruido.");
            return 1;
        }

        // 4. Construir prefix_str y suffix_str
        // prefix_str será todo ANTES del "0" del nonce (incluye "nonce":)
        prefix_str = compact_json_with_placeholder.substr(0, nonce_pos_start + std::string("\"nonce\":").length());
        
        // suffix_str será todo DESPUÉS del "0" del nonce, incluyendo el '}' final
        suffix_str = compact_json_with_placeholder.substr(nonce_pos_start + nonce_placeholder.length());

        log_host("Prefix String para GPU (muestra): " + prefix_str.substr(0, std::min(prefix_str.length(), static_cast<size_t>(200))));
        log_host("Suffix String para GPU (muestra): " + suffix_str.substr(0, std::min(suffix_str.length(), static_cast<size_t>(200))));
        
        auto start_nonce = parse_ull(argv[2], "start_nonce");
        auto end_nonce   = parse_ull(argv[3], "end_nonce");
        if (start_nonce > end_nonce) {
            log_host("Error: Rango inválido. 'start_nonce' debe ser menor o igual a 'end_nonce'.");
            return 1;
        }

        char             *d_pre, *d_suf;
        unsigned char    *d_tar;
        GpuResult        *d_res;

        CUDA_CHECK(cudaMalloc(&d_pre, prefix_str.size()+1));
        CUDA_CHECK(cudaMalloc(&d_suf, suffix_str.size()+1));
        CUDA_CHECK(cudaMalloc(&d_tar, tlen));
        CUDA_CHECK(cudaMalloc(&d_res, sizeof(GpuResult)));

        CUDA_CHECK(cudaMemcpy(d_pre, prefix_str.c_str(), prefix_str.size()+1, cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemcpy(d_suf, suffix_str.c_str(), suffix_str.size()+1, cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemcpy(d_tar, target, tlen, cudaMemcpyHostToDevice));

        GpuResult init_res{ ULLONG_MAX, {0}, 0 }; 
        CUDA_CHECK(cudaMemcpy(d_res, &init_res, sizeof(init_res), cudaMemcpyHostToDevice)); 

        unsigned long long total_nonces_to_check = end_nonce - start_nonce + 1;
        int                threads_per_block = 256;
        int                num_blocks  = static_cast<int>((total_nonces_to_check + threads_per_block - 1) / threads_per_block);
        
        if (num_blocks > prop.maxGridSize[0]) {
            log_host("Advertencia: El número de bloques calculado (" + std::to_string(num_blocks) + 
                     ") excede el máximo de la GPU (" + std::to_string(prop.maxGridSize[0]) + "). Limitando bloques.");
            num_blocks = prop.maxGridSize[0];
        }

        log_host("Lanzando kernel con " + std::to_string(num_blocks) + " bloques de " + std::to_string(threads_per_block) + " hilos.");

        auto t0 = std::chrono::high_resolution_clock::now();
        mineKernel<<<num_blocks, threads_per_block>>>(
            d_pre, (int)prefix_str.size(),
            d_suf, (int)suffix_str.size(),
            start_nonce, end_nonce,
            d_tar, tlen,
            d_res
        );
        CUDA_CHECK(cudaDeviceSynchronize()); 
        auto t1 = std::chrono::high_resolution_clock::now();

        GpuResult final_output;
        CUDA_CHECK(cudaMemcpy(&final_output, d_res, sizeof(final_output), cudaMemcpyDeviceToHost));
        
        cudaFree(d_pre); 
        cudaFree(d_suf); 
        cudaFree(d_tar); 
        cudaFree(d_res);

        double elapsed_ms = std::chrono::duration<double,std::milli>(t1 - t0).count();
        json   result_json_output;
        result_json_output["elapsed_time_ms"] = int64_t(elapsed_ms);

        if (final_output.solution_found) {
            char hash_str[33]; 
            for (int i = 0; i < MD5_DIGEST_LENGTH; ++i) {
                sprintf(hash_str + 2*i, "%02x", final_output.block_hash[i]);
            }
            hash_str[32] = '\0'; 

            result_json_output["status"]             = "solution_found";
            result_json_output["nonce_found"]        = final_output.found_nonce;
            result_json_output["block_hash_result"]  = std::string(hash_str);
            log_host("¡SOLUCIÓN ENCONTRADA! Nonce: " + std::to_string(final_output.found_nonce) + ", Hash: " + std::string(hash_str));
        } else {
            result_json_output["status"] = "no_solution_found";
            result_json_output["reason"] = "No se encontró un nonce válido en el rango especificado.";
            log_host("No se encontró solución en el rango especificado.");
        }

        std::cout << result_json_output.dump() << std::endl;
        return 0;

    } catch (const std::exception& e) {
        log_host(std::string("Error fatal inesperado: ") + e.what());
        return 1;
    }
}