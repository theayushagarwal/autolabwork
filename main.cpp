// AutoCode — Hackathon & Contest Automation Tool (C++)
// Automated pipeline: Problem extraction -> AI Solve -> Paste -> Compile & Run -> Test verification ->
// Randomized delay (4-6 mins) -> Submit -> Advance to next question.
// Guided login and manual MyLabs navigation with ENTER triggers.

#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include "config.hpp"
#include "cache_manager.hpp"
#include "ai_solver.hpp"
#include "gemini_client.hpp"
#include "webdriver_client.hpp"

void process_question(webdriver::Session& session, int question_num, const std::string& current_url) {
    std::cout << "\n=========================================================\n"
              << "  [Question #" << question_num << "] Reading Screen & Processing...\n"
              << "=========================================================" << std::endl;

    // Switch focus to latest tab (handles cases where Examly opens questions in a new tab)
    session.switch_to_latest_tab();

    if (config::PAGE_LOAD_WAIT_SECONDS > 0 && current_url != "current") {
        std::cout << "[*] Waiting " << config::PAGE_LOAD_WAIT_SECONDS
                  << "s for question to render..." << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(config::PAGE_LOAD_WAIT_SECONDS));
    }

    std::cout << "[*] Extracting problem statement from active screen..." << std::endl;
    std::string problem_text = session.extract_problem_text();

    if (problem_text.empty()) {
        throw std::runtime_error("Extracted problem text was empty! Make sure the question page is fully visible on Chrome.");
    }

    std::cout << "[OK] Extracted " << problem_text.size() << " characters from problem page." << std::endl;

    // Check local cache first
    std::string code = cache::get(problem_text);
    if (!code.empty()) {
        std::cout << "\n[CACHE HIT] Loaded solution from local cache (0 API calls used)!" << std::endl;
    } else {
        std::cout << "[*] Querying AI for basic Python solution (map, list, dict)..." << std::endl;
        auto start_time = std::chrono::steady_clock::now();
        code = ai::solve_problem_text(problem_text);
        auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - start_time).count();

        std::cout << "[OK] Solution generated in " << elapsed_ms << " ms!" << std::endl;
        cache::put(problem_text, code, current_url);
    }

    std::cout << "\n----- Generated Code -----\n"
              << code
              << "\n---------------------------\n" << std::endl;

    // Step 1: Inject code into editor
    std::cout << "[*] Injecting code into Ace Editor..." << std::endl;
    webdriver::paste_code_to_website(session, code);

    // Step 2: Compile & Run (if RUN_BUTTON_SELECTOR is provided)
    if (!config::RUN_BUTTON_SELECTOR.empty()) {
        std::cout << "[*] Triggering 'Compile & Run' button (" << config::RUN_BUTTON_SELECTOR << ")..." << std::endl;
        std::string run_btn = session.find_element_with_timeout(config::RUN_BUTTON_SELECTOR, 10);
        session.click(run_btn);

        // Verify test cases if selector is configured
        if (!config::TEST_RESULT_SELECTOR.empty()) {
            bool passed = session.wait_for_test_results(
                config::TEST_RESULT_SELECTOR,
                config::TEST_SUCCESS_KEYWORD,
                config::TEST_POLL_TIMEOUT_SECONDS
            );

            if (!passed) {
                std::cerr << "[!] Safety Stop: Test cases did not pass. Skipping automatic submission." << std::endl;
                return;
            }
        } else {
            std::cout << "[*] Waiting 5s for compilation..." << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }

    // Step 3: Randomized Delay (4 to 6 minutes by default)
    int delay = webdriver::get_random_delay_seconds(
        config::MIN_SUBMIT_DELAY_SECONDS,
        config::MAX_SUBMIT_DELAY_SECONDS
    );
    webdriver::sleep_with_countdown(delay);

    // Step 4: Submit Code
    if (!config::SUBMIT_BUTTON_SELECTOR.empty()) {
        std::cout << "[*] Submitting code (" << config::SUBMIT_BUTTON_SELECTOR << ")..." << std::endl;
        std::string submit_btn = session.find_element_with_timeout(config::SUBMIT_BUTTON_SELECTOR, 10);
        session.click(submit_btn);
        std::cout << "[OK] Code submitted successfully!" << std::endl;
    } else {
        std::cout << "[*] SUBMIT_BUTTON_SELECTOR not configured. Skipping submit click." << std::endl;
    }
}

int main(int argc, char* argv[]) {
    try {
        if (argc <= 2) {
            std::string url = (argc == 2) ? argv[1] : "";

            webdriver::Session session;

            if (url == "current") {
                std::cout << "[*] Active Tab Mode: Connecting directly to currently open tab..." << std::endl;
                session.navigate("current");
            } else if (!url.empty()) {
                std::cout << "[*] Navigating to specified URL: " << url << std::endl;
                session.navigate(url);
            } else {
                // =============================================================
                // Guided Login & Manual MyLabs Navigation Flow
                // =============================================================
                std::cout << "\n======================================================================\n"
                          << "  VIT Examly Guided Login\n"
                          << "======================================================================\n"
                          << "[*] Opening Login Page: " << config::LOGIN_URL << "\n"
                          << "[*] If you are not already logged in, enter your password/credentials.\n"
                          << "\n>>> Once logged in, press [ENTER] in this terminal to navigate to MyLabs... <<<\n"
                          << "======================================================================\n"
                          << std::flush;

                session.navigate(config::LOGIN_URL);

                // Wait for user to press ENTER after logging in
                std::string input;
                std::getline(std::cin, input);

                // Automatically navigate to the MyLabs URL
                std::cout << "\n[*] Navigating to MyLabs URL: " << config::LABS_URL << std::endl;
                session.navigate(config::LABS_URL);

                std::cout << "\n======================================================================\n"
                          << "  MyLabs Page Loaded!\n"
                          << "======================================================================\n"
                          << "[*] Chrome is now at your MyLabs dashboard:\n"
                          << "    " << config::LABS_URL << "\n"
                          << "[*] You can manually browse, select, and open whatever problem you want!\n"
                          << "[*] Take your time — the script is paused and waiting for you.\n"
                          << "\n>>> When you are on the question page, press [ENTER] in this terminal to start solving! <<<\n"
                          << "======================================================================\n"
                          << std::flush;

                // Wait for user to manually browse and open the question
                std::getline(std::cin, input);
                url = "current";
            }

            // Interactive Question Solving Loop
            int question_num = 1;
            while (true) {
                process_question(session, question_num, url);

                std::cout << "\n======================================================================\n"
                          << "  [✓] Question #" << question_num << " Finished!\n"
                          << "======================================================================\n"
                          << "[*] In Chrome, you can now review or manually open your next question.\n"
                          << "\n>>> Press [ENTER] to read & solve the next question (or type 'q' then ENTER to exit): <<<\n"
                          << "======================================================================\n"
                          << std::flush;

                std::string next_input;
                std::getline(std::cin, next_input);

                if (next_input == "q" || next_input == "Q" || next_input == "quit") {
                    std::cout << "[*] Exiting on user request. Chrome session preserved." << std::endl;
                    break;
                }

                question_num++;
            }

            std::cout << "[*] All done. Chrome session preserved. You remain logged in." << std::endl;

        } else {
            // Screenshot Mode: ./gemini_autocode <image_path> <url>
            std::string image_path = argv[1];
            std::string url = argv[2];

            std::cout << "[*] Running in Screenshot Mode..." << std::endl;

            std::string code = cache::get(image_path);
            if (!code.empty()) {
                std::cout << "\n[CACHE HIT] Loaded solution from local cache (0 API calls used)!" << std::endl;
            } else {
                std::cout << "[*] Reading question from image (" << image_path << ") and solving via Gemini Vision..."
                          << std::endl;
                code = gemini::solve_from_image(image_path);
                cache::put(image_path, code, image_path);
            }

            std::cout << "\n----- Generated Code -----\n"
                      << code
                      << "\n---------------------------\n" << std::endl;

            std::cout << "[*] Opening website and pasting code..." << std::endl;
            webdriver::paste_code_to_website(url, code);
        }

    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
