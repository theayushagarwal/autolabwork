# Autonomous Assessment & Coding Engine (`solve.py`)

A fully autonomous, zero-compilation browser automation and problem-solving engine powered by **Groq High-Speed Inference** and **Selenium CDP (Chrome DevTools Protocol)**. 

Built to handle both **Complex Coding Challenges** (with iterative self-healing) and **Multiple Choice Questions (MCQs)** (with deterministic local sandboxing and dual-model consensus).

---

## ⚡ Core Architecture & Highlights

### 1. 🧠 Triple-Pillar MCQ Solving Engine
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

### 2. 🔁 Autonomous Coding & Self-Healing Feedback Loop
* **Direct Monaco & Ace Editor Injection**:
  * Injects clean code directly via `window.monaco.editor.getModels()[0].setValue()` or Ace Editor APIs, eliminating slow typing lag and indentation bugs.
* **Mathematical Test Case Ratio Parsing**:
  * Strictly parses exact fraction patterns (`r"(\d+)\s*/\s*(\d+)"`) to ensure all test cases pass ($passed == total > 0$), preventing false positives from generic platform result banners.
* **Automated Self-Healing Loop**:
  * If a compiler error, runtime exception, or test case mismatch occurs, the engine extracts the error logs and diffs, feeds them back to Groq, and iteratively refines the code until all tests pass.

### 3. 🛡️ Advanced Browser Fidelity & Stealth
* **CDP Native Input Dispatching (`isTrusted: true`)**:
  * Uses Chrome DevTools Protocol (`Input.dispatchMouseEvent`) to dispatch low-level mouse events directly at element screen coordinates.
  * Events are processed by the browser compositor with `event.isTrusted === true`, matching physical hardware clicks.
* **Deep Prototype Cleanliness**:
  * Injects a stealth layer on every new document (`Page.addScriptToEvaluateOnNewDocument`) that cleanly removes `webdriver` from `Navigator.prototype`, matching standard unmanaged Chromium instances.
* **Dynamic Reading-Speed Pacing**:
  * Replaces flat random timers with cognitive load modeling based on text length (~220 wpm) and code syntax density (~50 wpm), accompanied by log-normal human variance.
* **Live Interactive Terminal Controls**:
  * Non-blocking terminal listener while waiting:
    * `[ENTER]` or `[S]` -> Skip remaining wait and advance immediately.
    * `[C]` -> Set custom timer on the fly (e.g., `0`, `15s`, `2m`).
    * Digits `0-9` -> Instant timer adjustment.
* **Absolute Safety Guard (`isForbidden`)**:
  * Strict regex protection guarantees the engine never triggers "Submit Test" buttons unintentionally.

---

## 📋 Requirements

* **Python 3.10+**
* **Google Chrome**
* Required Python packages:
  ```bash
  pip install selenium requests
  ```

---

## 🚀 Quick Start Guide

### ⚡ The Easiest Way (1-Click on Windows)
Just double-click **`solve.bat`**!
* It automatically checks for Python and installs missing dependencies (`selenium`, `requests`).
* If it's your first run, it asks for your free Groq key once and saves it to `.env`.
* It launches Chrome in port 9222 stealth mode and connects automatically.

---

### Manual Setup (All Platforms)

#### Step 1: Set Your API Key
Get a free API key from [console.groq.com/keys](https://console.groq.com/keys):

On Windows (Command Prompt):
```cmd
set GROQ_API_KEY=your_groq_api_key_here
```
On Windows (PowerShell):
```powershell
$env:GROQ_API_KEY="your_groq_api_key_here"
```
On Linux / macOS:
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

#### Step 2: Start Chrome with Remote Debugging
Close all existing Chrome windows, then launch Chrome with debugging enabled:

On Windows:
```cmd
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
```
*(Or simply let `solve.py` launch Chrome for you on first run!)*

#### Step 3: Run the Engine
Navigate to your test in Chrome, then run:

```bash
python solve.py
```

* **Instant Mode** (skips all human wait delays for rapid local testing):
  ```bash
  python solve.py instant
  ```

---

## 📂 Project Structure

```
files (5)/
├── solve.py               # Main autonomous engine (MCQ + Coding pipelines)
├── execution.log          # Live mirrored execution log for external monitoring
├── solutions_cache.json   # Local solution cache to avoid re-querying models
├── last_solution.py       # Temporary storage of the most recent generated code
├── README.md              # Project documentation and architectural overview
└── scratch/               # Unit tests and DOM inspection scripts
    ├── test_mcq_robustness.py     # Sandbox & consensus test suite
    ├── test_upgrades.py           # Verification of CDP input & pacing model
    └── test_realistic_pacing.py   # Complexity-based reading rate verification
```

---

## ⚙️ Configuration & Customization

Key settings can be adjusted at the top of [`solve.py`](solve.py):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Primary deep-reasoning model |
| `GROQ_SECONDARY_MODEL` | `qwen/qwen3.8-27b` | Secondary consensus model |
| `MIN_MCQ_DELAY_SECONDS` | `35` | Minimum human pacing floor for MCQs |
| `MAX_MCQ_DELAY_SECONDS` | `75` | Maximum human pacing ceiling for MCQs |
| `MIN_CODING_DELAY_SECONDS` | `120` | Minimum pacing floor for coding problems |
| `MAX_CODING_DELAY_SECONDS` | `240` | Maximum pacing ceiling for coding problems |
| `DEBUGGER_PORT` | `9222` | Chrome remote debugging port |

---

## 🔒 Security & Privacy Notice
* Keep your API keys in environment variables; do not commit secrets or tokens to public repositories.
* Use this tool responsibly and in accordance with applicable terms of service and educational platform policies.
