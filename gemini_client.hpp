#pragma once
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <algorithm>
#include <iostream>
#include <nlohmann/json.hpp>
#include "http_client.hpp"
#include "base64.hpp"
#include "config.hpp"

namespace gemini {

using json = nlohmann::json;

inline std::vector<unsigned char> read_file_bytes(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Could not open image file: " + path);
    }
    return std::vector<unsigned char>(std::istreambuf_iterator<char>(file),
                                       std::istreambuf_iterator<char>());
}

inline std::string mime_type_for(const std::string& path) {
    std::string lower = path;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (lower.size() >= 4 && lower.compare(lower.size() - 4, 4, ".png") == 0) {
        return "image/png";
    }
    return "image/jpeg";
}

// Strips ```lang / ``` markdown fences if Gemini adds them despite instructions.
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

// Hardened response parser: explicitly checks finishReason, content, and parts
inline std::string extract_code_from_gemini_response(const std::string& response_body) {
    json parsed;
    try {
        parsed = json::parse(response_body);
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse Gemini response as JSON: " + std::string(e.what()) + "\nResponse: " + response_body);
    }

    if (parsed.contains("promptFeedback") && parsed["promptFeedback"].contains("blockReason")) {
        std::string block_reason = parsed["promptFeedback"]["blockReason"].get<std::string>();
        throw std::runtime_error("Gemini request was blocked by prompt policy (blockReason: " + block_reason + ").");
    }

    if (parsed.contains("error") && parsed["error"].contains("message")) {
        throw std::runtime_error("Gemini API error: " + parsed["error"]["message"].get<std::string>());
    }

    if (!parsed.contains("candidates") || parsed["candidates"].empty()) {
        throw std::runtime_error("Gemini returned no candidates. Raw response: " + response_body);
    }

    const auto& candidate = parsed["candidates"][0];

    std::string finish_reason = candidate.value("finishReason", "UNKNOWN");
    if (finish_reason == "SAFETY") {
        throw std::runtime_error("Gemini generation blocked: finishReason is SAFETY.");
    } else if (finish_reason == "RECITATION") {
        throw std::runtime_error("Gemini generation blocked: finishReason is RECITATION.");
    } else if (finish_reason == "MAX_TOKENS") {
        std::cerr << "[!] Warning: Gemini response was truncated because MAX_TOKENS was reached." << std::endl;
    }

    if (!candidate.contains("content")) {
        throw std::runtime_error("Gemini candidate contains no 'content' object (finishReason: " + finish_reason + "). Raw response: " + response_body);
    }

    if (!candidate["content"].contains("parts") || candidate["content"]["parts"].empty()) {
        throw std::runtime_error("Gemini candidate content has no 'parts' array (finishReason: " + finish_reason + "). Raw response: " + response_body);
    }

    if (!candidate["content"]["parts"][0].contains("text")) {
        throw std::runtime_error("Gemini response part has no 'text' field (finishReason: " + finish_reason + "). Raw response: " + response_body);
    }

    std::string text = candidate["content"]["parts"][0]["text"].get<std::string>();
    return strip_markdown_fences(text);
}

// Sends extracted webpage text to Gemini and returns generated Python code.
inline std::string solve_from_text(const std::string& problem_text) {
    std::string api_key = config::gemini_api_key();
    if (api_key.empty() || api_key == "YOUR_GEMINI_API_KEY_HERE") {
        throw std::runtime_error("GEMINI_API_KEY is not set! Set the environment variable GEMINI_API_KEY or update config.hpp.\n"
                                 "Get your key at https://aistudio.google.com/apikey");
    }

    const std::string prompt =
        "The following text was extracted from a coding problem webpage.\n"
        "Solve it in clean, basic standard PYTHON 3.\n"
        "Coding Style: Use common student-level Python constructs: map(), list, dictionary (dict), set, simple for/while loops, and basic if-else checks.\n"
        "Use standard input reading if needed: input().strip(), int(input()), or list(map(int, input().split())).\n"
        "Do NOT write overly advanced, convoluted, or obscure code. Keep it simple, natural, and human-written.\n"
        "Reply with ONLY raw Python source code ready to run and pass tests. No explanations, no markdown fences.\n\n"
        "Problem Text:\n" + problem_text;

    json body = {
        {"contents", {{
            {"parts", {
                {{"text", prompt}}
            }}
        }}}
    };

    std::string url = "https://generativelanguage.googleapis.com/v1beta/models/" +
                       config::GEMINI_MODEL + ":generateContent?key=" + api_key;

    http::Response resp = http::post(url, body.dump());

    if (resp.status_code != 200) {
        throw std::runtime_error("Gemini API error (HTTP " + std::to_string(resp.status_code) +
                                  "): " + resp.body);
    }

    return extract_code_from_gemini_response(resp.body);
}

// Sends the screenshot to Gemini and returns generated Python code.
inline std::string solve_from_image(const std::string& image_path) {
    std::string api_key = config::gemini_api_key();
    if (api_key.empty() || api_key == "YOUR_GEMINI_API_KEY_HERE") {
        throw std::runtime_error("GEMINI_API_KEY is not set! Set the environment variable GEMINI_API_KEY or update config.hpp.\n"
                                 "Get your key at https://aistudio.google.com/apikey");
    }

    std::vector<unsigned char> image_bytes = read_file_bytes(image_path);
    std::string b64 = base64::encode(image_bytes);
    std::string mime = mime_type_for(image_path);

    const std::string prompt =
        "The attached image contains a coding question or problem statement.\n"
        "Solve it in clean, basic standard PYTHON 3.\n"
        "Coding Style: Use common student-level Python constructs: map(), list, dictionary (dict), set, simple for/while loops, and basic if-else checks.\n"
        "Use standard input reading if needed: input().strip(), int(input()), or list(map(int, input().split())).\n"
        "Do NOT write overly advanced, convoluted, or obscure code. Keep it simple, natural, and human-written.\n"
        "Reply with ONLY raw Python source code ready to run and pass tests. No explanations, no markdown fences.";

    json body = {
        {"contents", {{
            {"parts", {
                {{"inline_data", {{"mime_type", mime}, {"data", b64}}}},
                {{"text", prompt}}
            }}
        }}}
    };

    std::string url = "https://generativelanguage.googleapis.com/v1beta/models/" +
                       config::GEMINI_MODEL + ":generateContent?key=" + api_key;

    http::Response resp = http::post(url, body.dump());

    if (resp.status_code != 200) {
        throw std::runtime_error("Gemini API error (HTTP " + std::to_string(resp.status_code) +
                                  "): " + resp.body);
    }

    return extract_code_from_gemini_response(resp.body);
}

} // namespace gemini
