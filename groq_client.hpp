#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <stdexcept>
#include <nlohmann/json.hpp>
#include "http_client.hpp"
#include "config.hpp"

namespace groq {

using json = nlohmann::json;

// Strips ```lang / ``` markdown fences if the model wraps code in them.
inline std::string strip_markdown_fences(const std::string& text) {
    std::istringstream iss(text);
    std::string line, out;
    while (std::getline(iss, line)) {
        std::string trimmed = line;
        trimmed.erase(0, trimmed.find_first_not_of(" \t"));
        if (trimmed.rfind("```", 0) == 0) {
            continue; // skip fence lines
        }
        out += line + "\n";
    }
    if (!out.empty() && out.back() == '\n') out.pop_back();
    return out;
}

// Sends extracted webpage text to Groq's high-speed inference API and returns pure Python code.
inline std::string solve_from_text(const std::string& problem_text) {
    std::string api_key = config::groq_api_key();
    if (api_key.empty() || api_key == "YOUR_GROQ_API_KEY_HERE") {
        throw std::runtime_error("GROQ_API_KEY is not set! Set the environment variable GROQ_API_KEY or update config.hpp.\n"
                                 "Get your free key at https://console.groq.com/keys");
    }

    const std::string system_prompt =
        "You are a helpful student programmer.\n"
        "You will be given the extracted text content of a webpage containing a coding problem.\n"
        "Your task:\n"
        "1. Write the solution in clean, basic standard PYTHON 3.\n"
        "2. Coding Level & Style: Use common, straightforward student-level Python concepts: map(), list, dictionary (dict), set, simple for/while loops, and basic if-else checks.\n"
        "   - Use standard input reading patterns when required: e.g. input().strip(), int(input()), or list(map(int, input().split())).\n"
        "   - Avoid overly clever one-liners, obscure syntax, or complicated external libraries. The code must look natural, clear, and human-written by a beginner/intermediate programmer.\n"
        "3. Output ONLY the raw executable Python code ready to run and pass tests.\n"
        "STRICT RULE: Do NOT include any explanations, comments, or markdown code fences (like ```python or ```). Output raw Python code only.";

    json body = {
        {"model", config::GROQ_MODEL},
        {"messages", {
            {{"role", "system"}, {"content", system_prompt}},
            {{"role", "user"}, {"content", "Here is the webpage content containing the coding problem:\n\n" + problem_text}}
        }},
        {"temperature", 0.1}
    };

    std::string url = "https://api.groq.com/openai/v1/chat/completions";
    std::vector<std::string> headers = {
        "Authorization: Bearer " + api_key
    };

    http::Response resp = http::post(url, body.dump(), headers);

    if (resp.status_code != 200) {
        throw std::runtime_error("Groq API error (HTTP " + std::to_string(resp.status_code) + "): " + resp.body);
    }

    json parsed = json::parse(resp.body);

    if (!parsed.contains("choices") || parsed["choices"].empty()) {
        throw std::runtime_error("Groq returned no choices. Raw response: " + resp.body);
    }

    std::string text = parsed["choices"][0]["message"]["content"].get<std::string>();
    return strip_markdown_fences(text);
}

} // namespace groq
