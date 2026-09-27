#pragma once
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <iomanip>
#include <functional>
#include <ctime>
#include <nlohmann/json.hpp>

namespace cache {

using json = nlohmann::json;
inline const std::string CACHE_FILE = "solutions_cache.json";
inline const std::string LAST_SOLUTION_FILE = "last_solution.py";

// Computes a deterministic 64-bit hash string for any input text or binary
inline std::string hash_key(const std::string& input) {
    size_t h = std::hash<std::string>{}(input);
    std::stringstream ss;
    ss << std::hex << std::setw(16) << std::setfill('0') << h;
    return ss.str();
}

inline json load_cache() {
    std::ifstream file(CACHE_FILE);
    if (!file.is_open()) {
        return json::object();
    }
    try {
        json j;
        file >> j;
        return j;
    } catch (...) {
        return json::object();
    }
}

inline void save_cache(const json& j) {
    std::ofstream file(CACHE_FILE);
    if (file.is_open()) {
        file << j.dump(4);
    }
}

// Retrieves cached code if present, otherwise returns empty string
inline std::string get(const std::string& raw_input) {
    std::string key = hash_key(raw_input);
    json c = load_cache();
    if (c.contains(key) && c[key].contains("code")) {
        return c[key]["code"].get<std::string>();
    }
    return "";
}

// Stores generated solution into persistent cache and writes to last_solution.cpp
inline void put(const std::string& raw_input, const std::string& code, const std::string& context = "") {
    std::string key = hash_key(raw_input);
    json c = load_cache();
    c[key] = {
        {"code", code},
        {"context", context},
        {"timestamp", std::time(nullptr)}
    };
    save_cache(c);

    // Save to last_solution.cpp for instant access & review
    std::ofstream out(LAST_SOLUTION_FILE);
    if (out.is_open()) {
        out << code << std::endl;
        std::cout << "[SAVED] Solution saved to " << LAST_SOLUTION_FILE << " and " << CACHE_FILE << std::endl;
    }
}

} // namespace cache
