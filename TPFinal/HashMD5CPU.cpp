#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <chrono>
#include <cstring>
#include <cstdio>
#include <algorithm>
#include <limits.h>
#include <cstdlib>
#include <openssl/md5.h>
#include "json.hpp"

using json = nlohmann::json;

#define MAX_CONCAT_LEN 65536

void log(const std::string& msg) {
    std::cerr << "[LOG] " << msg << std::endl;
}

unsigned long long parse_ulong(const char* str, const std::string& name) {
    try {
        return std::stoull(str);
    } catch (const std::exception& e) {
        log("Error al convertir " + name + ": " + e.what());
        throw;
    }
}

int hexCharToInt(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int hexStringToBytes(const char* hex_string, unsigned char* byte_array) {
    int len = std::strlen(hex_string);
    if (len % 2 != 0) return -1;

    int byte_len = len / 2;
    for (int i = 0; i < byte_len; ++i) {
        int high = hexCharToInt(hex_string[i * 2]);
        int low  = hexCharToInt(hex_string[i * 2 + 1]);
        if (high == -1 || low == -1) return -1;
        byte_array[i] = (high << 4) | low;
    }
    return byte_len;
}

bool md5_matches_prefix(
    const unsigned char* block_data, size_t block_len,
    const unsigned char* prefix_bytes, unsigned int prefix_len,
    unsigned char* result_hash
) {
    unsigned char hash[MD5_DIGEST_LENGTH];
    MD5(block_data, block_len, hash);
    for (unsigned int i = 0; i < prefix_len; ++i) {
        if (hash[i] != prefix_bytes[i]) return false;
    }
    std::copy(hash, hash + MD5_DIGEST_LENGTH, result_hash);
    return true;
}

json cargar_bloque_json(const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        log("No se pudo abrir el archivo JSON: " + path);
        throw std::runtime_error("Archivo no accesible");
    }
    std::stringstream ss;
    ss << file.rdbuf();
    return json::parse(ss.str());
}

std::string extraer_dificultad(const json& bloque_json) {
    if (bloque_json.contains("configuracion") && bloque_json["configuracion"].contains("dificultad"))
        return bloque_json["configuracion"]["dificultad"].get<std::string>();
    if (bloque_json.contains("dificultad"))
        return bloque_json["dificultad"].get<std::string>();
    throw std::runtime_error("Campo dificultad no encontrado");
}

json minar(json bloque_json, unsigned long long start_nonce, unsigned long long end_nonce, 
           const unsigned char* target_prefix, int prefix_len) {
    unsigned char final_hash[MD5_DIGEST_LENGTH];
    unsigned long long nonce_encontrado = 0;
    bool encontrado = false;

    auto t0 = std::chrono::high_resolution_clock::now();

    for (unsigned long long nonce = start_nonce; nonce <= end_nonce; ++nonce) {
        bloque_json["nonce"] = nonce;
        std::string bloque_str = bloque_json.dump(-1, ' ', false, nlohmann::json::error_handler_t::strict);

        if (nonce == start_nonce || nonce == start_nonce + 1)
            log("Bloque serializado (nonce " + std::to_string(nonce) + "): " + bloque_str);

        if (md5_matches_prefix(
                reinterpret_cast<const unsigned char*>(bloque_str.c_str()),
                bloque_str.length(),
                target_prefix,
                prefix_len,
                final_hash)) {
            encontrado = true;
            nonce_encontrado = nonce;
            break;
        }
    }

    auto t1 = std::chrono::high_resolution_clock::now();
    auto ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    json resultado;
    resultado["elapsed_time_ms"] = static_cast<int64_t>(ms);

    if (encontrado) {
        char hash_str[33];
        for (int i = 0; i < MD5_DIGEST_LENGTH; ++i)
            sprintf(&hash_str[i * 2], "%02x", final_hash[i]);
        hash_str[32] = '\0';

        resultado["status"] = "solution_found";
        resultado["nonce_found"] = nonce_encontrado;
        resultado["block_hash_result"] = std::string(hash_str);
    } else {
        resultado["status"] = "no_solution_found";
        resultado["reason"] = "No se encontró un nonce válido.";
    }

    return resultado;
}

int main(int argc, char* argv[]) {
    if (argc != 4) {
        log("Uso: <ejecutable> <archivo_json> <start_nonce> <end_nonce>");
        return 1;
    }
    std::cerr.sync_with_stdio(true);
    std::cerr << std::unitbuf; // fuerza flush automático
    try {
        log("Inicializando ejecución...");
        std::string archivo_json = argv[1];
        unsigned long long start_nonce = parse_ulong(argv[2], "start_nonce");
        unsigned long long end_nonce   = parse_ulong(argv[3], "end_nonce");

        if (start_nonce > end_nonce) {
            log("Error: Rango de nonce inválido.");
            return 1;
        }

        log("Cargando JSON...");
        json bloque_json = cargar_bloque_json(archivo_json);

        log("Extrayendo dificultad...");
        std::string dificultad_hex = extraer_dificultad(bloque_json);
        log("Dificultad hex: " + dificultad_hex);

        unsigned char prefix_bytes[16];
        int prefix_len = hexStringToBytes(dificultad_hex.c_str(), prefix_bytes);
        if (prefix_len <= 0 || prefix_len > 16) {
            log("Prefijo de dificultad inválido.");
            return 1;
        }

        log("Iniciando búsqueda de nonce...");
        json resultado = minar(bloque_json, start_nonce, end_nonce, prefix_bytes, prefix_len);

        std::cout << resultado.dump() << std::endl;
        return 0;

    } catch (const std::exception& e) {
        log(std::string("Error fatal: ") + e.what());
        return 1;
    }
}
