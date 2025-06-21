// json_interface.cpp
#include "json_interface.h"
#include "json.hpp"           // nlohmann/json single_include
#include <fstream>
#include <limits>
#include <stdexcept>
#include <iostream> // Para depuración

using json = nlohmann::json;

void guardarResultadoJSON(const std::string &nonce,
                          const std::string &hash_hex,
                          double elapsed_ms) {
    json j;

    if (nonce.empty()) {
        j["status"] = "no_solution_found";
        j["nonce_found"] = nullptr;
        j["block_hash_result"] = "";
    } else {
        j["status"] = "solution_found";
        try {
            j["nonce_found"] = std::stoull(nonce);
        } catch (const std::invalid_argument& e) {
            std::cerr << "Error: No se pudo convertir nonce '" << nonce << "' a unsigned long long: " << e.what() << std::endl;
            j["nonce_found"] = "ERROR_INVALID_NONCE";
        } catch (const std::out_of_range& e) {
            std::cerr << "Error: Nonce '" << nonce << "' fuera de rango para unsigned long long: " << e.what() << std::endl;
            j["nonce_found"] = "ERROR_OUT_OF_RANGE";
        }
        j["block_hash_result"] = hash_hex;
    }
    j["elapsed_time_ms"] = elapsed_ms;

    std::ofstream ofs("resultado.json");
    if (ofs.is_open()) {
        ofs << j.dump(4);
    } else {
        std::cerr << "Error: No se pudo abrir 'resultado.json' para escribir." << std::endl;
    }
}

// Nueva implementación de la función de parsing
MiningTaskParams parseMiningTaskJSON(const std::string& json_string) {
    MiningTaskParams params;
    params.parse_success = false; // Inicialmente, asumimos que falla

    try {
        json task_json = json::parse(json_string);

        // Intenta obtener cada campo. Usa .value() con un valor por defecto
        // para evitar excepciones si un campo no existe.
        params.prev_hash_str = task_json.value("prev_hash", "");
        // Asume que "transacciones" es un array de objetos y si necesitas concatenarlos
        // deberías hacerlo aquí. Por ahora, si no viene como string, lo dejamos vacío o lo adaptas.
        // Ejemplo simplificado:
        // if (task_json.contains("transacciones") && task_json["transacciones"].is_array()) {
        //     for (const auto& tx : task_json["transacciones"]) {
        //         params.transactions_str += tx.dump(); // O solo ciertas partes de la transacción
        //     }
        // }
        params.difficulty_prefix_str = task_json.value("dificultad", "");
        params.start_nonce = task_json.value("start_nonce", 0ULL);
        params.end_nonce = task_json.value("end_nonce", 0ULL);
        params.index_str = std::to_string(task_json.value("index", 0)); // Convierte a string

        params.parse_success = true; // Si llegamos aquí, el parsing fue exitoso

    } catch (const json::exception& e) {
        std::cerr << "Error al parsear JSON de entrada en json_interface.cpp: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error inesperado al procesar JSON de entrada en json_interface.cpp: " << e.what() << std::endl;
    }
    return params;
}