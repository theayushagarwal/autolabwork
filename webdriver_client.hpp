#pragma once
// Talks directly to chromedriver's W3C WebDriver REST API using libcurl + JSON.
// Features:
// 1. Purges stale SingletonLocks to eliminate crash loops.
// 2. Active socket/HTTP handshake probing on port 9222 before attaching.
// 3. CDP Script Injection (Page.addScriptToEvaluateOnNewDocument) for 100% stealth.

#include <string>
#include <vector>
#include <stdexcept>
#include <thread>
#include <chrono>
#include <iostream>
#include <iomanip>
#include <random>
#include <algorithm>
#include <filesystem>
#include <nlohmann/json.hpp>
#include "http_client.hpp"
#include "config.hpp"

namespace webdriver {

using json = nlohmann::json;
namespace fs = std::filesystem;

// 1. Robust Persistent Profile: Detects and purges orphaned locks from past crashes
inline std::string get_robust_profile_dir() {
    std::string dir_str = config::CHROME_PROFILE_DIR;
    try {
        fs::path profile_dir(dir_str);
        fs::create_directories(profile_dir);

        // Clear orphaned lock files left behind by crashes
        const std::vector<std::string> stale_locks = {
            "SingletonLock",
            "SingletonSocket",
            "SingletonCookie"
        };

        for (const auto& lock_name : stale_locks) {
            fs::path lock_path = profile_dir / lock_name;
            if (fs::exists(lock_path)) {
                std::error_code ec;
                fs::remove(lock_path, ec);
                if (!ec) {
                    std::cout << "[✓] Purged stale lock file: " << lock_name << std::endl;
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[!] Note cleaning profile locks: " << e.what() << std::endl;
    }
    return dir_str;
}

// 2. Robust Port Attachment: Probes Chrome's DevTools Protocol endpoint (JSON version)
inline bool is_chrome_debug_port_healthy(int port = 9222, long timeout_seconds = 1) {
    try {
        std::string url = "http://127.0.0.1:" + std::to_string(port) + "/json/version";
        http::Response resp = http::get(url, {}, timeout_seconds);
        if (resp.status_code == 200 && !resp.body.empty()) {
            json data = json::parse(resp.body);
            return data.contains("webSocketDebuggerUrl");
        }
    } catch (...) {
        // Port is either closed or unresponsive
    }
    return false;
}

// Generates a random integer delay between min_sec and max_sec (e.g. 240s to 360s)
inline int get_random_delay_seconds(int min_sec, int max_sec) {
    if (min_sec >= max_sec) return min_sec;
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist(min_sec, max_sec);
    return dist(gen);
}

// Displays a live countdown timer during the randomized delay
inline void sleep_with_countdown(int total_seconds) {
    int minutes = total_seconds / 60;
    int seconds = total_seconds % 60;
    std::cout << "\n[*] Pacing delay active: waiting " << total_seconds << "s (~"
              << minutes << "m " << seconds << "s) before submitting..." << std::endl;

    for (int rem = total_seconds; rem > 0; --rem) {
        int m = rem / 60;
        int s = rem % 60;
        std::cout << "\r[*] Submitting in: " << m << "m "
                  << std::setw(2) << std::setfill('0') << s << "s remaining... " << std::flush;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    std::cout << "\r[OK] Wait period complete! Proceeding to submit...                          \n" << std::endl;
}

class Session {
public:
    Session() {
        json chrome_options = json::object();

        // 1. Check if healthy Chrome instance is ALREADY running on port 9222
        if (config::AUTO_DETECT_DEBUG_PORT && is_chrome_debug_port_healthy(config::DEBUGGER_PORT, 1)) {
            std::cout << "[✓] Detected healthy Chrome on port " << config::DEBUGGER_PORT << ". Attaching..." << std::endl;
            chrome_options["debuggerAddress"] = config::DEBUGGER_ADDRESS;
        } else {
            // 2. Launch new Chrome instance with persistent profile & crash protection
            std::cout << "[*] Launching new Chrome instance with persistent profile..." << std::endl;
            std::string profile_dir = get_robust_profile_dir();

            std::vector<std::string> args = {
                "--start-maximized",
                "--user-data-dir=" + profile_dir,
                "--profile-directory=Default",
                "--remote-debugging-port=" + std::to_string(config::DEBUGGER_PORT),
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check"
            };

            chrome_options["args"] = args;
            if (config::HIDE_AUTOMATION_FLAGS) {
                chrome_options["excludeSwitches"] = json::array({"enable-automation"});
            }
            if (config::DETACH_BROWSER) {
                chrome_options["detach"] = true;
            }
        }

        json body = {
            {"capabilities", {
                {"alwaysMatch", {
                    {"browserName", "chrome"},
                    {"goog:chromeOptions", chrome_options}
                }}
            }}
        };

        auto resp = http::post(config::CHROMEDRIVER_URL + "/session", body.dump());
        if (resp.status_code != 200) {
            throw std::runtime_error("Failed to start chromedriver session. Is `chromedriver` running on localhost:9515?\n"
                                     "Response: " + resp.body);
        }

        json parsed = json::parse(resp.body);
        session_id_ = parsed["value"]["sessionId"].get<std::string>();

        // 3. Inject CDP Stealth Layer (Page.addScriptToEvaluateOnNewDocument)
        apply_stealth_cdp();
        std::cout << "[✓] Browser ready and connected." << std::endl;
    }

    ~Session() {
        // If detach mode is enabled, keep Chrome running so profile and session stay open!
        if (!config::DETACH_BROWSER) {
            try {
                http::request(base_url(), "DELETE");
            } catch (...) {
                // best-effort cleanup on shutdown
            }
        } else {
            std::cout << "[*] Browser detached: session left running so you stay logged in." << std::endl;
        }
    }

    // 3. Robust Browser Stealth: CDP Script Injection (Page.addScriptToEvaluateOnNewDocument)
    // Runs before any website JavaScript loads on any tab or iframe
    void apply_stealth_cdp() {
        if (!config::HIDE_AUTOMATION_FLAGS) return;
        try {
            const std::string stealth_source = R"(
                // 1. Remove navigator.webdriver flag cleanly
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // 2. Mock standard chrome object if missing
                window.chrome = window.chrome || {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // 3. Mock standard plugins array (real browsers have plugins)
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            )";

            json body = {
                {"cmd", "Page.addScriptToEvaluateOnNewDocument"},
                {"params", {
                    {"source", stealth_source}
                }}
            };

            auto resp = http::post(base_url() + "/goog/cdp/execute", body.dump());
            if (resp.status_code == 200) {
                std::cout << "[✓] Injected CDP Stealth Layer (Page.addScriptToEvaluateOnNewDocument)." << std::endl;
            }
        } catch (...) {
            // CDP extension command not supported on older versions, fallback to in-page injection
        }
    }

    void navigate(const std::string& url) {
        if (url == "current" || url.empty()) {
            std::cout << "[*] Operating on currently active tab (skipping navigation)." << std::endl;
            return;
        }

        json body = {{"url", url}};
        auto resp = http::post(base_url() + "/url", body.dump());
        if (resp.status_code != 200) {
            throw std::runtime_error("Navigation failed: " + resp.body);
        }
    }

    // Switches WebDriver focus to the most recently opened tab (essential if Examly opens problems in a new tab)
    void switch_to_latest_tab() {
        try {
            auto resp = http::get(base_url() + "/window/handles");
            if (resp.status_code == 200) {
                json parsed = json::parse(resp.body);
                if (parsed.contains("value") && parsed["value"].is_array() && !parsed["value"].empty()) {
                    std::string latest_handle = parsed["value"].back().get<std::string>();
                    json body = {{"handle", latest_handle}};
                    http::post(base_url() + "/window", body.dump());
                }
            }
        } catch (...) {
            // best-effort
        }
    }

    // Executes synchronous JavaScript inside the active page context with optional arguments.
    std::string execute_script(const std::string& script, const json& args = json::array()) {
        json body = {
            {"script", script},
            {"args", args.is_array() ? args : json::array({args})}
        };
        auto resp = http::post(base_url() + "/execute/sync", body.dump());
        if (resp.status_code != 200) {
            throw std::runtime_error("execute_script failed: " + resp.body);
        }
        json parsed = json::parse(resp.body);
        if (parsed.contains("value") && !parsed["value"].is_null()) {
            if (parsed["value"].is_string()) {
                return parsed["value"].get<std::string>();
            }
            return parsed["value"].dump();
        }
        return "";
    }

    // Directly populates modern code editors, specifically optimized for Ace Editor.
    bool set_editor_content(const std::string& selector, const std::string& code) {
        std::string script = R"(
            const val = arguments[0];
            const sel = arguments[1] || '.ace_editor';

            // ==========================================
            // Priority 1: Ace Editor (Robust detection)
            // ==========================================
            const aceEl = document.querySelector(sel) || document.querySelector('.ace_editor');
            if (aceEl) {
                // Method 1A: Internal .env.editor reference (always present on Ace DOM elements)
                if (aceEl.env && aceEl.env.editor) {
                    aceEl.env.editor.setValue(val, 1);
                    aceEl.env.editor.clearSelection();
                    return true;
                }

                // Method 1B: Global window.ace.edit()
                if (window.ace && typeof window.ace.edit === 'function') {
                    try {
                        const editor = window.ace.edit(aceEl);
                        if (editor) {
                            editor.setValue(val, 1);
                            editor.clearSelection();
                            return true;
                        }
                    } catch (e) {}
                }
            }

            // ==========================================
            // Priority 2: Monaco Editor (VS Code in browser)
            // ==========================================
            if (window.monaco && window.monaco.editor && window.monaco.editor.getModels().length > 0) {
                window.monaco.editor.getModels()[0].setValue(val);
                return true;
            }

            // ==========================================
            // Priority 3: CodeMirror 5 & 6
            // ==========================================
            const cmElem = document.querySelector('.CodeMirror');
            if (cmElem && cmElem.CodeMirror) {
                cmElem.CodeMirror.setValue(val);
                return true;
            }

            const cm6 = document.querySelector('.cm-editor');
            if (cm6 && cm6.view) {
                cm6.view.dispatch({
                    changes: { from: 0, to: cm6.view.state.doc.length, insert: val }
                });
                return true;
            }

            // ==========================================
            // Priority 4: Standard textarea / input
            // ==========================================
            const el = document.querySelector(sel);
            if (el) {
                el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }

            return false;
        )";

        json args = json::array({code, selector});
        std::string result = execute_script(script, args);
        return (result == "true");
    }

    // Extracts the question / problem text from the page.
    std::string extract_problem_text() {
        if (!config::PROBLEM_TEXT_SELECTOR.empty()) {
            std::string script =
                "var el = document.querySelector('" + config::PROBLEM_TEXT_SELECTOR + "');"
                "return el ? el.innerText : '';";
            std::string text = execute_script(script);
            if (!text.empty()) {
                return text;
            }
            std::cout << "[!] Warning: PROBLEM_TEXT_SELECTOR '" << config::PROBLEM_TEXT_SELECTOR
                      << "' returned empty. Falling back to document.body.innerText." << std::endl;
        }
        return execute_script("return document.body ? document.body.innerText : '';");
    }

    // Returns the WebDriver element id for the first element matching the CSS selector.
    std::string find_element(const std::string& css_selector) {
        json body = {{"using", "css selector"}, {"value", css_selector}};
        auto resp = http::post(base_url() + "/element", body.dump());
        if (resp.status_code != 200) {
            throw std::runtime_error("Could not find element '" + css_selector +
                                      "'. Response: " + resp.body);
        }
        json parsed = json::parse(resp.body);
        const std::string key = "element-6066-11e4-a52e-4f735466cecf";
        if (parsed["value"].contains(key)) {
            return parsed["value"][key].get<std::string>();
        }
        return parsed["value"]["ELEMENT"].get<std::string>();
    }

    // Explicit Wait / Retry Loop: Repeatedly attempts to find an element until timeout, polling every 500ms.
    std::string find_element_with_timeout(const std::string& css_selector, int timeout_seconds = 10) {
        auto start = std::chrono::steady_clock::now();
        while (true) {
            try {
                return find_element(css_selector);
            } catch (...) {
                auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                    std::chrono::steady_clock::now() - start).count();
                if (elapsed >= timeout_seconds) {
                    throw std::runtime_error("Timed out after " + std::to_string(timeout_seconds) +
                                             "s waiting for element: " + css_selector);
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
        }
    }

    // Polls the test result element until the success keyword appears or timeout expires.
    bool wait_for_test_results(const std::string& result_selector,
                               const std::string& success_keyword,
                               int timeout_seconds = 45) {
        std::cout << "[*] Monitoring test execution results (up to " << timeout_seconds << "s)..." << std::endl;
        auto start = std::chrono::steady_clock::now();

        while (true) {
            try {
                std::string script =
                    "var el = document.querySelector('" + result_selector + "');"
                    "return el ? (el.innerText || el.textContent || '') : '';";
                std::string text = execute_script(script);

                if (!text.empty()) {
                    std::string lower_text = text;
                    std::string lower_kw = success_keyword;
                    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
                    std::transform(lower_kw.begin(), lower_kw.end(), lower_kw.begin(), ::tolower);

                    // Check for positive test pass
                    if (lower_text.find(lower_kw) != std::string::npos) {
                        std::cout << "[OK] Test cases PASSED! Verified keyword: '" << success_keyword << "'" << std::endl;
                        return true;
                    }

                    // Check for failure keywords
                    if (lower_text.find("fail") != std::string::npos ||
                        lower_text.find("error") != std::string::npos ||
                        lower_text.find("wrong") != std::string::npos ||
                        lower_text.find("exception") != std::string::npos) {
                        std::cerr << "[X] Test execution FAILED. Output snippet: "
                                  << text.substr(0, std::min<size_t>(text.size(), 200)) << std::endl;
                        return false;
                    }
                }
            } catch (...) {}

            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::steady_clock::now() - start).count();
            if (elapsed >= timeout_seconds) {
                std::cerr << "[!] Timed out after " << timeout_seconds
                          << "s waiting for test results." << std::endl;
                return false;
            }
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    void clear_element(const std::string& element_id) {
        http::post(element_url(element_id) + "/clear", "{}");
    }

    void send_keys(const std::string& element_id, const std::string& text) {
        json body = {{"text", text}};
        auto resp = http::post(element_url(element_id) + "/value", body.dump());
        if (resp.status_code != 200) {
            throw std::runtime_error("Failed to type into element: " + resp.body);
        }
    }

    void click(const std::string& element_id) {
        auto resp = http::post(element_url(element_id) + "/click", "{}");
        if (resp.status_code != 200) {
            throw std::runtime_error("Failed to click element: " + resp.body);
        }
    }

private:
    std::string session_id_;

    std::string base_url() const {
        return config::CHROMEDRIVER_URL + "/session/" + session_id_;
    }

    std::string element_url(const std::string& element_id) const {
        return base_url() + "/element/" + element_id;
    }
};

// Pastes generated code into the active session's code editor.
inline void paste_code_to_website(Session& session, const std::string& code) {
    // Attempt 1: Try intelligent JavaScript injection (Ace Editor / Monaco / DOM)
    bool injected = false;
    try {
        injected = session.set_editor_content(config::CODE_INPUT_SELECTOR, code);
    } catch (...) {
        injected = false;
    }

    if (injected) {
        std::cout << "[OK] Code populated via smart editor injection (Ace Editor / Monaco / DOM)." << std::endl;
    } else {
        // Attempt 2: Fallback to standard WebDriver find_element + send_keys
        std::string field_id = session.find_element_with_timeout(config::CODE_INPUT_SELECTOR, 15);
        session.clear_element(field_id);
        session.send_keys(field_id, code);
        std::cout << "[OK] Code typed into editor (" << config::CODE_INPUT_SELECTOR << ")." << std::endl;
    }
}

// Opens the URL, navigates, and pastes code (used for Screenshot mode).
inline void paste_code_to_website(const std::string& url, const std::string& code) {
    Session session;
    session.navigate(url);
    if (config::PAGE_LOAD_WAIT_SECONDS > 0) {
        std::this_thread::sleep_for(std::chrono::seconds(config::PAGE_LOAD_WAIT_SECONDS));
    }
    paste_code_to_website(session, code);
}

} // namespace webdriver
