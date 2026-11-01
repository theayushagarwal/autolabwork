# Autonomous Student Productivity & Automation Suite

A high-performance dual-engine automation suite built for academic workflows at VIT Vellore:

1. **⚡ VIT FFCS High-Speed Registration Engine (`fast_ffcs_register.py`)**: Sub-second course registration bot with zero-clash blueprint enforcement, SweetAlert handling, and instant slot-synchronized fallback pivoting.
2. **🧠 Autonomous Assessment & Coding Engine (`solve.py` / `main.cpp`)**: Browser automation and self-healing coding assistant powered by **Groq High-Speed Inference** and **Selenium CDP (Chrome DevTools Protocol)**.

---

## ⚡ Module 1: VIT FFCS High-Speed Registration Engine

Designed to eliminate registration lag and seat-sniping bottlenecks during **VIT Fully Flexible Credit System (FFCS)** drops.

```
       [ 🚀 LAUNCH_FFCS_BOOM.bat ]
                   │
                   ▼
       [ Connects to Chrome (Port 9222) ]
                   │
                   ▼
       [ User Logs in & Hits ENTER ]
                   │
      ┌────────────┴──────────────────────┐
      ▼                                   ▼
 [ Priority 1: Compulsory UCC ]      [ Priority 2: PCC & UCC ]
  • BAENG101 (Tech English)           • BAMAT205 (Discrete Math)
  • BAHUM101 (India Studies)          • BACSE103 (Comp Struct)
  (Unlocks PCC Registration)          • BACSE105 (DSA)
                                      • BACSE104 (SOOP)
                                      • BAPHY105 (Physics)
                   │
                   ▼
 [ 100% Zero-Clash Timetable & Sub-Second Execution ]
```

### 🎯 Key Engineering Features

* **Sub-Second DOM Injection**:
  Bypasses sluggish UI click events by dispatching direct JavaScript DOM queries and native CDP radio selections, dropping selection time from seconds to milliseconds.
* **Compulsory-First Priority Sequencing**:
  VTOP strictly locks Programme Core (PCC) until compulsory University Core Courses (UCC) are registered. The bot registers `BAENG101` and `BAHUM101` first, instantly unlocking the rest of the course catalog.
* **Synchronized Slot-Matched Fallback Architecture**:
  Every primary professor (Tier 1 / Plan A) is mapped to secondary (Tier 2 / Plan B) and emergency (Tier 3 / Plan C) professors locked to the **exact same theory and lab slots**. If a section fills up, the bot falls back in 10ms without changing your weekly timetable.
* **VTOP CourseOption (`RGR`) Auto-Assertion**:
  VTOP resets radio states on theory selection. The bot re-asserts `CourseOption = 'RGR'` immediately prior to dispatching the register button.
* **SweetAlert Dialog & Modal Dismantling**:
  Intercepts VTOP SweetAlert modals, closes backdrops, forcefully clears `.sweet-overlay`, and filters out hidden DOM template strings like `<div class="sa-error-container">Not valid!</div>` to prevent false failure reports.
* **Native Email OTP Prompting**:
  Monitors for VTOP Email OTP triggers, immediately alerts the user with an audible prompt in the terminal, and injects the 5-character OTP without page reloads.

---

### 📅 Verified Master Blueprint (Zero Clashes)

| Priority | Course Code | Course Title | Cat | Plan A Faculty | Theory Slot (Venue) | Lab Slot (Venue) | Synchronized Backups (Same Slots) |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **1** | **BAENG101** | Technical English | UCC | **Dr. SARASWATHY S** | `B2+TB2` (TT404) | `L21+L22` (TT306) | Dr. Denish Raja Durai K, Senthil Babu M K |
| **2** | **BAHUM101** | India Studies | UCC | **Dr. ADIL AHMAD SHAH** | `NIL` (Online) | *None* | Any Online Faculty |
| **3** | **BAMAT205** | Discrete Mathematics | PCC | **Dr. MONICA C** | `A2+TA2+TAA2` (PRP111) | *None* | Dr. Reenu Rani, Dr. Tabinda Nahid, Dr. Parthiban A |
| **4** | **BACSE103** | Computation Structures | PCC | **Dr. PRABHU R** | `C2+TC2` (PRP122) | `L9+L10` (PRP117) | Dr. Arun Dev Dhar Dwivedi, Dr. Vikas Vijayvargiya |
| **5** | **BACSE105** | Data Structures & Algorithms | PCC | **Dr. SUBRAMANYAM REDDY A** | `E2+TE2` (PRPG23) | `L45+L46` (PRP135) | Dr. Sharief Basha S, Dr. Saravanarajan M C |
| **6** | **BACSE104** | SOOP | PCC | **Dr. ANURADHA G** | `D2` (PRPG03) | `L3+L4 & L19+L20` (PRP118a) | Dr. Vinila Jinny, Dr. Gunasekar M |
| **7** | **BAPHY105** | Engineering Physics | UCC | **Dr. KANHAIYA LAL PANDEY** | `G2+TG2` (PRP109) | `L13+L14` (PRPG17) | Dr. Samuel P, Dr. Sangem Rajesh |

---

### 🚀 Running the FFCS Engine

#### Method 1: Instant 1-Click Launch (Recommended)
Double-click **`LAUNCH_FFCS_BOOM.bat`**:
1. Chrome launches automatically on remote debugging port `9222`.
2. Log into VTOP and solve your Captcha.
3. Switch back to the terminal and press **`[ENTER]`** when your registration window opens.

#### Method 2: Command-Line Flags
```bash
# Interactive registration prompt mode (default)
python fast_ffcs_register.py

# Unattended instant registration of all target courses
python fast_ffcs_register.py --all

# View currently registered courses & credit summary
python fast_ffcs_register.py --view

# Run mock seat registration test
python test_mock_run.py
```

---

## 🧠 Module 2: Autonomous Assessment & Coding Engine (`solve.py`)

A fully autonomous, zero-compilation browser automation and problem-solving engine powered by **Groq High-Speed Inference** and **Selenium CDP (Chrome DevTools Protocol)**. 

Handles both **Complex Coding Challenges** (with iterative self-healing) and **Multiple Choice Questions (MCQs)** (with deterministic local sandboxing and dual-model consensus).

---

### ⚡ Core Architecture & Highlights

#### 1. 🧠 Triple-Pillar MCQ Solving Engine
* **Pillar 1 — Deterministic Python Sandbox**:
  * Automatically isolates executable code snippets from question statements.
  * Filters editor gutter line numbers and invisible zero-width characters.
  * Executes the code locally in an isolated sub-process with a 3.0s timeout guard.
  * Mathematically matches `stdout` against option texts for **100% certainty** (zero LLM hallucination).
* **Pillar 2 — Dual-Model Cross-Validation Consensus**:
  * Conceptual and theoretical questions are queried concurrently across two independent SOTA models on Groq:
    1. **Primary Model**: `openai/gpt-oss-120b` (Deep multi-step reasoning).
    2. **Secondary Model**: `qwen/qwen3.8-27b` (High-speed cross-validation).
  * Requires **100% consensus** before committing answers.
* **Pillar 3 — Triple-Layer Verification**:
  * **Layer 1 (Native DOM)**: Verifies radio input `checked === true`.
  * **Layer 2 (Visual CSS)**: Verifies active styling classes (e.g. `!t-bg-primary`, `!t-text-white`, `selected`).
  * **Layer 3 (Palette State)**: Confirms the sidebar question palette updates to the answered state.

#### 2. 🔁 Autonomous Coding & Self-Healing Feedback Loop
* **Direct Monaco & Ace Editor Injection**:
  * Injects clean code directly via `window.monaco.editor.getModels()[0].setValue()` or Ace Editor APIs, eliminating slow typing lag and indentation bugs.
* **Mathematical Test Case Ratio Parsing**:
  * Strictly parses exact fraction patterns (`r"(\d+)\s*/\s*(\d+)"`) to ensure all test cases pass ($passed == total > 0$), preventing false positives from generic platform result banners.
* **Automated Self-Healing Loop**:
  * If a compiler error, runtime exception, or test case mismatch occurs, the engine extracts the error logs and diffs, feeds them back to Groq, and iteratively refines the code until all tests pass.

#### 3. 🛡️ Advanced Browser Fidelity & Stealth
* **CDP Native Input Dispatching (`isTrusted: true`)**:
  * Uses Chrome DevTools Protocol (`Input.dispatchMouseEvent`) to dispatch low-level mouse events directly at element screen coordinates.
  * Events are processed by the browser compositor with `event.isTrusted === true`, matching physical hardware clicks.
* **Deep Prototype Cleanliness**:
  * Injects a stealth layer on every new document (`Page.addScriptToEvaluateOnNewDocument`) that cleanly removes `webdriver` from `Navigator.prototype`, matching standard unmanaged Chromium instances.
* **Dynamic Reading-Speed Pacing**:
  * Replaces flat random timers with cognitive load modeling based on text length (~220 wpm) and code syntax density (~50 wpm), accompanied by log-normal human variance.
* **Live Interactive Terminal Controls**:
  * `[ENTER]` or `[S]` -> Skip remaining wait and advance immediately.
  * `[C]` -> Set custom timer on the fly (e.g., `0`, `15s`, `2m`).
  * Digits `0-9` -> Instant timer adjustment.
* **Absolute Safety Guard (`isForbidden`)**:
  * Strict regex protection guarantees the engine never triggers "Submit Test" buttons unintentionally.

---

### 🚀 Running the Assessment Engine

#### Quick Start (1-Click Windows)
Double-click **`solve.bat`**:
* Verifies Python environment and installs missing packages (`selenium`, `requests`).
* Reads or prompts for your Groq API key (saved securely in `.env`).
* Launches Chrome on port 9222 and attaches automatically.

#### Manual Execution
```bash
# Set your API key
export GROQ_API_KEY="your_groq_api_key_here"  # Linux / macOS
$env:GROQ_API_KEY="your_groq_api_key_here"     # Windows PowerShell

# Start Chrome with remote debugging
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"

# Run assessment solver
python solve.py

# Instant Mode (skips human reading delays for rapid local testing)
python solve.py instant
```

---

## 📂 Project Structure

```
autolabwork/
├── fast_ffcs_register.py       # Production high-speed VTOP FFCS registration engine
├── LAUNCH_FFCS_BOOM.bat        # 1-Click launcher for instant FFCS registration
├── run_ffcs_bot.bat            # Interactive menu launcher for FFCS operations
├── vtop.bat                    # Isolated Chrome debugging session launcher
├── test_mock_run.py            # Automated mock registration test runner
├── RUN_MOCK_TEST.bat           # 1-Click launcher for mock testing
├── verify_blueprint_on_vtop.py # Blueprint audit and live slot verification tool
│
├── solve.py                    # Autonomous assessment engine (MCQ + Coding pipelines)
├── solve.bat                   # 1-Click launcher for assessment engine
├── main.cpp                    # High-performance C++ solver core
├── ai_solver.hpp               # C++ AI client interface
├── webdriver_client.hpp        # C++ Chrome DevTools Protocol client
├── config.hpp                  # C++ configuration loader
│
├── .gitignore                  # Production Git ignore rules (profiles, logs, secrets)
├── .env.example                # Template for required environment keys
└── README.md                   # Comprehensive project documentation
```

---

## 📋 Requirements

* **Python 3.10+**
* **Google Chrome** (standard installation)
* Required Python dependencies:
  ```bash
  pip install selenium requests
  ```

---

## 🔒 Security & Privacy Notice

* **Environment Secrets**: Never commit `.env` or API credentials to public repositories. All sensitive files are blocked via `.gitignore`.
* **Responsible Usage**: Use these tools responsibly and in compliance with educational guidelines, university codes of conduct, and platform terms of service.
