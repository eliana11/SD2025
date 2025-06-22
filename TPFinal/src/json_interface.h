// json_interface.h
#pragma once
#include <string>
#include <map> // Si necesitas pasar mapas, aunque para esto quizás no

// Estructura para contener los datos de la tarea de minería parseados
struct MiningTaskParams {
    std::string prev_hash_str;
    std::string transactions_str; // Opcional, si lo necesitas para la construcción del bloque
    std::string difficulty_prefix_str;
    unsigned long long start_nonce;
    unsigned long long end_nonce;
    std::string index_str; // Para el index del bloqu
    std::string original_json_string; // Almacena el JSON de entrada completo
    bool parse_success; // Para indicar si el parsing fue exitoso
};

// Guarda el resultado en un archivo JSON.
void guardarResultadoJSON(const std::string &nonce, const std::string &hash_hex, double elapsed_ms);

// Devuelve una estructura con los parámetros.
MiningTaskParams parseMiningTaskJSON(const std::string& json_string);