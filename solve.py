#!/usr/bin/env python3
"""
AutoCode — Hackathon & Contest Automation (Python Engine)
Features:
- Groq high-speed API (openai/gpt-oss-120b)
- Basic student-level Python code generation (map, list, dict)
- Zero-API solution caching (solutions_cache.json & last_solution.py)
- Smart button detection: clicks "Compile & Run", "Submit Code", "Next" directly by label
- Automatic test result verification (detects pass/fail)
- Realistic 2-Stage Human Pacing Workflow:
  * Stage 1: Simulates coding/typing time (~3 to 4 min) before 'Compile & Run'
  * Automatic 'Compile & Run' + full test verification
  * Stage 2: Simulates review time (~1 min) before 'Submit Code'
  * Live Terminal Controls: Press [ENTER] or [S] at any time to skip wait immediately,
    or press [C] to customize timer.
- Stale SingletonLock purging to eliminate crash loops
- DevTools port 9222 health probing before attaching
- Chrome DevTools Protocol (CDP) Page.addScriptToEvaluateOnNewDocument stealth injection
- Ace Editor direct DOM/instance injection with Angular change events
- Interactive guided login, manual MyLabs browsing, and ENTER triggers
"""

import os
import sys
import subprocess
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class TeeLogger:
    def __init__(self, filename="execution.log"):
        self.terminal = sys.stdout
        try:
            self.log = open(filename, "a", encoding="utf-8", buffering=1)
        except Exception:
            self.log = None

    def write(self, message):
        self.terminal.write(message)
        if self.log:
            try:
                self.log.write(message)
                self.log.flush()
            except Exception:
                pass

    def flush(self):
        self.terminal.flush()
        if self.log:
            try:
                self.log.flush()
            except Exception:
                pass

sys.stdout = TeeLogger("execution.log")
import time
import json
import random
import hashlib
import re
import urllib.request
from pathlib import Path

# Keyboard listener on Windows
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

# =============================================================================
# CONFIGURATION & ENVIRONMENT LOADING
# =============================================================================
def _load_local_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        except Exception:
            pass

_load_local_env()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def ensure_groq_api_key() -> str:
    """Ensures GROQ_API_KEY is available. Prompts interactively and saves to .env if missing."""
    global GROQ_API_KEY
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
        print("\n" + "=" * 65)
        print("  [!] GROQ_API_KEY was not found in environment or .env!")
        print("=================================================================")
        print("  Get a free key in 30 seconds at: https://console.groq.com/keys")
        print("=================================================================")
        try:
            key_input = input("Paste your Groq API key here (starts with gsk_): ").strip().strip("'\"")
        except Exception:
            key_input = ""
        if key_input:
            GROQ_API_KEY = key_input
            os.environ["GROQ_API_KEY"] = key_input
            try:
                env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(f"GROQ_API_KEY={key_input}\n")
                print(f"[OK] Automatically saved your key to {env_file} for future runs!\n")
            except Exception:
                pass
        else:
            raise RuntimeError("GROQ_API_KEY is required to solve questions!")
    return GROQ_API_KEY

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_SECONDARY_MODEL = "qwen/qwen3.8-27b"

LOGIN_URL = "https://vitvellore312.examly.io/login"
LABS_URL = "https://vitvellore312.examly.io/mycourses/details?id=e0d46aa1-e455-412f-b9b4-0a8c84889cc2&type=mylabs"

# =============================================================================
# ACCESS CONTROL & USER AUTHORIZATION (EMAIL WHITELIST)
# =============================================================================
# Whitelist of authorized email addresses permitted to run this engine.
# Only accounts matching this list (case-insensitive) can use the solver.
# You can add authorized student emails or Gmail IDs here:
ALLOWED_EMAILS = [
    "ayush.agarwal2026a@vitstudent.ac.in",
    # Add other authorized emails here, e.g.:
    # "friend@gmail.com",
    # "vartika@vitstudent.ac.in",
]

# Support adding emails via .env (comma-separated: ALLOWED_EMAILS=a@b.com,c@d.com)
_env_allowed = os.getenv("ALLOWED_EMAILS", "")
if _env_allowed:
    for _em in _env_allowed.split(","):
        _em_clean = _em.strip().lower()
        if _em_clean and _em_clean not in [x.lower() for x in ALLOWED_EMAILS]:
            ALLOWED_EMAILS.append(_em_clean)

def get_current_user_email(driver) -> str:
    """
    Extracts user email from Examly session:
    1. localStorage 'token' JSON (.email)
    2. localStorage 'formData' JSON (.email)
    3. localStorage 'studentData' JSON (.email)
    4. DOM login email input fields (value)
    """
    script = """
    try {
        const token = JSON.parse(localStorage.getItem('token') || '{}');
        if (token && token.email && typeof token.email === 'string') return token.email.toLowerCase().trim();
    } catch(e) {}
    try {
        const formData = JSON.parse(localStorage.getItem('formData') || '{}');
        if (formData && formData.email && typeof formData.email === 'string') return formData.email.toLowerCase().trim();
    } catch(e) {}
    try {
        const student = JSON.parse(localStorage.getItem('studentData') || '{}');
        if (student && student.email && typeof student.email === 'string') return student.email.toLowerCase().trim();
    } catch(e) {}
    try {
        const emailInput = document.querySelector('input[type="email"], input[name="email"], input[id*="email"]');
        if (emailInput && emailInput.value && emailInput.value.includes('@')) {
            return emailInput.value.toLowerCase().trim();
        }
    } catch(e) {}
    return '';
    """
    try:
        email = driver.execute_script(script)
        if email and isinstance(email, str) and "@" in email:
            return email.strip().lower()
    except Exception:
        pass
    return ""

def verify_user_authorization(driver, stage_name: str = "", force_check: bool = False) -> bool:
    """
    Verifies that the logged-in or entered email is permitted in ALLOWED_EMAILS.
    If unauthorized email is found, prints ACCESS DENIED banner and immediately exits.
    Returns True if user is verified and authorized.
    """
    normalized_allowed = [e.strip().lower() for e in ALLOWED_EMAILS if e.strip()]
    if not normalized_allowed:
        return True

    email = get_current_user_email(driver)
    if email:
        if email not in normalized_allowed:
            print("\n" + "=" * 70)
            print("  [ACCESS DENIED] UNAUTHORIZED ACCOUNT DETECTED!")
            print("=" * 70)
            print(f"  Detected Account : {email}")
            print(f"  Current Stage    : {stage_name or 'Authorization Gate'}")
            print("  Access Status    : BLOCKED — NOT ON AUTHORIZED WHITELIST")
            print("")
            print("  This automation tool is strictly restricted to licensed accounts.")
            print("  Execution has been halted to prevent unauthorized usage.")
            print("  Please contact the administrator to request access.")
            print("=" * 70 + "\n")
            try:
                driver.quit()
            except Exception:
                pass
            sys.exit(1)
        else:
            if stage_name:
                print(f"[AUTH OK] Verified authorized account ({email}) at {stage_name}.")
            else:
                print(f"[AUTH OK] Verified authorized account: {email}")
            return True
    elif force_check:
        print("\n" + "=" * 70)
        print("  [ACCESS ERROR] No Authenticated Account Found!")
        print("=" * 70)
        print("  Could not detect an active Examly login session or entered email.")
        print("  Please log into Examly with an authorized account first.")
        print("=" * 70 + "\n")
        try:
            driver.quit()
        except Exception:
            pass
        sys.exit(1)

    return False

def handle_guided_login(driver):
    """
    Guides the user through login on Examly.
    Actively checks for entered email and denies access immediately if unauthorized.
    Proceeds automatically once login completes with an authorized account.
    """
    print("\n======================================================================")
    print("  VIT Examly Guided Login & Account Verification")
    print("======================================================================")
    print(f"[*] Opening Login Page: {LOGIN_URL}")
    print("[*] Enter your authorized email and credentials in Chrome.")
    print("[*] System is monitoring account authorization in real-time...")
    print("\n>>> Once logged in, press [ENTER] in this terminal (or wait for auto-detection) <<<")
    print("======================================================================")

    driver.get(LOGIN_URL)
    time.sleep(2)

    last_detected = ""
    while True:
        # 1. Non-blocking key check on Windows
        if HAS_MSVCRT and msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):
                # User pressed ENTER to signal login completion
                email = get_current_user_email(driver)
                if email:
                    verify_user_authorization(driver, stage_name="Login Submission")
                break

        # 2. Check if an email is present in input or localStorage
        email = get_current_user_email(driver)
        if email and email != last_detected:
            # Only test when email is full (matches email format) to avoid blocking during typing
            if re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
                last_detected = email
                verify_user_authorization(driver, stage_name="Login Form Entry")

        # 3. Check if user navigated away from login (login succeeded)
        curr = driver.current_url.lower()
        if "examly.io" in curr and "login" not in curr:
            print("[OK] Login completed! Verifying account credentials...")
            verify_user_authorization(driver, stage_name="Post-Login Verification", force_check=True)
            break

        # Fallback if not Windows MSVCRT
        if not HAS_MSVCRT:
            input("Press [ENTER] after entering credentials in Chrome... ")
            verify_user_authorization(driver, stage_name="Manual Login Verification")
            break

        time.sleep(0.5)

# Button candidate label lists (from Examly interface)
RUN_BUTTON_LABELS = ["Compile & Run", "Compile and Run", "Compile&Run", "Run Code", "Compile", "Run"]
SUBMIT_BUTTON_LABELS = ["Submit Code", "submit code"]
NEXT_BUTTON_LABELS = ["Next", "Next Question", "Next >", ">"]

CODE_INPUT_SELECTOR = ".ace_editor"
PROBLEM_TEXT_SELECTOR = ""      # Leave empty to extract full page via document.body.innerText

PAGE_LOAD_WAIT_SECONDS = 3

# =============================================================================
# REALISTIC 2-STAGE HUMAN TIMING SETTINGS
# =============================================================================
# Stage 1: Coding & typing simulation before Compile & Run (3 to 4 minutes)
MIN_CODING_DELAY_SECONDS = 180  # 3 minutes
MAX_CODING_DELAY_SECONDS = 240  # 4 minutes

# Stage 2: Final review simulation before Submit Code (~1 minute)
MIN_REVIEW_DELAY_SECONDS = 50   # ~50 seconds
MAX_REVIEW_DELAY_SECONDS = 75   # ~1.25 minutes

# MCQ Pacing: Realistic human reading, thinking and answering delay (40 to 70 seconds)
MIN_MCQ_DELAY_SECONDS = 40      # 40 seconds
MAX_MCQ_DELAY_SECONDS = 70      # 70 seconds

SUBMIT_DELAY_OVERRIDE = None    # Set via CLI arguments e.g. 'solve instant' or 'solve 30'

CACHE_FILE = "solutions_cache.json"
LAST_SOLUTION_FILE = "last_solution.py"
DEBUGGER_PORT = 9222

# =============================================================================
# 1. TIME PARSER & CACHE MANAGER
# =============================================================================
def parse_duration(s: str) -> int:
    """Parses user input into seconds: '0', '30', '45s', '2m', '1.5m', '3 min'."""
    s = s.strip().lower()
    if not s:
        return 0
    m_match = re.match(r"^([\d.]+)\s*(?:m|min|mins|minute|minutes)$", s)
    if m_match:
        return int(float(m_match.group(1)) * 60)
    s_match = re.match(r"^([\d.]+)\s*(?:s|sec|secs|second|seconds)?$", s)
    if s_match:
        return int(float(s_match.group(1)))
    return 0

def hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_to_cache(raw_text: str, code: str, context: str = ""):
    cache_data = load_cache()
    key = hash_text(raw_text)
    cache_data[key] = {
        "code": code,
        "context": context,
        "timestamp": int(time.time())
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=4)
    with open(LAST_SOLUTION_FILE, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[SAVED] Solution saved to {LAST_SOLUTION_FILE} and {CACHE_FILE}")

def get_from_cache(raw_text: str) -> str:
    cache_data = load_cache()
    key = hash_text(raw_text)
    if key in cache_data and "code" in cache_data[key]:
        return cache_data[key]["code"]
    return ""

# =============================================================================
# 2. GROQ AI SOLVER (Student-Level Python: map, list, dict)
# =============================================================================
def strip_markdown_fences(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        trimmed = line.strip()
        if trimmed.startswith("```"):
            continue
        out.append(line)
    return "\n".join(out).strip()

def solve_with_groq(problem_text: str, constraints: dict = None, error_context: str = "") -> str:
    ensure_groq_api_key()

    constraints = constraints or {}
    wl_items = constraints.get("whitelist", [])
    bl_items = constraints.get("blacklist", [])
    raw_constraints = constraints.get("raw_matches", [])

    system_prompt = (
        "You are an expert Python coding assistant acting as a student programmer.\n"
        "You will be given the extracted text content of a webpage containing a coding problem.\n"
        "Your task:\n"
        "1. Write the solution in clean, basic standard PYTHON 3.\n"
        "2. Coding Level & Style: Use common, straightforward student-level Python concepts: "
        "map(), list, dictionary (dict), set, simple for/while loops, and basic if-else checks.\n"
        "   - Use standard input reading patterns when required: e.g. input().strip(), int(input()), "
        "or list(map(int, input().split())).\n"
        "   - If input may contain multiple lines or uncertain number of tokens, read with sys.stdin.read().split().\n"
        "   - Avoid overly clever one-liners, obscure syntax, or complicated external libraries. "
        "The code must look natural, clear, and human-written by a beginner/intermediate programmer.\n"
        "3. Output ONLY the raw executable Python code ready to run and pass tests.\n"
        "4. WHITELIST / MANDATORY SYNTAX RULE (CRITICAL):\n"
        "   - If any Whitelist functions or syntaxes are specified (e.g. 'pow', 'math.sqrt', 'round'), "
        "YOU MUST EXPLICITLY USE THEM in your solution! (e.g. use pow(base, exp) instead of **).\n"
        "   - Never violate Blacklist restrictions.\n"
        "STRICT RULE: Do NOT include any explanations, comments, or markdown code fences (like ```python or ```). "
        "Output raw Python code only."
    )

    user_content = f"Here is the problem statement:\n\n{problem_text}"

    if wl_items or raw_constraints:
        user_content += (
            f"\n\n=========================================\n"
            f"[CRITICAL PLATFORM CONSTRAINTS DETECTED]:\n"
            f"Mandatory Whitelist Functions: {wl_items}\n"
            f"Raw Constraint Badges Found on Page:\n" + "\n".join(raw_constraints) + "\n"
            f"-> YOU MUST EXPLICITLY CALL/USE THESE FUNCTIONS IN YOUR CODE. THE PLATFORM WILL REJECT CODE WITHOUT THEM!\n"
            f"========================================="
        )

    if bl_items:
        user_content += (
            f"\n\n=========================================\n"
            f"[FORBIDDEN BLACKLIST SYNTAX]:\n"
            f"Do NOT use any of these: {bl_items}\n"
            f"========================================="
        )

    if error_context:
        user_content += (
            f"\n\n=========================================\n"
            f"[CRITICAL AUTO-FIX / SELF-HEALING DIAGNOSIS]:\n"
            f"The previous attempt FAILED compilation or test cases!\n"
            f"Detailed Diagnostic Report:\n"
            f"{error_context}\n\n"
            f"SELF-HEALING GUIDELINES:\n"
            f"1. If a Whitelist Syntax error occurred: YOU MUST USE THE REQUIRED FUNCTION (e.g., pow(), math.sqrt(), round()).\n"
            f"2. If Wrong Answer / Mismatch: Compare Expected Output vs Actual Output carefully. Fix spacing, newline, precision (e.g. %.2f), or logic bugs.\n"
            f"3. If EOFError / Input Mismatch: Use sys.stdin.read().split() or handle all test inputs cleanly.\n"
            f"4. If SyntaxError / Traceback: Fix the syntax, indentation, or type error on the specified line.\n"
            f"Write a completely revised, working Python 3 solution that satisfies all constraints and passes every test."
            f"\n========================================="
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1
    }

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AutoCode/1.0"
        },
        data=json.dumps(payload).encode("utf-8")
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"Groq returned no choices. Raw response: {data}")

    code = data["choices"][0]["message"]["content"]
    return strip_markdown_fences(code)

# =============================================================================
# 3. INDUSTRIAL-STRENGTH CHROME LAUNCHER (Persistent Profile, Locks, CDP Stealth)
# =============================================================================
def get_robust_profile_dir() -> str:
    local_app = os.getenv("LOCALAPPDATA")
    if local_app:
        profile_dir = Path(local_app) / "Google" / "Chrome" / "NeoColabProfile"
    else:
        profile_dir = Path("C:/Users/ayush/AppData/Local/Google/Chrome/NeoColabProfile")

    profile_dir.mkdir(parents=True, exist_ok=True)

    # Detect and purge orphaned crash locks
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = profile_dir / lock_name
        if lock_path.exists():
            try:
                lock_path.unlink()
                print(f"[OK] Purged stale lock file: {lock_name}")
            except Exception:
                pass

    return str(profile_dir)

def is_chrome_debug_port_healthy(port: int = 9222, timeout: float = 1.0) -> bool:
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "webSocketDebuggerUrl" in data
    except Exception:
        return False

def apply_stealth_cdp(driver):
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    // 1. Cleanly remove 'webdriver' from Navigator.prototype directly
                    try {
                        const proto = Navigator.prototype;
                        if ('webdriver' in proto) {
                            delete proto.webdriver;
                        }
                    } catch (e) {}

                    // 2. Ensure navigator.webdriver returns undefined naturally
                    try {
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                            configurable: true
                        });
                    } catch (e) {}

                    // 3. Ensure window.chrome matches standard desktop Chromium structure
                    try {
                        window.chrome = window.chrome || {
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {}
                        };
                    } catch (e) {}

                    // 4. Mock standard plugins array (real browsers have plugins)
                    try {
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                            configurable: true
                        });
                    } catch (e) {}
                """
            }
        )
        print("[OK] Injected Deep CDP Stealth Layer (Page.addScriptToEvaluateOnNewDocument).")
    except Exception as e:
        print(f"[!] CDP stealth injection note: {e}")

def cdp_click_element(driver, element_or_selector) -> bool:
    """
    Clicks an element using native CDP Input events (isTrusted: true)
    at the element's exact viewport coordinates.
    """
    try:
        if isinstance(element_or_selector, str):
            rect = driver.execute_script("""
                const el = document.querySelector(arguments[0]);
                if (!el) return null;
                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                const r = el.getBoundingClientRect();
                return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            """, element_or_selector)
        else:
            rect = driver.execute_script("""
                const el = arguments[0];
                if (!el) return null;
                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                const r = el.getBoundingClientRect();
                return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            """, element_or_selector)

        if not rect or rect.get("x") is None:
            return False

        x, y = int(rect["x"]), int(rect["y"])

        # Dispatch native mousePressed and mouseReleased with natural click duration
        driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        time.sleep(random.uniform(0.04, 0.08))
        driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        return True
    except Exception as e:
        return False

def calculate_human_pacing(question_text: str, code_snippet: str = "", min_sec: int = 35, max_sec: int = 75) -> int:
    """
    Calculates a human-modeled pacing delay based on word count,
    code complexity, and a right-skewed log-normal distribution.
    """
    text_words = len(question_text.split()) if question_text else 0
    code_words = len(code_snippet.split()) if code_snippet else 0

    # Reading speed: ~200-220 wpm for text (~3.5 words/sec), ~40-50 wpm for code (~0.8 words/sec)
    text_time = text_words / 3.5
    code_time = code_words / 0.8

    # Base thinking / verification time: 8-15 seconds
    base_time = text_time + code_time + random.uniform(8.0, 15.0)

    # Right-skewed log-normal variance
    try:
        variance_factor = random.lognormvariate(0, 0.12)
        total_time = base_time * variance_factor
    except Exception:
        total_time = base_time

    delay = int(round(max(min_sec, min(total_time, max_sec))))
    return delay

def launch_chrome() -> webdriver.Chrome:
    options = Options()

    if is_chrome_debug_port_healthy(DEBUGGER_PORT):
        print(f"[OK] Detected healthy Chrome on port {DEBUGGER_PORT}. Attaching...")
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUGGER_PORT}")
        driver = webdriver.Chrome(options=options)
    else:
        print("[*] Launching new Chrome instance with persistent profile...")
        profile_dir = get_robust_profile_dir()

        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument(f"--remote-debugging-port={DEBUGGER_PORT}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("detach", True)

        driver = webdriver.Chrome(options=options)

    apply_stealth_cdp(driver)
    print("[OK] Browser ready and connected.")
    return driver

# =============================================================================
# 4. SMART BUTTON CLICKING & ACE EDITOR INJECTION
# =============================================================================
def switch_to_latest_tab(driver):
    handles = driver.window_handles
    if len(handles) > 1:
        driver.switch_to.window(handles[-1])

def click_smart_button(driver, candidate_labels, retries: int = 4, retry_delay: float = 0.5) -> bool:
    """
    Ultra-robust button locator & clicker tailored for Examly / Angular.
    - Normalizes non-breaking spaces (\u00a0) & multi-whitespace
    - Inspects native interactive elements (button, [role="button"], a, input) first
    - If a matched text is inside a leaf span/div, traverses up to closest button parent
    - Strips 'disabled' attributes and '.disabled' CSS classes
    - Dispatches full event chain: mouseover, mousedown, mouseup, click, .click()
    - Also triggers native Selenium ActionChains / element.click() for OS-level event
    """
    if isinstance(candidate_labels, str):
        candidate_labels = [candidate_labels]

    script = """
        const targets = arguments[0];

        function norm(s) {
            if (!s) return "";
            return s.replace(/\\u00a0/g, " ").replace(/\\s+/g, " ").trim().toLowerCase();
        }

        function isForbidden(txt) {
            // NEVER click any button that terminates or submits the entire test!
            const bad = ['submit test', 'end test', 'finish test', 'terminate test'];
            return bad.some(b => txt.includes(b));
        }

        const wantsSubmitCode = targets.some(tgt => tgt.toLowerCase().includes('submit code'));
        const wantsCompile = targets.some(tgt => tgt.toLowerCase().includes('compile'));

        // 1. Check all native interactive elements: button, [role="button"], a, input
        const interactives = Array.from(document.querySelectorAll('button, [role="button"], a, input[type="button"], input[type="submit"]'));

        // Exact match on interactives
        for (const target of targets) {
            const t = norm(target);
            for (const el of interactives) {
                const txt = norm(el.innerText || el.textContent || el.value || '');
                if (isForbidden(txt)) continue;
                if (wantsSubmitCode && (!txt.includes('code') || !txt.includes('submit'))) continue;
                if (txt === t) return el;
            }
        }

        // Substring match on interactives
        for (const target of targets) {
            const t = norm(target);
            for (const el of interactives) {
                const txt = norm(el.innerText || el.textContent || el.value || '');
                if (isForbidden(txt)) continue;
                if (wantsSubmitCode && (!txt.includes('code') || !txt.includes('submit'))) continue;
                if (txt.includes(t) && txt.length < 50) return el;
            }
        }

        // Dual keyword match (e.g. contains both 'compile' and 'run')
        if (wantsCompile) {
            for (const el of interactives) {
                const txt = norm(el.innerText || el.textContent || el.value || '');
                if (isForbidden(txt)) continue;
                if (txt.includes('compile') && txt.includes('run')) return el;
            }
        }

        // 2. Check inner elements (span, div, b, strong, i, p) and climb up to parent button
        const leafElements = Array.from(document.querySelectorAll('span, div, b, strong, i, p, label'));
        for (const target of targets) {
            const t = norm(target);
            for (const el of leafElements) {
                if (el.children.length > 2) continue; // Skip large container wrappers
                const txt = norm(el.innerText || el.textContent || '');
                if (isForbidden(txt)) continue;
                if (wantsSubmitCode && (!txt.includes('code') || !txt.includes('submit'))) continue;
                if (txt === t || (txt.includes(t) && txt.length < 35)) {
                    const btn = el.closest('button, [role="button"], a, input[type="button"], input[type="submit"]');
                    if (btn) {
                        const btnTxt = norm(btn.innerText || btn.textContent || '');
                        if (isForbidden(btnTxt)) continue;
                        return btn;
                    }
                    return el;
                }
            }
        }

        // Dual keyword check on inner elements climbing up
        if (wantsCompile) {
            for (const el of leafElements) {
                if (el.children.length > 2) continue;
                const txt = norm(el.innerText || el.textContent || '');
                if (txt.includes('compile') && txt.includes('run')) {
                    const btn = el.closest('button, [role="button"], a, input[type="button"], input[type="submit"]');
                    if (btn) return btn;
                    return el;
                }
            }
        }

        // 3. Fallback: check classes or IDs containing keyword
        for (const el of interactives) {
            const cls = norm(el.className || '');
            const id = norm(el.id || '');
            if (wantsCompile && (cls.includes('compile') || id.includes('compile') || cls.includes('run') || id.includes('run'))) {
                return el;
            }
        }

        return null;
    """

    click_script = """
        const el = arguments[0];
        if (!el) return false;

        // Remove disabled states
        el.removeAttribute('disabled');
        el.disabled = false;
        el.classList.remove('disabled');

        // Bring into view
        el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });

        // Dispatch full mouse event suite
        el.focus();
        el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window }));
        el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true, cancelable: true, view: window }));
        el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, button: 0 }));
        el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, button: 0 }));
        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, button: 0 }));
        el.click();
        return true;
    """

    for attempt in range(retries):
        try:
            element = driver.execute_script(script, candidate_labels)
            if element:
                # 1. Fire synthetic event suite via JS
                driver.execute_script(click_script, element)

                # 2. Fire Selenium native ActionChains click for genuine OS-level isTrusted event
                try:
                    ActionChains(driver).move_to_element(element).click().perform()
                except Exception:
                    try:
                        element.click()
                    except Exception:
                        pass

                return True
        except Exception:
            pass

        if attempt < retries - 1:
            time.sleep(retry_delay)

    # 4. Final XPath fallback
    for label in candidate_labels:
        try:
            lower_label = label.lower()
            xpath = (
                f"//*[(self::button or self::a or @role='button') and "
                f"contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{lower_label}')]"
            )
            el = driver.find_element(By.XPATH, xpath)
            driver.execute_script(click_script, el)
            el.click()
            return True
        except Exception:
            pass

    return False

def click_button_by_text(driver, text_match: str) -> bool:
    """Wrapper for backward compatibility."""
    return click_smart_button(driver, [text_match])

def inject_code_into_editor(driver, code: str, selector: str = ".ace_editor") -> bool:
    """
    Direct Ace Editor injection with Angular change event propagation.
    Ensures that Angular marks the form dirty/valid so compile & submit buttons activate.
    """
    script = """
        const val = arguments[0];
        const sel = arguments[1] || '.ace_editor';

        // 1. Ace Editor
        const aceEl = document.querySelector(sel) || document.querySelector('.ace_editor');
        if (aceEl) {
            let editor = null;
            if (aceEl.env && aceEl.env.editor) {
                editor = aceEl.env.editor;
            } else if (window.ace && typeof window.ace.edit === 'function') {
                try { editor = window.ace.edit(aceEl); } catch(e) {}
            }

            if (editor) {
                const prior = (editor.getValue() || '').trim();
                const priorLength = prior.length;

                // 1. Explicitly clear any existing code/template/boilerplate
                if (priorLength > 0) {
                    editor.selectAll();
                    if (editor.session) {
                        editor.session.setValue('');
                    }
                    editor.setValue('', -1);
                }

                // 2. Set the new code cleanly
                editor.setValue(val, -1);
                editor.clearSelection();
                editor.focus();

                // Trigger Ace change event & reset undo history
                try {
                    if (editor.session) {
                        editor.session._emit('change');
                        if (editor.session.getUndoManager()) {
                            editor.session.getUndoManager().reset();
                        }
                    }
                } catch(e) {}

                aceEl.dispatchEvent(new Event('input', { bubbles: true }));
                aceEl.dispatchEvent(new Event('change', { bubbles: true }));

                // Unfocus active element to trigger Angular form change detection
                setTimeout(() => {
                    if (document.activeElement && document.activeElement.blur) {
                        document.activeElement.blur();
                    }
                }, 50);

                return { success: true, prior_length: priorLength, editor: "Ace" };
            }
        }

        // 2. Monaco Editor
        if (window.monaco && window.monaco.editor && window.monaco.editor.getModels().length > 0) {
            const m = window.monaco.editor.getModels()[0];
            const prior = m.getValue() || '';
            m.setValue('');
            m.setValue(val);
            return { success: true, prior_length: prior.trim().length, editor: "Monaco" };
        }

        // 3. Standard Textarea
        const el = document.querySelector(sel);
        if (el) {
            const prior = el.value || '';
            el.value = '';
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return { success: true, prior_length: prior.trim().length, editor: "Textarea" };
        }

        return { success: false };
    """
    try:
        result = driver.execute_script(script, code, selector)
        if result and isinstance(result, dict) and result.get("success"):
            prior_len = result.get("prior_length", 0)
            if prior_len > 0:
                print(f"[OK] Detected {prior_len} characters of existing code/template in editor. Wiped completely clean!")
            else:
                print("[OK] Editor was empty.")
            print("[OK] Fresh code cleanly injected into editor (Ace Editor / Angular sync).")
            return True
        elif result is True:
            print("[OK] Code populated via smart editor injection.")
            return True
    except Exception as e:
        print(f"[!] Injection note: {e}")

    # Fallback to finding element and sending keys
    try:
        from selenium.webdriver.common.keys import Keys
        el = driver.find_element(By.CSS_SELECTOR, selector)
        el.click()
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.BACKSPACE)
        el.clear()
        el.send_keys(code)
        print(f"[OK] Existing text cleared & new code typed into editor ({selector}).")
        return True
    except Exception as e:
        print(f"[X] Fallback typing failed: {e}")
        return False

def extract_problem_text(driver) -> str:
    switch_to_latest_tab(driver)
    if PROBLEM_TEXT_SELECTOR:
        script = f"var el = document.querySelector('{PROBLEM_TEXT_SELECTOR}'); return el ? el.innerText : '';"
        text = driver.execute_script(script)
        if text and len(text.strip()) > 0:
            return text.strip()
    return driver.execute_script("return document.body ? document.body.innerText : '';").strip()

def get_current_question_info(driver) -> tuple:
    """Returns (current_question_num: int, total_questions: int) from page text."""
    try:
        text = driver.execute_script("return document.body ? document.body.innerText : '';")
        m = re.search(r"Question\s*No\s*:\s*(\d+)\s*/\s*(\d+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1, 8

def click_next_button(driver) -> bool:
    """
    Clicks the 'Next' button on either MCQ or Coding questions.
    In Examly, Next is typically a div with class 'next-btn' or an element with text 'Next'.
    Prefers native CDP Input (isTrusted: true).
    """
    try:
        next_el = driver.execute_script("""
            const nextBtn = document.querySelector('.next-btn');
            if (nextBtn) return nextBtn;
            const elements = Array.from(document.querySelectorAll('button, div, span, a'));
            for (const el of elements) {
                const txt = (el.innerText || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim().toLowerCase();
                if (txt === 'next' || txt === 'next >') return el;
            }
            return null;
        """)
        if next_el and cdp_click_element(driver, next_el):
            return True
    except Exception:
        pass

    script = """
        function norm(s) {
            return (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim().toLowerCase();
        }
        // 1. Try explicit next-btn class first (Examly standard)
        const nextBtn = document.querySelector('.next-btn');
        if (nextBtn) {
            nextBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
            nextBtn.focus();
            nextBtn.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window }));
            nextBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, button: 0 }));
            nextBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, button: 0 }));
            nextBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, button: 0 }));
            nextBtn.click();
            return true;
        }
        // 2. Scan all elements with text 'Next'
        const elements = Array.from(document.querySelectorAll('button, div, span, a'));
        for (const el of elements) {
            const txt = norm(el.innerText);
            if (txt === 'next' || txt === 'next >') {
                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                el.focus();
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                el.click();
                return true;
            }
        }
        return false;
    """
    try:
        if driver.execute_script(script):
            return True
    except Exception:
        pass
    return click_smart_button(driver, NEXT_BUTTON_LABELS)

def navigate_to_question(driver, target_q_num: int) -> bool:
    """
    Directly clicks the question palette box (1, 2, 3, 4, 5, 6, 7, 8) on the left sidebar,
    or the 'Next' button if advancing to next question.
    """
    script = """
        const target = String(arguments[0]);
        // 1. Check palette boxes inside sidebar specifically
        const sidebar = document.querySelector('.test-sidebar') || document;
        const paletteLeaves = Array.from(sidebar.querySelectorAll('*')).filter(el => {
            return el.children.length === 0 && el.innerText.trim() === target;
        });
        for (const leaf of paletteLeaves) {
            const clickable = leaf.closest('[role="menuitemradio"], [aria-labelledby="each-question"], [aria-labelledby="not-attempted"], .t-cursor-pointer') || leaf;
            clickable.scrollIntoView({ behavior: 'instant', block: 'center' });
            clickable.focus();
            clickable.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window }));
            clickable.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, button: 0 }));
            clickable.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, button: 0 }));
            clickable.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, button: 0 }));
            clickable.click();
            if (clickable.parentElement) {
                clickable.parentElement.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                clickable.parentElement.click();
            }
            return true;
        }

        // 2. Generic palette check: leaf element whose text is target number
        const allLeaves = Array.from(document.querySelectorAll('div, span, button')).filter(el => el.children.length === 0 && el.innerText.trim() === target);
        for (const leaf of allLeaves) {
            const parent = leaf.closest('[class*="palette"], [class*="sidebar"], [class*="section"], .ng-star-inserted');
            if (parent) {
                leaf.scrollIntoView({ behavior: 'instant', block: 'center' });
                leaf.click();
                return true;
            }
        }
        return false;
    """
    try:
        res = driver.execute_script(script, target_q_num)
        if res:
            time.sleep(2)
            return True
    except Exception:
        pass

    # Fallback to Next button
    return click_next_button(driver)

# =============================================================================
# 5. UNIVERSAL ERROR DETECTION & CONSTRAINT EXTRACTOR
# =============================================================================
def extract_page_constraints(driver) -> dict:
    """
    Scrapes the Examly question page to detect Whitelist, Blacklist, or mandatory functions.
    Prevents errors before the first compile by feeding platform requirements directly to AI.
    """
    script = """
        const bodyText = document.body ? document.body.innerText : '';
        const results = {
            whitelist: [],
            blacklist: [],
            raw_matches: []
        };

        // 1. Text Regex Scanning for Whitelist / Blacklist
        const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        for (const line of lines) {
            if (/whitelist/i.test(line) || /blacklist/i.test(line) || /mandatory/i.test(line) || /set\\s*\\d+\\s*:/i.test(line)) {
                if (line.length < 120 && !results.raw_matches.includes(line)) {
                    results.raw_matches.push(line);
                }
            }
        }

        // 2. Specific Pill / Badge Scanner in DOM
        const badgeSelectors = 'span, div, b, strong, p, code, .badge, .tag, [class*="badge"], [class*="tag"], [class*="pill"]';
        const elements = Array.from(document.querySelectorAll(badgeSelectors));
        for (const el of elements) {
            if (el.children.length > 3) continue;
            const txt = (el.innerText || '').trim();
            if (/whitelist/i.test(txt) || /blacklist/i.test(txt) || /set\\s*\\d+\\s*:/i.test(txt)) {
                if (!results.raw_matches.includes(txt) && txt.length < 120) {
                    results.raw_matches.push(txt);
                }
            }
        }

        // 3. Extract Function Names (e.g. Set 1: pow, Set 2: math.sqrt, round)
        const combined = results.raw_matches.join(' ');
        const setMatches = Array.from(combined.matchAll(/set\\s*\\d+\\s*:\\s*([a-zA-Z0-9_.]+)/gi));
        for (const sm of setMatches) {
            const func = sm[1].trim();
            if (func && !results.whitelist.includes(func)) {
                results.whitelist.push(func);
            }
        }

        const wlTokens = combined.match(/whitelist\\s*:?\\s*([a-zA-Z0-9_.,\\s()]+)/i);
        if (wlTokens && wlTokens[1]) {
            const tokens = wlTokens[1].split(/[,;\\s]+/).map(t => t.replace(/[()]/g, '').trim()).filter(t => t.length > 1 && !/^(and|or|set|\\d+|syntax|syntaxes|in|your|code|error)$/i.test(t));
            for (const t of tokens) {
                if (!results.whitelist.includes(t)) results.whitelist.push(t);
            }
        }

        const blTokens = combined.match(/blacklist\\s*:?\\s*([a-zA-Z0-9_.,\\s()]+)/i);
        if (blTokens && blTokens[1]) {
            const tokens = blTokens[1].split(/[,;\\s]+/).map(t => t.replace(/[()]/g, '').trim()).filter(t => t.length > 1 && !/^(and|or|set|\\d+|syntax|syntaxes|in|your|code|error)$/i.test(t));
            for (const t of tokens) {
                if (!results.blacklist.includes(t)) results.blacklist.push(t);
            }
        }

        return results;
    """
    try:
        constraints = driver.execute_script(script)
        if isinstance(constraints, dict):
            return constraints
    except Exception as e:
        print(f"[!] Constraint extraction note: {e}")
    return {"whitelist": [], "blacklist": [], "raw_matches": []}

def detect_floating_alerts(driver) -> str:
    """
    High-frequency scanner that intercepts toast notifications, error popups, and alerts.
    Catches errors (such as Whitelist violation toasts) instantly (<1s) rather than timing out at 40s.
    """
    script = """
        const toastSelectors = [
            '.ant-notification-notice',
            '.ant-notification',
            '.ant-message-notice',
            '.ant-message',
            '.toast',
            '[role="alert"]',
            '.swal2-modal',
            '.swal2-popup',
            '.swal2-toast',
            '[class*="toast"]',
            '[class*="notification"]',
            '.t-text-red-500',
            '.error-message'
        ];
        const elements = Array.from(document.querySelectorAll(toastSelectors.join(',')));
        for (const el of elements) {
            if (!el || !el.innerText) continue;
            const txt = el.innerText.trim();
            if (txt.length === 0) continue;
            
            // Ensure visible in layout
            try {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
            } catch(e) {}
            
            const lower = txt.toLowerCase();
            const isAlertError = lower.includes('include the whitelist') ||
                                 lower.includes('whitelist error') ||
                                 lower.includes('failed whitelist') ||
                                 lower.includes('blacklist') ||
                                 lower.includes('compilation error') ||
                                 lower.includes('syntaxerror') ||
                                 lower.includes('runtime error') ||
                                 lower.includes('wrong answer') ||
                                 lower.includes('time limit exceeded') ||
                                 (lower.includes('error') && !lower.includes('0 error')) ||
                                 lower.includes('submission failed') ||
                                 lower.includes('timed out');
            if (isAlertError) {
                return txt;
            }
        }
        return '';
    """
    try:
        alert = driver.execute_script(script)
        if alert and len(alert.strip()) > 0:
            return alert.strip()
    except Exception:
        pass
    return ""

def wait_for_test_results(driver, timeout: int = 40) -> tuple:
    """
    Monitors page output to verify if the code compiled and passed test cases.
    Scrapes dedicated compiler/result output panes.
    Parses testcase fractions (X/Y) strictly:
      - X < Y (e.g. 0/2, 1/2) is a definitive FAILURE.
      - X == Y and Y > 0 (e.g. 2/2, 4/4) is a definitive PASS.
    Returns (passed: bool, message: str).
    """
    print(f"[*] Monitoring test execution results (up to {timeout}s)...")
    start = time.time()

    fail_keywords = [
        "compilation error",
        "wrong answer",
        "runtime error",
        "time limit exceeded",
        "test cases failed",
        "failed to compile",
        "syntaxerror",
        "include the whitelist syntaxes",
        "whitelist error",
    ]

    time.sleep(1.0)  # Short initial wait for action initiation

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)

        # 1. Instant Toast / Floating Alert Check (catches Whitelist / Syntax error toasts immediately)
        alert = detect_floating_alerts(driver)
        if alert:
            print(f"\n[X] Platform Toast / Alert INTERCEPTED: '{alert}'")
            return False, f"Platform Alert: {alert}"

        try:
            # 2. Extract dedicated result/output panes and check Submit Code button state
            exec_data = driver.execute_script("""
                const selectors = '.output-pane, [class*="console"], [class*="result"], .testcase, [class*="testcase"], pre, .compiler-message, [class*="t-bg-neutral-4"]';
                const containers = Array.from(document.querySelectorAll(selectors));
                const resText = containers.map(c => (c.innerText || '').trim()).filter(t => t.length > 0).join('\\n').toLowerCase();
                
                // Check if 'Submit Code' button is active (enabled + primary blue color)
                const submitBtn = Array.from(document.querySelectorAll('button')).find(b => {
                    const t = (b.innerText || '').trim().toLowerCase();
                    return t.includes('submit code') && !b.disabled && (b.className || '').includes('primary-btn-color');
                });
                
                return {
                    res_text: resText,
                    submit_active: !!submitBtn
                };
            """)
            res_text = exec_data.get("res_text", "")
            submit_active = exec_data.get("submit_active", False)

            # 3. Check if still compiling or executing
            if any(prog in res_text for prog in ["compiling", "executing", "running test", "evaluating"]):
                print(f"\r[*] Tests running: compiling/executing in progress... ({elapsed}s)", end="", flush=True)
                time.sleep(0.5)
                continue

            # 4. PRIMARY CHECK: Parse explicit testcase fraction (e.g. "0/2 Sample testcase passed", "2/2 Sample testcase passed")
            frac_match = re.search(r"\b(\d+)\s*/\s*(\d+)\s*(?:sample\s*)?test", res_text)
            if frac_match:
                passed_cnt = int(frac_match.group(1))
                total_cnt = int(frac_match.group(2))
                
                # If any testcase failed (e.g. 0/2, 1/2) -> DEFINITIVE FAILURE!
                if passed_cnt < total_cnt or total_cnt == 0:
                    print(f"\n[X] Test execution FAILED! Only {passed_cnt}/{total_cnt} sample testcases passed.")
                    return False, f"Only {passed_cnt}/{total_cnt} sample testcases passed"

                # If all passed (e.g. 2/2, 4/4) and NO card is failed -> DEFINITIVE PASS!
                if passed_cnt == total_cnt and total_cnt > 0:
                    if not re.search(r"testcase\s*\d*\s*-\s*failed", res_text) and "wrong answer" not in res_text:
                        print(f"\n[OK] Test cases PASSED! Verified {passed_cnt}/{total_cnt} sample testcases passed.")
                        return True, f"{passed_cnt}/{total_cnt} sample testcases passed"

            # 5. Check for explicit testcase failure cards (e.g. "Testcase 1 - Failed")
            testcase_failed = re.search(r"testcase\s*\d*\s*-\s*failed", res_text)
            if testcase_failed:
                print(f"\n[X] Test execution FAILED! Detected: '{testcase_failed.group(0)}'")
                return False, testcase_failed.group(0)

            # 6. Check for compilation / runtime error keywords
            for fail_kw in fail_keywords:
                if fail_kw in res_text:
                    print(f"\n[X] Test execution FAILED! Detected failure indicator: '{fail_kw}'")
                    return False, fail_kw

            # 7. Check for unambiguous full-sentence pass phrases ONLY if no failure exists
            if "all test cases passed" in res_text and not testcase_failed:
                print(f"\n[OK] Test cases PASSED! Verified keyword: 'all test cases passed'")
                return True, "all test cases passed"

        except Exception:
            pass

        print(f"\r[*] Monitoring test results... ({elapsed}s elapsed) ", end="", flush=True)
        time.sleep(0.5)

    print(f"\n[*] Test monitoring finished (no explicit errors detected). Proceeding.")
    return True, "No errors detected (timeout)"

def extract_detailed_error_diagnostic(driver, last_alert: str = "") -> str:
    """
    Deeply parses testcase cards, compiler output, input/expected/actual mismatches,
    and platform alerts into a structured diagnostic report for AI self-healing.
    """
    script = """
        const report = [];

        // 1. Gather compiler output or traceback
        const compilerBoxes = Array.from(document.querySelectorAll('.output-pane, [class*="console"], [class*="terminal"], [class*="compiler"], pre, code'));
        for (const box of compilerBoxes) {
            const txt = (box.innerText || '').trim();
            if (txt.length > 0 && (/traceback/i.test(txt) || /error/i.test(txt) || /syntaxerror/i.test(txt) || /exception/i.test(txt) || /failed/i.test(txt))) {
                report.push('=== COMPILER / TERMINAL OUTPUT ===');
                report.push(txt.slice(0, 1000));
                break;
            }
        }

        // 2. Structured Testcase Cards (Input, Expected, Actual)
        const testCards = Array.from(document.querySelectorAll('[class*="testcase"], [class*="test-case"], .ant-collapse-item, [class*="tab-pane"]'));
        let foundTestDetails = false;
        
        for (let idx = 0; idx < testCards.length; idx++) {
            const card = testCards[idx];
            const txt = (card.innerText || '').trim();
            if (/input/i.test(txt) && (/expected/i.test(txt) || /actual/i.test(txt) || /output/i.test(txt))) {
                foundTestDetails = true;
                report.push(`--- Testcase Card #${idx + 1} ---`);
                const lines = txt.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                for (const line of lines) {
                    if (/^(input|expected|actual|output|status|result|compiler message)/i.test(line) || line.length < 100) {
                        report.push(line);
                    }
                }
            }
        }

        // 3. Fallback to keyword window scanning on entire body if no structured card found
        if (!foundTestDetails) {
            const bodyLines = (document.body ? document.body.innerText : '').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            const kw = ['expected output', 'actual output', 'compiler message', 'testcase', 'traceback', 'syntaxerror', 'whitelist'];
            const matched = [];
            for (let i = 0; i < bodyLines.length; i++) {
                const line = bodyLines[i];
                if (kw.some(k => line.toLowerCase().includes(k))) {
                    for (let j = Math.max(0, i - 1); j <= Math.min(bodyLines.length - 1, i + 2); j++) {
                        const candidate = bodyLines[j];
                        if (!matched.includes(candidate)) matched.push(candidate);
                    }
                }
            }
            if (matched.length > 0) {
                report.push('=== PAGE ERROR SNIPPETS ===');
                report.push(matched.slice(0, 25).join('\\n'));
            }
        }

        return report.join('\\n');
    """
    details = ""
    try:
        details = driver.execute_script(script) or ""
    except Exception:
        pass

    out_parts = []
    if last_alert:
        out_parts.append(f"INTERCEPTED PLATFORM ALERT / TOAST:\n{last_alert}\n")
    if details:
        out_parts.append(f"EXTRACTED TEST & COMPILER DIAGNOSTICS:\n{details}")
    
    return "\n".join(out_parts).strip()

# =============================================================================
# 6. INTERACTIVE LIVE COUNTDOWN CONTROLLER
# =============================================================================
def sleep_with_countdown(total_seconds: int, stage_name: str = "Pacing Delay", next_action: str = "Proceeding"):
    """
    Live pacing countdown before compilation or submission.
    Interactive features:
    - Press [ENTER] or [S] at any time -> trigger next action immediately (0s wait)
    - Press [C] at any time            -> set custom wait time
    - Type any digit (0-9) directly    -> change timer on the fly
    """
    if total_seconds <= 0:
        return

    m = total_seconds // 60
    s = total_seconds % 60
    print("\n" + "=" * 65)
    print(f"[*] {stage_name}: {total_seconds}s (~{m}m {s:02d}s) scheduled.")
    print("[*] LIVE TERMINAL CONTROLS:")
    print(f"    - Press [ENTER] or [S] -> {next_action.upper()} IMMEDIATELY (0s wait)")
    print("    - Press [C]            -> Change wait time (e.g. '0', '30s', '2m')")
    print("    - Type any digit (0-9) -> Adjust timer on the fly")
    print("    - Or just wait; it will advance automatically when timer expires.")
    print("=" * 65 + "\n")

    current_remaining = float(total_seconds)
    last_print_second = -1

    while current_remaining > 0:
        if HAS_MSVCRT:
            try:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    # Instant trigger: Enter, newline, 's', 'S'
                    if ch in ('\r', '\n', 's', 'S'):
                        print(f"\n\n[!] User triggered IMMEDIATE {next_action.upper()}! Skipping remaining wait...")
                        return

                    # Change time triggers: 'c', 'C', 't', 'T'
                    elif ch in ('c', 'C', 't', 'T'):
                        print("\n")
                        try:
                            raw = input("[?] Enter new wait time (e.g. '0' for instant, '30' for 30s, '2m' for 2 min): ").strip()
                            new_sec = parse_duration(raw)
                            if new_sec <= 0:
                                print(f"[!] Immediate {next_action} selected!")
                                return
                            current_remaining = float(new_sec)
                            print(f"[*] Timer updated to {new_sec} seconds!\n")
                            last_print_second = -1
                        except Exception as e:
                            print(f"[!] Invalid input: {e}. Resuming countdown...")

                    # User typed a digit directly (0-9)
                    elif ch.isdigit():
                        print(f"\n")
                        try:
                            rest = input(f"[?] Enter new delay (starting with '{ch}', e.g. '{ch}0' or '{ch}m', ENTER to confirm): ").strip()
                            full_val = ch + rest
                            new_sec = parse_duration(full_val)
                            if new_sec <= 0:
                                print(f"[!] Immediate {next_action} selected!")
                                return
                            current_remaining = float(new_sec)
                            print(f"[*] Timer updated to {new_sec} seconds!\n")
                            last_print_second = -1
                        except Exception as e:
                            print(f"[!] Invalid input: {e}. Resuming countdown...")
            except Exception:
                pass

        # Update countdown line on each full second
        sec_int = int(current_remaining)
        if sec_int != last_print_second:
            last_print_second = sec_int
            rm = sec_int // 60
            rs = sec_int % 60
            print(f"\r[*] {next_action} in: {rm}m {rs:02d}s remaining... [Press ENTER/S to skip wait, C to change] ", end="", flush=True)

        time.sleep(0.1)
        current_remaining -= 0.1

    print(f"\r[OK] Countdown complete! {next_action}...                                              \n")

# =============================================================================
# 7. MULTIPLE CHOICE QUESTION (MCQ) SOLVER & TICKER
# =============================================================================
def detect_question_type(driver) -> str:
    """
    Determines if the current question is 'MCQ' or 'CODING'.
    """
    script = """
        // 1. Check for radio buttons or checkmark containers
        const radios = document.querySelectorAll('input[type="radio"], label.checkmark-container, [class*="checkmark-container"]');
        if (radios.length > 0) return 'MCQ';

        // 2. Check for explicit question type text in page
        const text = document.body ? document.body.innerText : '';
        if (text.includes('Multi Choice Type Question') || (text.includes('Answer here') && text.includes('Clear'))) {
            return 'MCQ';
        }

        // 3. Check for coding indicators
        const ace = document.querySelector('.ace_editor');
        if (ace && ace.offsetParent !== null) return 'CODING';

        return 'CODING';
    """
    try:
        res = driver.execute_script(script)
        if res in ('MCQ', 'CODING'):
            return res
    except Exception:
        pass
    return 'CODING'

def extract_mcq_data(driver) -> dict:
    """
    Extracts the question statement and options from an MCQ question.
    """
    script = """
        let qText = '';
        const fullText = document.body ? document.body.innerText : '';
        
        if (fullText.includes('Answer here')) {
            const parts = fullText.split('Answer here');
            qText = parts[0].trim();
            const qIdx = qText.indexOf('Question No');
            if (qIdx !== -1) {
                qText = qText.slice(qIdx);
            }
        } else {
            const qEl = document.querySelector('.question-text, [class*="question-container"], [class*="problem-description"], .ql-editor');
            qText = qEl ? qEl.innerText.trim() : fullText.slice(0, 500);
        }

        const optionDivs = Array.from(document.querySelectorAll('div[aria-labelledby="each-option"]'));
        const options = [];
        if (optionDivs.length > 0) {
            for (let i = 0; i < optionDivs.length; i++) {
                const el = optionDivs[i];
                const text = (el.innerText || '').trim();
                options.push({
                    index: i,
                    text: text
                });
            }
        } else {
            const optionLabels = Array.from(document.querySelectorAll('label.checkmark-container, [class*="checkmark-container"]'));
            for (let i = 0; i < optionLabels.length; i++) {
                const lbl = optionLabels[i];
                const text = (lbl.innerText || '').trim();
                options.push({
                    index: i,
                    text: text
                });
            }
        }

        return {
            question_text: qText,
            options: options
        };
    """
    try:
        data = driver.execute_script(script)
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"[!] Error extracting MCQ data: {e}")
    return {"question_text": "", "options": []}

def clean_mcq_text(text: str) -> str:
    """Removes zero-width and invisible characters commonly injected by web platforms."""
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF\u00a0]", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()

def extract_code_from_mcq(q_text: str) -> str:
    """
    Extracts executable Python code snippets from an MCQ question statement.
    Handles numbered lines (e.g. '1 a = 4', '2 b = 9'), standalone gutter numbers, and code blocks.
    """
    lines = [l.rstrip() for l in q_text.splitlines() if l.strip()]
    
    # 1. Look for inline numbered lines e.g. "1 a = 4", "2 b = 9"
    numbered_lines = []
    in_numbered = False
    for line in lines:
        m = re.match(r"^\s*(\d{1,3})\s{1,4}(\S.*)$", line)
        if m:
            in_numbered = True
            numbered_lines.append(m.group(2))
        elif in_numbered:
            if not any(k in line.lower() for k in ["option", "choose", "select", "marks :", "negative marks"]):
                numbered_lines.append(line)
            else:
                break
    
    if len(numbered_lines) >= 2:
        return "\n".join(numbered_lines)

    # 2. Look for "output of the following" or "following code"
    header_idx = -1
    for i, line in enumerate(lines):
        if any(h in line.lower() for h in ["output of", "following code", "following snippet", "following program", "following python"]):
            header_idx = i
            break
            
    if header_idx != -1 and header_idx + 1 < len(lines):
        code_candidates = []
        for line in lines[header_idx + 1:]:
            if any(term in line.lower() for term in ["marks :", "negative marks", "options", "answer here"]):
                break
            # Skip standalone gutter numbers like "1", "2", "3"
            if re.match(r"^\s*\d{1,3}\s*$", line):
                continue
            # Strip inline leading numbers if present (e.g. "1  x = 2")
            cleaned = re.sub(r"^\s*\d{1,3}\s{1,4}", "", line)
            code_candidates.append(cleaned)
        if len(code_candidates) > 0:
            return "\n".join(code_candidates)

    return ""

def execute_mcq_code_snippet(code: str, options: list) -> tuple:
    """
    Executes Python code in a safe local sandbox with a strict 3.0s timeout.
    Returns (matched_option_index: int, details: str) or (None, "") if no match.
    """
    if not code or not code.strip():
        return None, ""

    try:
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=3.0
        )
        
        # Success case: match stdout against options
        if res.returncode == 0:
            raw_stdout = res.stdout.strip()
            stdout_lower = raw_stdout.lower()
            print(f"[*] Sandbox Execution Output: '{raw_stdout}'")

            for opt in options:
                opt_text = clean_mcq_text(opt['text'])
                opt_lower = opt_text.lower()
                
                # Direct string equality or case-insensitive equality
                if opt_text == raw_stdout or opt_lower == stdout_lower:
                    return opt['index'], f"Python Sandbox executed code -> Output: '{raw_stdout}' matches Option #{opt['index'] + 1}"
                
                # Check for float vs int representation e.g. 2.0 vs 2
                try:
                    if float(opt_text) == float(raw_stdout):
                        return opt['index'], f"Python Sandbox numeric match -> Output: '{raw_stdout}' matches Option #{opt['index'] + 1}"
                except ValueError:
                    pass

        # Error / Exception case: check for error options
        else:
            err_msg = (res.stderr or "").strip().splitlines()[-1] if res.stderr else "Runtime Exception"
            print(f"[*] Sandbox Execution Exception: '{err_msg}'")
            
            for opt in options:
                opt_lower = clean_mcq_text(opt['text']).lower()
                if any(err_word in opt_lower for err_word in ["error", "exception", "syntaxerror", "indexerror", "typeerror", "nameerror", "zerodivisionerror"]):
                    return opt['index'], f"Python Sandbox raised error: '{err_msg}' -> Matches Option #{opt['index'] + 1}"

    except subprocess.TimeoutExpired:
        print("[!] Sandbox Execution timed out (>3.0s). Infinite loop detected.")
        for opt in options:
            if "infinite" in opt['text'].lower() or "loop" in opt['text'].lower():
                return opt['index'], f"Python Sandbox timed out -> Matches Option #{opt['index'] + 1}"
    except Exception as e:
        print(f"[!] Sandbox Execution error: {e}")

    return None, ""

def query_groq_mcq(model: str, question_text: str, options: list) -> tuple:
    """Queries a single Groq model for an MCQ solution. Returns (chosen_index: int, reasoning: str)."""
    ensure_groq_api_key()

    formatted_options = []
    for opt in options:
        formatted_options.append(f"{opt['index'] + 1}. {clean_mcq_text(opt['text'])}")
    options_str = "\n".join(formatted_options)

    system_prompt = (
        "You are an expert computer science and programming tutor.\n"
        "You will be given a Multiple Choice Question (MCQ) and options.\n"
        "Your task is to analyze the question carefully, trace any code step-by-step, "
        "and identify the single correct option.\n"
        "OUTPUT FORMAT:\n"
        "You must respond strictly in this exact format:\n"
        "CHOICE: <number between 1 and 4>\n"
        "REASONING: <brief one sentence explanation>"
    )

    user_content = (
        f"Question:\n{question_text}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Which option is correct? Respond strictly with CHOICE: <number>"
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.0
    }

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AutoCode/1.0"
        },
        data=json.dumps(payload).encode("utf-8")
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ans = data["choices"][0]["message"]["content"].strip()

        m = re.search(r"CHOICE\s*:\s*(\d+)", ans, re.IGNORECASE)
        if m:
            choice_num = int(m.group(1)) - 1
            return max(0, min(choice_num, len(options) - 1)), ans

        for opt in options:
            if clean_mcq_text(opt['text']).lower() in ans.lower():
                return opt['index'], ans

        return 0, ans
    except Exception as e:
        return None, str(e)

def solve_mcq_with_dual_consensus(question_text: str, options: list) -> tuple:
    """
    Queries two independent LLM models on Groq for cross-validation.
    Returns (chosen_index: int, reasoning: str).
    """
    print(f"[*] Querying Primary Model ({GROQ_MODEL})...")
    start = time.time()
    c1, r1 = query_groq_mcq(GROQ_MODEL, question_text, options)
    t1 = int((time.time() - start) * 1000)

    print(f"[*] Querying Secondary Model ({GROQ_SECONDARY_MODEL}) for Cross-Validation...")
    start = time.time()
    c2, r2 = query_groq_mcq(GROQ_SECONDARY_MODEL, question_text, options)
    t2 = int((time.time() - start) * 1000)

    print(f" -> Model 1 ({GROQ_MODEL}, {t1}ms): Option #{c1 + 1 if c1 is not None else 'N/A'}")
    print(f" -> Model 2 ({GROQ_SECONDARY_MODEL}, {t2}ms): Option #{c2 + 1 if c2 is not None else 'N/A'}")

    if c1 is not None and c2 is not None and c1 == c2:
        return c1, f"[100% Consensus] Both {GROQ_MODEL} and {GROQ_SECONDARY_MODEL} selected Option #{c1 + 1}.\nReasoning: {r1}"
    elif c1 is not None:
        return c1, f"[Primary Model Decisive] {GROQ_MODEL} chosen over secondary.\nReasoning: {r1}"
    elif c2 is not None:
        return c2, f"[Secondary Model Fallback] {GROQ_SECONDARY_MODEL} chosen.\nReasoning: {r2}"
    else:
        return 0, "No model returned a response."

def select_mcq_option(driver, target_idx: int, retries: int = 3) -> bool:
    """
    Clicks the specified MCQ option container with Triple-Layer verification:
      Layer 1: Native DOM input radio.checked === true
      Layer 2: Visual CSS active class (primary blue pill / border)
      Layer 3: Left sidebar palette status badge updated
    Prefers native CDP Input (isTrusted: true) with automatic fallback.
    """
    for attempt in range(retries):
        try:
            # 1. Attempt native CDP Input dispatching (isTrusted: true)
            cdp_clicked = False
            try:
                el = driver.execute_script(f"""
                    const div = document.getElementById('tt-option-{target_idx}') || 
                                document.querySelectorAll('div[aria-labelledby="each-option"]')[{target_idx}];
                    if (!div) return null;
                    return div.querySelector('.checkmark1, [class*="checkmark"]') || div;
                """)
                if el:
                    cdp_clicked = cdp_click_element(driver, el)
            except Exception:
                cdp_clicked = False

            # 2. Check and fallback to styled checkmark click if needed
            script = """
                const targetIdx = arguments[0];
                const div = document.getElementById(`tt-option-${targetIdx}`) || 
                            document.querySelectorAll('div[aria-labelledby="each-option"]')[targetIdx];
                if (!div) return { success: false, reason: 'Option container not found' };

                const checkmark = div.querySelector('.checkmark1, [class*="checkmark"]') || div;
                checkmark.scrollIntoView({ behavior: 'instant', block: 'center' });
                
                const radio = div.querySelector('input[type="radio"]');
                const isChecked = radio ? radio.checked : false;
                const hasBlue = div.className.includes('primary') || 
                                (checkmark && checkmark.className.includes('primary')) ||
                                div.className.includes('selected');

                if (!isChecked && !hasBlue) {
                    checkmark.click();
                }

                return {
                    success: (radio && radio.checked) || hasBlue,
                    checked: radio ? radio.checked : false,
                    hasBlue: hasBlue,
                    text: div.innerText.trim()
                };
            """
            res = driver.execute_script(script, target_idx)
            if res and isinstance(res, dict) and res.get("success"):
                clean_text = clean_mcq_text(res.get('text', ''))
                cdp_tag = " [CDP isTrusted: True]" if cdp_clicked else ""
                print(f"[OK] Option #{target_idx + 1} ('{clean_text}') selected!{cdp_tag} "
                      f"(Layer 1 DOM: {res.get('checked')}, Layer 2 CSS: {res.get('hasBlue')})")

                # Layer 3: Verify palette status
                palette_verified = driver.execute_script("""
                    const sidebar = document.querySelector('.test-sidebar');
                    if (!sidebar) return true;
                    const answeredEl = Array.from(sidebar.querySelectorAll('*')).find(el => {
                        return el.children.length === 0 && (el.innerText || '').includes('Answered');
                    });
                    return !!answeredEl;
                """)
                if palette_verified:
                    print("[OK] Layer 3 Verified: Examly sidebar palette acknowledges answer state!")
                return True
            else:
                print(f"[!] Attempt #{attempt + 1}: Selection not confirmed ({res}). Retrying with ActionChains...")
                opts = driver.find_elements(By.CSS_SELECTOR, 'div[aria-labelledby="each-option"]')
                if target_idx < len(opts):
                    ActionChains(driver).move_to_element(opts[target_idx]).click().perform()
                time.sleep(0.5)
        except Exception as e:
            print(f"[!] Error in select_mcq_option (attempt {attempt + 1}): {e}")
            time.sleep(0.5)

    return False

def click_mcq_next(driver) -> bool:
    """
    Clicks the 'Next' button on an MCQ question using unified click_next_button.
    """
    return click_next_button(driver)

def process_mcq_question(driver, question_num: int) -> bool:
    print(f"\n=========================================================")
    print(f"  [MCQ Question #{question_num}] Detecting, Solving & Ticking...")
    print(f"=========================================================")

    switch_to_latest_tab(driver)

    mcq_data = extract_mcq_data(driver)
    q_text = clean_mcq_text(mcq_data.get("question_text", ""))
    options = mcq_data.get("options", [])

    if not options:
        print("[!] No MCQ options found on page! Falling back to coding handler...")
        return process_coding_question(driver, question_num)

    # Clean all options text
    for opt in options:
        opt['text'] = clean_mcq_text(opt['text'])

    print(f"[OK] Extracted MCQ Question:\n{q_text[:300]}...")
    print(f"[*] Available Options ({len(options)}):")
    for opt in options:
        print(f"    [{opt['index'] + 1}] {opt['text']}")

    # STEP 1: Attempt Python Sandbox Execution First (100% mathematical certainty)
    code_snippet = extract_code_from_mcq(q_text)
    chosen_idx = None
    explanation = ""

    if code_snippet:
        print("\n[*] Detected code snippet in MCQ. Attempting Python Sandbox execution...")
        print(f"--- Code Snippet ---\n{code_snippet}\n--------------------")
        sandbox_idx, sandbox_reason = execute_mcq_code_snippet(code_snippet, options)
        if sandbox_idx is not None:
            print(f"\n[SANDBOX HIT] Executed code locally with 100% mathematical certainty!")
            chosen_idx = sandbox_idx
            explanation = sandbox_reason

    # STEP 2: Dual-Model Cross-Validation Fallback (if sandbox didn't resolve)
    if chosen_idx is None:
        print("\n[*] Invoking Dual-Model Cross-Validation (Groq openai/gpt-oss-120b + qwen/qwen3.8-27b)...")
        chosen_idx, explanation = solve_mcq_with_dual_consensus(q_text, options)

    chosen_opt = options[chosen_idx]
    print(f"\n[>] Selected Answer: Option #{chosen_idx + 1} -> '{chosen_opt['text']}'")
    print(f"[*] Explanation: {explanation.strip()}\n")

    # STEP 3: Triple-Layer Option Ticking & Confirmation
    print(f"[*] Ticking Option #{chosen_idx + 1} ('{chosen_opt['text']}')...")
    ticked = select_mcq_option(driver, chosen_idx)
    if ticked:
        print(f"[OK] Option #{chosen_idx + 1} ('{chosen_opt['text']}') ticked and registered successfully!")
    else:
        print(f"[!] Warning: Could not verify option click via JS.")

    time.sleep(1)

    # Realistic Human Pacing: Reading-Speed & Complexity Modeled
    if SUBMIT_DELAY_OVERRIDE is not None:
        mcq_delay = SUBMIT_DELAY_OVERRIDE
    else:
        mcq_delay = calculate_human_pacing(
            q_text,
            code_snippet,
            min_sec=MIN_MCQ_DELAY_SECONDS,
            max_sec=MAX_MCQ_DELAY_SECONDS
        )

    if mcq_delay > 0:
        sleep_with_countdown(
            mcq_delay,
            stage_name="MCQ Human Thinking & Verification Pacing",
            next_action="Advancing to Next Question"
        )

    # Click "Next" to save and move to next question
    print("[*] Clicking 'Next' button to save answer and advance...")
    clicked_next = click_mcq_next(driver)
    if clicked_next:
        print("[OK] Clicked 'Next' button!")
    else:
        print("[!] Next button not found. Using question palette navigation...")
        next_q = question_num + 1
        navigate_to_question(driver, next_q)

    time.sleep(2)
    return True

# =============================================================================
# 8. CODING QUESTION PROCESSING PIPELINE (2-STAGE REALISTIC WORKFLOW)
# =============================================================================
def process_coding_question(driver, question_num: int):
    print(f"\n=========================================================")
    print(f"  [Coding Question #{question_num}] Reading Screen & Processing...")
    print(f"=========================================================")

    switch_to_latest_tab(driver)

    problem_text = extract_problem_text(driver)
    if not problem_text:
        raise RuntimeError("Extracted problem text was empty! Make sure the question is visible in Chrome.")

    print(f"[OK] Extracted {len(problem_text)} characters from problem page.")

    # Universal Pre-Check: Scan for platform constraints (Whitelist, Blacklist, required functions)
    constraints = extract_page_constraints(driver)
    if constraints.get("whitelist"):
        print(f"[!] DETECTED PLATFORM WHITELIST: {constraints['whitelist']}")
    if constraints.get("blacklist"):
        print(f"[!] DETECTED PLATFORM BLACKLIST: {constraints['blacklist']}")
    if constraints.get("raw_matches"):
        print(f"[*] Platform constraint badges: {constraints['raw_matches']}")

    # Cache check
    code = get_from_cache(problem_text)
    if code:
        # If cached code exists, verify if it meets the whitelist before using
        wl = constraints.get("whitelist", [])
        if wl and not any(f in code for f in wl):
            print(f"[!] Cached solution missing mandatory whitelist {wl}. Regenerating...")
            code = ""
        else:
            print("\n[CACHE HIT] Loaded verified solution from local cache (0 API calls used)!")

    if not code:
        print("[*] Querying Groq (openai/gpt-oss-120b) for Python solution with constraint enforcement...")
        start = time.time()
        code = solve_with_groq(problem_text, constraints=constraints)
        elapsed_ms = int((time.time() - start) * 1000)
        print(f"[OK] Solution generated in {elapsed_ms} ms!")
        save_to_cache(problem_text, code)

    print("\n----- Generated Code -----\n" + code + "\n---------------------------\n")

    # Step 1: Inject code into Ace Editor (wipes existing template first)
    print("[*] Injecting code into Ace Editor (with Angular event sync)...")
    inject_code_into_editor(driver, code, CODE_INPUT_SELECTOR)
    time.sleep(1.5)

    # Step 2: Stage 1 Pacing - Coding Simulation (~3 to 4 minutes)
    if SUBMIT_DELAY_OVERRIDE is not None:
        coding_delay = SUBMIT_DELAY_OVERRIDE
    else:
        coding_delay = random.randint(MIN_CODING_DELAY_SECONDS, MAX_CODING_DELAY_SECONDS)

    if coding_delay > 0:
        sleep_with_countdown(
            coding_delay,
            stage_name="Stage 1: Simulating Coding / Typing Time",
            next_action="Triggering 'Compile & Run'"
        )

    # Step 3: Click "Compile & Run" with Automatic Self-Healing / Retry Loop
    MAX_COMPILE_ATTEMPTS = 4
    compile_attempt = 1
    passed = False
    last_error_message = ""
    clicked_run = False

    while compile_attempt <= MAX_COMPILE_ATTEMPTS:
        print(f"\n[*] Triggering 'Compile & Run' button (Attempt {compile_attempt} of {MAX_COMPILE_ATTEMPTS})...")
        clicked_run = click_smart_button(driver, RUN_BUTTON_LABELS)
        if not clicked_run:
            print(f"[!] Warning: Could not locate 'Compile & Run' button on screen.")
            print("[*] If this is an MCQ or non-coding question, proceeding directly to submission...")
            passed = True  # Treat as non-coding question, proceed to submit
            break

        print(f"[OK] Clicked 'Compile & Run' button!")
        passed, msg = wait_for_test_results(driver, timeout=40)

        if passed:
            print(f"\n[OK] All test cases PASSED successfully on attempt #{compile_attempt}!")
            break

        last_error_message = msg
        print(f"\n[X] Test execution failed on attempt #{compile_attempt}!")
        print(f"    Detected issue: {msg}")

        if compile_attempt < MAX_COMPILE_ATTEMPTS:
            print("\n" + "=" * 65)
            print(f"  [*] AUTO-HEALING ACTIVATED: Diagnosing & Repairing Solution")
            print("=" * 65)
            
            # Deep diagnostic extraction
            error_details = extract_detailed_error_diagnostic(driver, last_alert=msg)
            print(f"[*] Extracted Diagnostic Report:\n{error_details}\n")

            print("[*] Querying Groq to heal and rewrite solution based on diagnostics...")
            code = solve_with_groq(
                problem_text,
                constraints=constraints,
                error_context=f"Failed Code:\n{code}\n\nDiagnostic Output:\n{error_details}"
            )
            print("\n----- Healed Code -----\n" + code + "\n------------------------\n")
            save_to_cache(problem_text, code)

            print("[*] Re-injecting clean fixed code into Ace Editor...")
            inject_code_into_editor(driver, code, CODE_INPUT_SELECTOR)
            time.sleep(2)
            compile_attempt += 1
        else:
            compile_attempt += 1

    if not passed and clicked_run:
        print("\n" + "=" * 65)
        print(f"  [!] All {MAX_COMPILE_ATTEMPTS} automatic attempts failed to pass tests!")
        print(f"      Last error: {last_error_message}")
        print("=" * 65)
        print("Options:")
        print("  - Press [S]            -> Override and force submit anyway")
        print("  - Press [ENTER] or [N] -> Skip to next question")
        print("=" * 65)
        ans = input("Your choice ('s' to submit, [ENTER] to skip): ").strip().lower()
        if ans in ("s", "submit", "force"):
            print("[*] User chose to force submission.")
        else:
            print("[*] Skipping submission on user request.")
            return False

    # Step 4: Stage 2 Pacing - Final Review Simulation (~1 minute)
    if SUBMIT_DELAY_OVERRIDE is not None:
        review_delay = 0  # If user set custom delay, it already applied at Stage 1
    else:
        review_delay = random.randint(MIN_REVIEW_DELAY_SECONDS, MAX_REVIEW_DELAY_SECONDS)

    if review_delay > 0:
        sleep_with_countdown(
            review_delay,
            stage_name="Stage 2: Simulating Final Review & Verification Time",
            next_action="Triggering 'Submit Code'"
        )

    # Step 5: Click "Submit Code" (Strictly protected against "Submit Test")
    print(f"[*] Triggering 'Submit Code' button (Question submission)...")
    clicked_submit = click_smart_button(driver, SUBMIT_BUTTON_LABELS)
    if clicked_submit:
        print(f"[OK] Clicked 'Submit Code' successfully!")
        time.sleep(3)
    else:
        print(f"[!] Warning: Could not find 'Submit Code' button on screen.")

    return True

# =============================================================================
# 9. MASTER QUESTION PROCESSOR (AUTO-ROUTER)
# =============================================================================
def process_question(driver, question_num: int):
    # Guard: Ensure current session account is authorized
    verify_user_authorization(driver, stage_name=f"Question #{question_num}")
    q_type = detect_question_type(driver)
    print(f"\n[*] Question Type Detected: [{q_type}]")
    if q_type == "MCQ":
        return process_mcq_question(driver, question_num)
    else:
        return process_coding_question(driver, question_num)

# =============================================================================
# 8. MAIN GUIDED WORKFLOW
# =============================================================================
def main():
    global SUBMIT_DELAY_OVERRIDE
    try:
        # CLI Argument Parsing
        if len(sys.argv) > 1:
            arg = sys.argv[1].strip().lower()
            if arg in ("instant", "0", "now"):
                SUBMIT_DELAY_OVERRIDE = 0
                print("[*] CLI Mode: Instant submission enabled (0s delay).")
            elif re.match(r"^[\d.]+[sm]?", arg):
                SUBMIT_DELAY_OVERRIDE = parse_duration(arg)
                print(f"[*] CLI Mode: Custom submit delay set to {SUBMIT_DELAY_OVERRIDE}s.")

        driver = launch_chrome()

        # Check if Chrome is already on Examly
        switch_to_latest_tab(driver)
        current_url = driver.current_url.lower()

        if "examly.io" in current_url:
            print("\n======================================================================")
            print("  Active Examly Session Detected!")
            print("======================================================================")
            print(f"[*] Chrome is already at:\n    {driver.current_url}")
            # Verify authorization for existing session
            verify_user_authorization(driver, stage_name="Active Session Verification")
            print("[*] You are logged in and ready.")
            print("\n>>> Navigate to your desired question in Chrome, then press [ENTER] here to start! <<<")
            print(">>> (Or type 'login' + ENTER if you want to re-open the Login page)                  <<<")
            print("======================================================================")
            ans = input().strip().lower()
            if ans in ("login", "relogin"):
                handle_guided_login(driver)
                print(f"[*] Navigating to MyLabs URL: {LABS_URL}")
                driver.get(LABS_URL)
                print(f"[*] Opened MyLabs: {LABS_URL}")
                print(">>> When you are on your question page, press [ENTER] to start solving! <<<")
                input()
        else:
            # Guided flow with real-time email authorization gate
            handle_guided_login(driver)

            print(f"\n[*] Navigating to MyLabs URL: {LABS_URL}")
            driver.get(LABS_URL)

            print("\n======================================================================")
            print("  MyLabs Page Loaded!")
            print("======================================================================")
            print(f"[*] Chrome is now at your MyLabs dashboard:\n    {LABS_URL}")
            print("[*] You can manually browse, select, and open whatever problem you want!")
            print("[*] Take your time — the script is paused and waiting for you.")
            print("\n>>> When you are on the question page, press [ENTER] in this terminal to start solving! <<<")
            print("======================================================================")

            input()
            verify_user_authorization(driver, stage_name="Pre-Solve Verification")

        # Automated continuous loop for solving questions
        while True:
            current_q, total_q = get_current_question_info(driver)

            process_question(driver, current_q)

            print("\n" + "=" * 70)
            print(f"  [OK] Question #{current_q} of {total_q} Finished & Submitted!")
            print("=" * 70)

            if current_q >= total_q:
                print(f"\n[DONE] All {total_q} questions in this test have been solved and submitted!")
                print("[*] Automation finished cleanly. You may review in Chrome and submit the test when ready.")
                break

            next_q = current_q + 1
            # Check if page already transitioned to next_q (e.g. from MCQ 'Next' button)
            page_q, _ = get_current_question_info(driver)
            if page_q != next_q:
                print(f"[*] Navigating to Question #{next_q} of {total_q} automatically in 2s (Press Ctrl+C to pause/exit)...")
                time.sleep(2)

                # Navigate to next question via Palette on left
                print(f"[*] Clicking Question #{next_q} on palette...")
                navigated = navigate_to_question(driver, next_q)
                if not navigated:
                    print(f"[!] Could not auto-navigate to Question #{next_q}. Pausing for manual navigation.")
                    break
            else:
                print(f"[OK] Question #{next_q} already active on screen.")

            print(f"[OK] Successfully loaded Question #{next_q}!\n")
            time.sleep(2)  # Wait for new question DOM to render

    except KeyboardInterrupt:
        print("\n[*] Script interrupted by user. Exiting cleanly.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
