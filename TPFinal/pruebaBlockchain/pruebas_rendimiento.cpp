#include <iostream>
#include <chrono>
#include <openssl/md5.h>
#include <string>

int main() {
    const int num_hashes = 1'000'000;
    unsigned char result[MD5_DIGEST_LENGTH];
    std::string base = "test";

    auto start = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < num_hashes; ++i) {
        std::string data = base + std::to_string(i);
        MD5(reinterpret_cast<const unsigned char*>(data.c_str()), data.size(), result);
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    double hashrate = num_hashes / elapsed.count();

    std::cout << "Tiempo total: " << elapsed.count() << " segundos" << std::endl;
    std::cout << "Tasa de hash: " << hashrate << " hashes/segundo ("
              << hashrate / 1'000'000 << " MH/s)" << std::endl;

    return 0;
}
