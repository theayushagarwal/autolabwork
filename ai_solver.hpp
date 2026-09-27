#pragma once
#include <string>
#include <iostream>
#include "config.hpp"
#include "groq_client.hpp"
#include "gemini_client.hpp"

namespace ai {

// Determines whether to use Groq or Gemini based on user config and available API keys.
inline std::string solve_problem_text(const std::string& problem_text) {
    std::string groq_key = config::groq_api_key();
    std::string gemini_key = config::gemini_api_key();

    bool groq_available = (!groq_key.empty() && groq_key != "YOUR_GROQ_API_KEY_HERE");
    bool gemini_available = (!gemini_key.empty() && gemini_key != "YOUR_GEMINI_API_KEY_HERE");

    bool use_groq = true;

    if (config::PREFERRED_PROVIDER == "groq") {
        use_groq = true;
    } else if (config::PREFERRED_PROVIDER == "gemini") {
        use_groq = false;
    } else {
        // "auto" mode:
        if (groq_available) {
            use_groq = true; // Groq is 100% free and fastest
        } else if (gemini_available) {
            use_groq = false;
        } else {
            // Default to Groq guide if neither is configured
            use_groq = true;
        }
    }

    if (use_groq) {
        std::cout << "[*] Sending problem text to Groq (" << config::GROQ_MODEL
                  << " - Free & Ultra-Fast)..." << std::endl;
        return groq::solve_from_text(problem_text);
    } else {
        std::cout << "[*] Sending problem text to Gemini (" << config::GEMINI_MODEL
                  << ")..." << std::endl;
        return gemini::solve_from_text(problem_text);
    }
}

} // namespace ai
