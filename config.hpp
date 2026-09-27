#pragma once
#include <string>
#include <cstdlib>

namespace config {

// =============================================================================
// Target URLs (VIT Vellore Examly Portal)
// =============================================================================
inline const std::string LOGIN_URL = "https://vitvellore312.examly.io/login";
inline const std::string LABS_URL = "https://vitvellore312.examly.io/mycourses/details?id=e0d46aa1-e455-412f-b9b4-0a8c84889cc2&type=mylabs";
inline const std::string DEFAULT_URL = LOGIN_URL;

// Reads GROQ_API_KEY from environment if set, otherwise falls back to the configured key below.
inline std::string groq_api_key() {
    const char* env = std::getenv("GROQ_API_KEY");
    if (env != nullptr && std::string(env).size() > 0) {
        return std::string(env);
    }
    return "YOUR_GROQ_API_KEY_HERE";
}

// Reads GEMINI_API_KEY from environment if set, otherwise falls back to placeholder.
// Get a key at https://aistudio.google.com/apikey
inline std::string gemini_api_key() {
    const char* env = std::getenv("GEMINI_API_KEY");
    if (env != nullptr && std::string(env).size() > 0) {
        return std::string(env);
    }
    return "YOUR_GEMINI_API_KEY_HERE";
}

// Preferred AI provider:
// "auto"   -> Uses Groq if GROQ_API_KEY is set (100% free & ultra-fast), otherwise Gemini
// "groq"   -> Force Groq
// "gemini" -> Force Gemini (gemini-2.0-flash)
inline const std::string PREFERRED_PROVIDER = "groq";

// Models
inline const std::string GROQ_MODEL = "openai/gpt-oss-120b";
inline const std::string GEMINI_MODEL = "gemini-2.0-flash";

// Target Programming Language & Style
inline const std::string TARGET_LANGUAGE = "Python";

// =============================================================================
// Chrome Profile, Debugger Port & Stealth Options
// =============================================================================

// Default persistent profile directory (keeps logins, cookies, and tokens forever)
inline std::string get_default_profile_dir() {
    const char* local_app = std::getenv("LOCALAPPDATA");
    if (local_app != nullptr) {
        return std::string(local_app) + "\\Google\\Chrome\\NeoColabProfile";
    }
    return "C:\\Users\\ayush\\AppData\\Local\\Google\\Chrome\\NeoColabProfile";
}

inline const std::string CHROME_PROFILE_DIR = get_default_profile_dir();

// Remote debugging port
inline const int DEBUGGER_PORT = 9222;
inline const std::string DEBUGGER_ADDRESS = "127.0.0.1:9222";

// Probe port 9222 first: if healthy, attach to existing Chrome automatically; otherwise launch fresh instance.
inline const bool AUTO_DETECT_DEBUG_PORT = true;

// Hide automation flags (turns off 'Chrome is being controlled...' banner and navigator.webdriver)
inline const bool HIDE_AUTOMATION_FLAGS = true;

// Keep Chrome open permanently even after the program exits (detach mode)
inline const bool DETACH_BROWSER = true;

// =============================================================================
// DOM Selectors for Target Site (Inspect element -> Copy selector)
// =============================================================================

// CSS selector for the code editor. Examly uses Ace Editor (.ace_editor) or Monaco.
inline const std::string CODE_INPUT_SELECTOR = ".ace_editor";

// Optional: CSS selector to target only the problem description element.
// Leave empty ("") to extract the entire page via document.body.innerText.
inline const std::string PROBLEM_TEXT_SELECTOR = "";

// CSS selector for the "Compile & Run" / "Run Code" button.
// Leave empty ("") to skip test running and proceed directly.
inline const std::string RUN_BUTTON_SELECTOR = "";

// CSS selector for the test result box / console output.
// e.g., ".testcase-results", "#output", ".verdict"
inline const std::string TEST_RESULT_SELECTOR = "";

// Keyword indicating that test cases passed (case-insensitive search in TEST_RESULT_SELECTOR).
// e.g., "Passed", "Accepted", "Success", "Correct"
inline const std::string TEST_SUCCESS_KEYWORD = "Passed";

// CSS selector for the final "Submit" button.
inline const std::string SUBMIT_BUTTON_SELECTOR = "";

// CSS selector for the "Next Question" / "Next Problem" button.
// Leave empty ("") if single question or manual navigation.
inline const std::string NEXT_BUTTON_SELECTOR = "";

// =============================================================================
// Automation & Timing Settings
// =============================================================================

// Seconds to wait after page load/navigation for SPAs to render.
inline const int PAGE_LOAD_WAIT_SECONDS = 3;

// Max seconds to wait for compilation and test case execution to finish.
inline const int TEST_POLL_TIMEOUT_SECONDS = 45;

// Randomized delay before submitting (in seconds).
// 240s = 4 minutes, 360s = 6 minutes.
inline const int MIN_SUBMIT_DELAY_SECONDS = 240;
inline const int MAX_SUBMIT_DELAY_SECONDS = 360;

// Automatically advance to the next question when NEXT_BUTTON_SELECTOR is found.
inline const bool AUTO_ADVANCE_NEXT_QUESTION = true;

// chromedriver must already be running (e.g. `chromedriver` in another terminal).
inline const std::string CHROMEDRIVER_URL = "http://localhost:9515";

} // namespace config
