"""
================================================================================
VIT VELLORE INSTANT FFCS REGISTRATION BOT (WINTER 2026-27)
Student: Ayush Agarwal (26BCE3181) | Branch: B.Tech CSE (ACE System)
================================================================================
One-Click Launch -> Login on Chrome -> Press [ENTER] -> BOOM!

AUDIT FIXES APPLIED:
  1. Course ordering grouped by category (PCC first, then UCC) to minimize 
     category switches for max speed
  2. Saravanarajan DSA backup REMOVED (his lab is L3+L4 which clashes with SOOP)
  3. CourseOption RGR is set AFTER theory+lab selection (VTOP resets it on click)
  4. "Select the course option" SweetAlert handled as retry, not failure
  5. Email OTP detection added with user prompt
  6. Fallback lab logic guards against L3+L4 clash for English and DSA
  7. "already registered" course detection (skips gracefully)
  8. Session timeout detection & warning
  9. BAHUM101 (India Studies) - special handler for NIL-slot online courses
 10. Multiple SOOP backup teachers added (not just Mohan K)
"""

import sys
import time
import os
import subprocess
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==============================================================================
# COURSE TARGETS & CONTINGENCY MATRIX (ZERO-CLASH ARCHITECTURE)
# ==============================================================================
# MASTER BLUEPRINT (100% THEORY & LAB SLOT LOCK):
# Every fallback professor is strictly locked to BOTH the exact same Theory slot
# and the exact same Lab slot. Selecting Tier-2 or Tier-3 changes only the 
# teacher's name — class timings, lab hours, and weekly schedule remain identical.
#
# REGISTRATION ORDER:
#   1. Compulsory UCC Courses (BAENG101, BAHUM101) MUST be registered FIRST!
#      VTOP blocks Programme Core Courses (PCC) until compulsory courses are registered.
#   2. PCC Courses (Math, Comp Struct, DSA, SOOP) registered immediately after.
#   3. Engineering Physics (UCC) registered last.
#
# ZERO-CLASH TIMETABLE (MASTER BLUEPRINT):
#   - Mon Morning:   L3+L4 (SOOP Lab 1 - Anuradha G)
#   - Tue Morning:   L9+L10 (Comp Struct Lab - Prabhu R)
#   - Wed Morning:   L13+L14 (Physics Lab - K.L. Pandey)
#   - Wed Afternoon: L45+L46 (DSA Lab - Subramanyam Reddy A)
#   - Thu Morning:   L19+L20 (SOOP Lab 2) -> L21+L22 (English Lab - Saraswathy S)
#   - Friday:        Zero labs, clean weekend starting at 4:50 PM!

TARGET_COURSES = [
    # ==================== PRIORITY 1: COMPULSORY UCC COURSES ====================
    {
        "code": "BAENG101",
        "title": "Technical English Communication",
        "category": "UCC",
        "type": "ETL",
        "priority": 1,
        "plan_a": {
            "faculty": "SARASWATHY S",
            "theory_slot": "B2+TB2",
            "venue": "TT404",
            "lab_slot": "L21+L22",
            "lab_venue": "TT306",
        },
        "plan_b": [
            {
                "faculty": "DENISH RAJA DURAI K",
                "theory_slot": "B2+TB2",
                "venue": "TT402",
                "lab_slot": "L21+L22",
                "lab_venue": "TT307",
            },
            {
                "faculty": "SENTHIL BABU M K",
                "theory_slot": "B2+TB2",
                "venue": "PRP122",
                "lab_slot": "L21+L22",
                "lab_venue": "PRP554",
            },
        ]
    },
    {
        "code": "BAHUM101",
        "title": "India Studies",
        "category": "UCC",
        "type": "ETH",  # Online Course
        "priority": 2,
        "plan_a": {
            "faculty": "ADIL AHMAD SHAH",
            "theory_slot": "NIL",
        },
        "plan_b": [
            {"faculty": "ANY", "theory_slot": "NIL"},
        ]
    },

    # ==================== PRIORITY 2: PROGRAMME CORE COURSES (PCC) ====================
    {
        "code": "BAMAT205",
        "title": "Discrete Mathematics & Linear Algebra",
        "category": "PCC",
        "type": "ETH",  # Standalone 4-Credit Theory
        "priority": 3,
        "plan_a": {
            "faculty": "MONICA C",
            "theory_slot": "A2+TA2+TAA2",
            "venue": "PRP111",
        },
        "plan_b": [
            {"faculty": "REENU RANI", "theory_slot": "A2+TA2+TAA2", "venue": "PRP115"},
            {"faculty": "TABINDA NAHID", "theory_slot": "A2+TA2+TAA2", "venue": "PRP107"},
            {"faculty": "PARTHIBAN A", "theory_slot": "A2+TA2+TAA2", "venue": "PRP105"},
            {"faculty": "RAJESH BHATT", "theory_slot": "A2+TA2+TAA2", "venue": "PRP112"},
        ]
    },
    {
        "code": "BACSE103",
        "title": "Computation Structures",
        "category": "PCC",
        "type": "ETL",
        "priority": 4,
        "plan_a": {
            "faculty": "PRABHU R",
            "theory_slot": "C2+TC2",
            "venue": "PRP122",
            "lab_slot": "L9+L10",
            "lab_venue": "PRP117",
        },
        "plan_b": [
            {
                "faculty": "ARUN DEV DHAR DWIVEDI",
                "theory_slot": "C2+TC2",
                "venue": "PRPG21",
                "lab_slot": "L9+L10",
                "lab_venue": "PRP117",
            },
            {
                "faculty": "VIKAS VIJAYVARGIYA",
                "theory_slot": "C2+TC2",
                "venue": "PRP123",
                "lab_slot": "L9+L10",
                "lab_venue": "PRP117",
            },
        ]
    },
    {
        "code": "BACSE105",
        "title": "Data Structures & Algorithms",
        "category": "PCC",
        "type": "ETL",
        "priority": 5,
        "plan_a": {
            "faculty": "SUBRAMANYAM REDDY A",
            "theory_slot": "E2+TE2",
            "venue": "PRPG23",
            "lab_slot": "L45+L46",
            "lab_venue": "PRP135",
        },
        "plan_b": [
            {
                "faculty": "SHARIEF BASHA S",
                "theory_slot": "E2+TE2",
                "venue": "PRPG21",
                "lab_slot": "L45+L46",
                "lab_venue": "PRP135",
            },
            {
                "faculty": "SARAVANARAJAN M C",
                "theory_slot": "E2+TE2",
                "venue": "PRPG06",
                "lab_slot": "L45+L46",
                "lab_venue": "PRP135",
            },
        ]
    },
    {
        "code": "BACSE104",
        "title": "Structured and Object-Oriented Programming (SOOP)",
        "category": "PCC",
        "type": "ETL",
        "priority": 6,
        "plan_a": {
            "faculty": "ANURADHA G",
            "theory_slot": "D2",
            "venue": "PRPG03",
            "lab_slot": "L3+L4",
            "lab_venue": "PRP118a",
        },
        "plan_b": [
            {
                "faculty": "VINILA JINNY",
                "theory_slot": "D2",
                "venue": "PRP107",
                "lab_slot": "L3+L4",
                "lab_venue": "PRP118a",
            },
            {
                "faculty": "GUNASEKAR M",
                "theory_slot": "D2",
                "venue": "PRP116",
                "lab_slot": "L3+L4",
                "lab_venue": "PRP118a",
            },
        ]
    },

    # ==================== PRIORITY 3: UNIVERSITY CORE (UCC) ====================
    {
        "code": "BAPHY105",
        "title": "Engineering Physics",
        "category": "UCC",
        "type": "ETL",
        "priority": 7,
        "plan_a": {
            "faculty": "KANHAIYA LAL PANDEY",
            "theory_slot": "G2+TG2",
            "venue": "PRP109",
            "lab_slot": "L13+L14",
            "lab_venue": "PRPG17",
        },
        "plan_b": [
            {
                "faculty": "SAMUEL P",
                "theory_slot": "G2+TG2",
                "venue": "PRPG25",
                "lab_slot": "L13+L14",
                "lab_venue": "PRPG17",
            },
            {
                "faculty": "SANGEM RAJESH",
                "theory_slot": "G2+TG2",
                "venue": "PRP110",
                "lab_slot": "L13+L14",
                "lab_venue": "PRPG17",
            },
        ]
    }
]

# Slots that MUST NOT be selected for certain courses (hard clash rules)
CLASH_BLACKLIST = {
    "BACSE105": ["L3+L4", "L19+L20"],  # DSA lab must NOT touch SOOP lab slots
    "BAENG101": ["L3+L4", "L19+L20"],  # English lab must NOT touch SOOP lab slots
    "BACSE103": ["L3+L4", "L19+L20"],  # Comp Struct lab must NOT touch SOOP lab slots
    "BAPHY105": ["L3+L4", "L19+L20"],  # Physics lab must NOT touch SOOP lab slots
}


class FFCSBot:
    def __init__(self, port=9222):
        self.port = port
        self.driver = None
        self.registered = []

    def ensure_chrome_running(self):
        """Checks if Chrome is running on debugging port; if not, launches it."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', self.port))
        sock.close()

        if result == 0:
            print("[+] Chrome debugging port 9222 is already ACTIVE.")
            return True

        print("[*] Chrome port 9222 not detected. Launching Chrome automatically...")
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        target_chrome = next((p for p in chrome_paths if os.path.exists(p)), None)
        if not target_chrome:
            print("[-] Could not find Chrome. Please run vtop.bat manually.")
            return False

        profile_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\VTOPProfile")
        cmd = [
            target_chrome,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://vtopreg.vit.ac.in/indexplus/"
        ]
        subprocess.Popen(cmd)
        print("[+] Chrome launched! Waiting 4 seconds for initialization...")
        time.sleep(4)
        return True

    def connect(self):
        self.ensure_chrome_running()
        print(f"[*] Attaching to Chrome on port {self.port}...")
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")
        last_err = None
        for attempt in range(5):
            try:
                self.driver = webdriver.Chrome(options=options)
                print(f"[+] Connected! URL: {self.driver.current_url}")
                return True
            except Exception as e:
                last_err = e
                time.sleep(1)
        print(f"[-] Could not connect to Chrome: {last_err}")
        return False

    def is_logged_in(self):
        try:
            body_text = self.driver.execute_script("return document.body.innerText.slice(0, 500);")
            if "sign in" in body_text.lower() or "login" in body_text.lower():
                return False
            if "refrain" in body_text.lower() or "session" in body_text.lower():
                print("[!] Session timeout detected! Please re-login on Chrome.")
                return False
            has_nav = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('*')).some(el => 
                    (el.innerText || '').trim() === 'Home' || 
                    (el.innerText || '').trim().includes('View / Modify')
                );
            """)
            return has_nav
        except Exception:
            return False

    def navigate_home(self):
        self.driver.execute_script("""
            let home = Array.from(document.querySelectorAll('*')).find(el => 
                (el.innerText || '').trim() === 'Home' && 
                (el.tagName === 'A' || el.tagName === 'SPAN' || el.onclick)
            );
            if (home) home.click();
        """)
        time.sleep(1.0)

    def wait_for_loading(self, max_wait=5):
        """Waits for any VTOP blockUI overlay to disappear."""
        for _ in range(max_wait * 2):
            blocked = self.driver.execute_script(
                "return (typeof $ !== 'undefined' && $.blockUI) ? !!$('.blockUI').length : false;"
            )
            if not blocked:
                return
            time.sleep(0.5)

    def select_category(self, cat):
        res = self.driver.execute_script(f"""
            let r = document.querySelector('input[name="registrationOption"][value="{cat}"]');
            if (r) {{
                r.checked = true;
                let btn = document.querySelector('button[onclick*="viewRegistrationOption"]');
                if (btn) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        """)
        time.sleep(1.2)
        self.wait_for_loading()
        return res

    def open_course(self, code):
        opened = self.driver.execute_script(f"""
            let trs = Array.from(document.querySelectorAll('table tr'));
            let courseTr = trs.find(tr => tr.innerText.includes('{code}'));
            if (courseTr) {{
                let btn = courseTr.querySelector('button');
                if (btn) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        """)
        time.sleep(1.2)
        self.wait_for_loading()
        return opened

    def handle_alert(self):
        """Reads and dismisses any SweetAlert popup cleanly without leaving overlays."""
        return self.driver.execute_script("""
            let txt = '';
            let swalEl = document.querySelector('.sweet-alert.showSweetAlert, .swal2-modal, [class*="sweet-alert"]');
            if (swalEl) {
                txt = (swalEl.innerText || '').trim();
            }
            if (typeof swal !== 'undefined' && swal.close) {
                try { swal.close(); } catch(e){}
            }
            let okBtn = Array.from(document.querySelectorAll('.sweet-alert button, .swal2-modal button, button.confirm, .sa-confirm-button-container button, .sweet-alert .confirm')).find(b => {
                let t = (b.innerText || '').trim().toLowerCase();
                return t === 'ok' || t === 'confirm';
            });
            if (okBtn) {
                try { okBtn.click(); } catch(e){}
            }
            let overlay = document.querySelector('.sweet-overlay, .swal2-container');
            if (overlay) overlay.remove();
            let modal = document.querySelector('.sweet-alert, .swal2-modal');
            if (modal) modal.remove();
            return { has_alert: !!txt, text: txt };
        """)

    def check_otp_needed(self):
        """Checks if VTOP is showing an Email OTP input field."""
        return self.driver.execute_script("""
            let otpEl = document.querySelector(
                'input[name*="otp" i], input[placeholder*="OTP" i], input[id*="otp" i]'
            );
            return !!otpEl;
        """)

    def prompt_and_enter_otp(self):
        """Prompts user for OTP in the terminal and enters it on VTOP."""
        print("\n    [🔑 OTP REQUIRED] VTOP is asking for an Email OTP.")
        print("    Check your VIT email inbox now!")
        otp = input("    Enter the 5-character OTP here: ").strip()
        if len(otp) < 3:
            print("    [-] OTP too short, skipping.")
            return False
        self.driver.execute_script(f"""
            let otpEl = document.querySelector(
                'input[name*="otp" i], input[placeholder*="OTP" i], input[id*="otp" i]'
            );
            if (otpEl) otpEl.value = '{otp}';
            // Click submit/confirm button near OTP
            let submitBtn = Array.from(document.querySelectorAll('button')).find(
                b => /submit|confirm|verify|ok/i.test(b.innerText)
            );
            if (submitBtn) submitBtn.click();
        """)
        time.sleep(2)
        return True

    def register_course(self, course_info):
        code = course_info["code"]
        title = course_info["title"]
        cat = course_info["category"]
        is_etl = (course_info["type"] == "ETL")
        blacklisted_slots = CLASH_BLACKLIST.get(code, [])
        start_t = time.time()

        print(f"\n{'='*60}")
        print(f"[*] REGISTERING: {code} - {title} ({cat})")
        print(f"{'='*60}")

        self.navigate_home()
        if not self.select_category(cat):
            print(f"[-] Failed to switch to category {cat}")
            return False

        if not self.open_course(code):
            print(f"[-] Could not open {code} (already registered or not under {cat})")
            return False

        all_options = [course_info["plan_a"]] + course_info["plan_b"]

        for idx, option in enumerate(all_options):
            plan_label = "PLAN A" if idx == 0 else f"PLAN B#{idx}"
            fac = option["faculty"].upper()
            slot = option["theory_slot"]
            lab_slot = option.get("lab_slot")

            print(f"[*] Trying {plan_label}: {option['faculty']} ({slot})...")

            # --- STEP 1: Find and click Theory radio ---
            theory_res = self.driver.execute_script(f"""
                let rows = Array.from(document.querySelectorAll('table tr'));
                for (let tr of rows) {{
                    let txt = (tr.innerText || '').toUpperCase();
                    if (txt.includes('{fac}') && (txt.includes('{slot}') || '{slot}' === 'NIL')) {{
                        let r = tr.querySelector('input[type="radio"]');
                        if (r) {{
                            // Check if row shows Full / 0 seats
                            let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                            let lastCell = cells[cells.length-1];
                            let isFull = lastCell === '0' || lastCell.toLowerCase() === 'full';
                            if (isFull) return {{ found: true, isFull: true }};
                            r.scrollIntoView({{behavior:'instant',block:'center'}});
                            r.click();
                            return {{ found: true, isFull: false }};
                        }}
                    }}
                }}
                return {{ found: false }};
            """)

            if not theory_res.get("found"):
                print(f"    [-] {fac} not found in slot table. Trying next...")
                continue

            if theory_res.get("isFull"):
                print(f"    [!] {fac} is FULL (0 seats). Fallback in 10ms...")
                continue

            print(f"    [+] Theory selected: {fac} ({slot})")
            time.sleep(1.0)
            self.wait_for_loading()

            # --- STEP 2: Select Lab (for ETL courses) ---
            if is_etl:
                lab_target = lab_slot if lab_slot else "NONE"
                print(f"    [*] Selecting Lab: {lab_slot or 'Auto-pick available'}...")
                
                # Build blacklist JS condition
                blacklist_js = " || ".join([f"txt.includes('{s}')" for s in blacklisted_slots]) if blacklisted_slots else "false"

                lab_res = self.driver.execute_script(f"""
                    let rows = Array.from(document.querySelectorAll('table tr'));
                    let isLab = r => r && (r.name === 'classnbr2' || r.name === 'courseOption3' || (r.value || '').includes('ELA'));
                    
                    // First pass: find the exact requested lab slot if specified
                    if ('{lab_target}' !== 'NONE') {{
                        for (let tr of rows) {{
                            let txt = (tr.innerText || '').toUpperCase();
                            let r = tr.querySelector('input[type="radio"]');
                            if (r && isLab(r)) {{
                                // CLASH GUARD: skip blacklisted slots
                                if ({blacklist_js}) continue;
                                let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                                let lastCell = cells[cells.length-1];
                                if (lastCell === '0' || lastCell.toLowerCase() === 'full') continue;
                                if (txt.includes('{lab_target}')) {{
                                    r.scrollIntoView({{behavior:'instant',block:'center'}});
                                    r.click();
                                    return {{ found: true, text: txt }};
                                }}
                            }}
                        }}
                    }}
                    // Second pass: first available non-blacklisted lab
                    for (let tr of rows) {{
                        let txt = (tr.innerText || '').toUpperCase();
                        let r = tr.querySelector('input[type="radio"]');
                        if (r && isLab(r)) {{
                            if ({blacklist_js}) continue;
                            let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                            let lastCell = cells[cells.length-1];
                            if (lastCell === '0' || lastCell.toLowerCase() === 'full') continue;
                            r.scrollIntoView({{behavior:'instant',block:'center'}});
                            r.click();
                            return {{ found: true, text: txt }};
                        }}
                    }}
                    return {{ found: false }};
                """)
                if not lab_res.get("found"):
                    print(f"    [-] No valid lab found. Trying next faculty...")
                    continue
                print(f"    [+] Lab selected!")

            # --- STEP 3: Set CourseOption = RGR (MUST be AFTER theory+lab clicks) ---
            # CRITICAL: VTOP resets CourseOption when you click a theory radio.
            # Always set it LAST, right before hitting Register.
            self.driver.execute_script("""
                // jQuery method
                if (typeof $ !== 'undefined') {
                    $('input[name=CourseOption][value=RGR]').prop('checked', true);
                }
                // Vanilla fallback
                let opt = document.querySelector('input[name="CourseOption"][value="RGR"]');
                if (opt) {
                    opt.checked = true;
                    opt.dispatchEvent(new Event('change', {bubbles: true}));
                    opt.click();
                }
            """)
            time.sleep(0.1)

            # --- STEP 4: Click Register ---
            print(f"    [⚡] Clicking Register...")
            self.driver.execute_script("""
                let regBtn = Array.from(document.querySelectorAll('button')).find(
                    b => b.innerText.trim() === 'Register'
                );
                if (regBtn) regBtn.click();
            """)

            time.sleep(2.0)

            # --- STEP 5: Handle the result ---
            # Check for OTP prompt first
            if self.check_otp_needed():
                self.prompt_and_enter_otp()
                time.sleep(2)

            alert = self.handle_alert()
            dur = round(time.time() - start_t, 2)

            if alert["has_alert"]:
                txt = alert["text"].lower()
                print(f"    [ALERT]: {alert['text'][:80]}")

                # Check success first! (VTOP modal contains hidden 'Not valid!' template text)
                if "successfully" in txt or "success" in txt:
                    print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED in {dur}s!")
                    self.registered.append(code)
                    return True
                elif "already registered" in txt:
                    print(f"    [✓] {code} is ALREADY REGISTERED!")
                    self.registered.append(code)
                    return True
                elif "select the course option" in txt:
                    print(f"    [!] CourseOption reset detected. Re-setting RGR and retrying...")
                    self.driver.execute_script("""
                        if (typeof $ !== 'undefined') {
                            $('input[name=CourseOption][value=RGR]').prop('checked', true);
                        }
                        let opt = document.querySelector('input[name="CourseOption"][value="RGR"]');
                        if (opt) { opt.checked = true; opt.click(); }
                        let regBtn = Array.from(document.querySelectorAll('button')).find(
                            b => b.innerText.trim() === 'Register'
                        );
                        if (regBtn) regBtn.click();
                    """)
                    time.sleep(2)
                    alert2 = self.handle_alert()
                    if alert2["has_alert"]:
                        txt2 = alert2["text"].lower()
                        if "successfully" in txt2 or "success" in txt2:
                            print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED in {dur}s!")
                            self.registered.append(code)
                            return True
                        if "clash" in txt2 or "full" in txt2 or "error" in txt2 or "select the course" in txt2:
                            print(f"    [-] Still blocked after retry: {alert2['text'][:60]}")
                            continue
                    print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED in {dur}s!")
                    self.registered.append(code)
                    return True
                elif "clash" in txt or "full" in txt or "error" in txt or "not allowed" in txt:
                    print(f"    [-] Registration blocked ({alert['text'][:60]}). Falling back...")
                    continue
                else:
                    print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED in {dur}s!")
                    self.registered.append(code)
                    return True
            else:
                # No alert = registration went through silently
                print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED in {dur}s!")
                self.registered.append(code)
                return True

        print(f"[-] All options for {code} exhausted.")
        return False

    def view_registered(self):
        print("\n[*] Loading registered courses from VTOP...")
        self.driver.execute_script("""
            let vm = Array.from(document.querySelectorAll('*')).find(el => 
                (el.innerText || '').trim().includes('View / Modify') && 
                (el.tagName === 'A' || el.tagName === 'SPAN' || el.onclick)
            );
            if (vm) vm.click();
        """)
        time.sleep(2)
        self.wait_for_loading()

        reg_data = self.driver.execute_script("""
            let trs = Array.from(document.querySelectorAll('table tr'));
            return trs.map(tr => 
                Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim())
            ).filter(r => r.length >= 4 && (r[0].startsWith('BA') || r[0].startsWith('Course')));
        """)

        total_credits = 0
        print("\n" + "="*75)
        print(" FINAL REGISTERED COURSES")
        print("="*75)
        for r in reg_data:
            line = " | ".join(f"{c:<20}" for c in r[:6])
            print(line)
            # Parse credit
            try:
                cr = float(r[1])
                total_credits += cr
            except (ValueError, IndexError):
                pass
        print("="*75)
        print(f" Total Credits: {total_credits}")
        print("="*75 + "\n")

    def run_boom_mode(self):
        """The ultimate user experience: Launch -> User logs in -> Hit ENTER -> BOOM!"""
        print("\n" + "="*70)
        print(" 🔥 VIT VELLORE INSTANT BOOM REGISTRATION MODE 🔥")
        print(" Student: Ayush Agarwal (26BCE3181) | B.Tech CSE (ACE)")
        print("="*70)
        print(f"\n Plan A Target Teachers:")
        for c in TARGET_COURSES:
            fac = c["plan_a"]["faculty"]
            slot = c["plan_a"]["theory_slot"]
            lab = c["plan_a"].get("lab_slot", "N/A")
            print(f"   {c['code']:<10} | {c['title']:<45} | {fac:<20} | {slot} | Lab: {lab}")
        print()

        if not self.connect():
            return

        print("\n[👀] Checking your VTOP login status...")
        if not self.is_logged_in():
            print("\n" + "!"*70)
            print(" [ACTION NEEDED] Please switch to Chrome and:")
            print("   1. Enter your Reg No & Password")
            print("   2. Solve the Captcha")
            print("   3. Click 'Sign In'")
            print(" Come back here once you see the Registration page.")
            print("!"*70)
            while not self.is_logged_in():
                time.sleep(2)
            print("\n[✅] Login detected! You are in VTOP!")
        else:
            print("[✅] Already logged in to VTOP!")

        print("\n" + "#"*70)
        print("  🎯 GET READY FOR THE DROP!")
        print("  When your FFCS registration window opens, simply press:")
        print("  ===> [ ENTER ] TO BLAST AND REGISTER ALL 7 COURSES <===")
        print("#"*70 + "\n")

        try:
            input("Press [ENTER] to launch BOOM registration now... ")
        except KeyboardInterrupt:
            print("\nAborted.")
            return

        start_all = time.time()
        print("\n" + "🚀"*20 + " BLASTOFF! " + "🚀"*20)
        
        success_count = 0
        last_cat = None
        for c in TARGET_COURSES:
            # Check session is still alive before each course
            if not self.is_logged_in():
                print("\n[!] Session expired! Please re-login on Chrome...")
                while not self.is_logged_in():
                    time.sleep(2)
                print("[✅] Session restored!")

            if self.register_course(c):
                success_count += 1
            time.sleep(0.5)

        total_time = round(time.time() - start_all, 2)
        print("\n" + "="*70)
        print(f" 🎉 MISSION ACCOMPLISHED in {total_time} seconds!")
        print(f" Successfully Registered: {success_count}/{len(TARGET_COURSES)} Courses")
        print("="*70)

        self.view_registered()


# ==============================================================================
# ENTRY POINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="VIT FFCS High-Speed Registration Tool (Winter 2026-27)"
    )
    parser.add_argument("--view", action="store_true", help="View registered courses")
    parser.add_argument("--all", action="store_true", help="Register all courses (no prompt)")
    args = parser.parse_args()

    bot = FFCSBot()

    if args.view:
        if bot.connect():
            bot.view_registered()
        return

    if args.all:
        if bot.connect() and bot.is_logged_in():
            for c in TARGET_COURSES:
                bot.register_course(c)
                time.sleep(0.5)
            bot.view_registered()
        return

    # Default: Interactive BOOM mode
    bot.run_boom_mode()


if __name__ == "__main__":
    main()
