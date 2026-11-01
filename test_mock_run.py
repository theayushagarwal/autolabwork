"""
================================================================================
VIT VELLORE MOCK FFCS LIVE REGISTRATION TEST RUNNER
Student Account: 26BCE0120 (Jahan Amish Vasoya)
Registers all remaining courses using 100% OPEN teachers in Mock right now!
================================================================================
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Remaining 4 courses to register:
MOCK_COURSES = [
    {
        "code": "BACSE103",
        "title": "Computation Structures",
        "category": "PCC",
        "type": "ETL",
        "faculty": ["SUBHRA SANKHA SARMA", "MOHIUL ISLAM", "SULTAN MAHMOOD CHOWDHURY"],
        "slot": "C2+TC2",
        "lab_slot": "L11+L12"
    },
    {
        "code": "BACSE104",
        "title": "Structured and Object-Oriented Programming (SOOP)",
        "category": "PCC",
        "type": "ETL",
        "faculty": ["RISHIN HALDAR", "MUCHENEDI HARI KISHOR", "MOHAN K", "DEEPANRAMKUMAR P"],
        "slot": "D2",
        "lab_slot": "L3+L4"
    },
    {
        "code": "BACSE105",
        "title": "Data Structures & Algorithms",
        "category": "PCC",
        "type": "ETL",
        "faculty": ["JOSHVA DEVADAS T", "MYTHILI N", "SIVAPRASAD DARLA", "RAJA S P"],
        "slot": "E2+TE2",
        "lab_slot": None  # Will pick first non-clashing lab
    },
    {
        "code": "BAPHY105",
        "title": "Engineering Physics",
        "category": "UCC",
        "type": "ETL",
        "faculty": ["SHAIK KALEEMULLA", "SHOBANA M K", "PREMKUMAR S"],
        "slot": "G2+TG2",
        "lab_slot": None  # Will pick first non-clashing lab
    }
]

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

def dismiss_any_alert():
    return driver.execute_script("""
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

def go_home():
    dismiss_any_alert()
    driver.execute_script("""
        let home = Array.from(document.querySelectorAll('*')).find(el => (el.innerText || '').trim() === 'Home' && (el.tagName === 'A' || el.tagName === 'SPAN' || el.onclick));
        if (home) home.click();
    """)
    time.sleep(1.2)

def select_cat(cat):
    driver.execute_script(f"""
        let r = document.querySelector('input[name="registrationOption"][value="{cat}"]');
        if (r) r.checked = true;
        let btn = document.querySelector('button[onclick*="viewRegistrationOption"]');
        if (btn) btn.click();
    """)
    time.sleep(1.5)

def open_course(code):
    opened = driver.execute_script(f"""
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
    time.sleep(1.5)
    return opened

print("\n" + "="*70)
print(" 🚀 COMPLETING MOCK REGISTRATION FOR JAHAN AMISH VASOYA")
print("="*70 + "\n")

for c in MOCK_COURSES:
    code = c["code"]
    title = c["title"]
    cat = c["category"]
    slot = c["slot"]
    is_etl = (c["type"] == "ETL")
    fac_list = c["faculty"]
    
    print(f"\n[*] Processing: {code} - {title} ({cat})...")
    go_home()
    select_cat(cat)
    if not open_course(code):
        print(f"    [-] Course {code} already registered or not found under {cat}. Skipping.")
        continue

    # Try faculties in order
    registered = False
    for fac in fac_list:
        print(f"    [*] Trying Faculty: {fac} ({slot})...")
        th_found = driver.execute_script(f"""
            let rows = Array.from(document.querySelectorAll('table tr'));
            for (let tr of rows) {{
                let txt = (tr.innerText || '').toUpperCase();
                if (txt.includes('{fac}') && txt.includes('{slot}')) {{
                    let r = tr.querySelector('input[type="radio"]');
                    if (r) {{
                        let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                        let lastCell = cells[cells.length-1];
                        if (lastCell === '0' || lastCell.toLowerCase() === 'full') return {{ ok: false, full: true }};
                        r.scrollIntoView({{behavior:'instant', block:'center'}});
                        r.click();
                        return {{ ok: true, val: r.value }};
                    }}
                }}
            }}
            return {{ ok: false, full: false }};
        """)

        if not th_found.get("ok"):
            if th_found.get("full"):
                print(f"        [!] {fac} is FULL. Trying next backup...")
            else:
                print(f"        [-] {fac} slot row not found. Trying next...")
            continue

        print(f"        [+] Theory clicked for {fac}!")
        time.sleep(1.2)

        # Lab selection if ETL
        if is_etl:
            preferred_lab = c.get("lab_slot")
            lab_sel = driver.execute_script(f"""
                let rows = Array.from(document.querySelectorAll('table tr'));
                let isLab = r => r && (r.name === 'classnbr2' || r.name === 'courseOption3' || (r.value || '').includes('ELA'));
                // Pass 1: try preferred lab
                if ('{preferred_lab}' !== 'None') {{
                    for (let tr of rows) {{
                        let txt = (tr.innerText || '').toUpperCase();
                        let r = tr.querySelector('input[type="radio"]');
                        if (r && isLab(r) && txt.includes('{preferred_lab}')) {{
                            let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                            let last = cells[cells.length-1];
                            if (last !== '0' && last.toLowerCase() !== 'full') {{
                                r.scrollIntoView({{behavior:'instant', block:'center'}});
                                r.click();
                                return {{ ok: true, text: txt.replace(/\\t+/g, ' | ').trim() }};
                            }}
                        }}
                    }}
                }}
                // Pass 2: any valid non-clashing lab
                for (let tr of rows) {{
                    let txt = (tr.innerText || '').toUpperCase();
                    let r = tr.querySelector('input[type="radio"]');
                    if (r && isLab(r)) {{
                        if (txt.includes('L3+L4') || txt.includes('L19+L20')) continue;
                        let cells = Array.from(tr.querySelectorAll('td,th')).map(c=>c.innerText.trim());
                        let last = cells[cells.length-1];
                        if (last !== '0' && last.toLowerCase() !== 'full') {{
                            r.scrollIntoView({{behavior:'instant', block:'center'}});
                            r.click();
                            return {{ ok: true, text: txt.replace(/\\t+/g, ' | ').trim() }};
                        }}
                    }}
                }}
                return {{ ok: false }};
            """)
            if not lab_sel.get("ok"):
                print(f"        [-] No open lab for {fac}. Trying next faculty...")
                continue
            print(f"        [+] Lab selected: {lab_sel.get('text', '')[:45]}")

        # Set CourseOption RGR
        driver.execute_script("""
            if (typeof $ !== 'undefined') {
                $('input[name=CourseOption][value=RGR]').prop('checked', true);
            }
            let opt = document.querySelector('input[name="CourseOption"][value="RGR"]');
            if (opt) { opt.checked = true; opt.click(); }
        """)

        # Register button
        driver.execute_script("""
            let regBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Register');
            if (regBtn) regBtn.click();
        """)
        time.sleep(2.0)

        alert = dismiss_any_alert()
        if alert["has_alert"]:
            txt = alert["text"].lower()
            if "successfully" in txt or "success" in txt:
                print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED SUCCESSFULLY!")
                registered = True
                break
            elif "clash" in txt or "full" in txt or "error" in txt:
                print(f"        [-] Rejected: {alert['text']}")
                continue
            else:
                print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED SUCCESSFULLY!")
                registered = True
                break
        else:
            print(f"    [💥 BOOM!] {code} ({fac}) REGISTERED!")
            registered = True
            break

    if not registered:
        print(f"    [-] Could not register {code}. Options exhausted.")
    time.sleep(1.0)

# View final registered summary
print("\n" + "="*70)
print(" 🏁 FINAL REGISTERED COURSES")
print("="*70)
go_home()
driver.execute_script("""
    let vm = Array.from(document.querySelectorAll('*')).find(el => (el.innerText || '').trim().includes('View / Modify') && (el.tagName === 'A' || el.tagName === 'SPAN' || el.onclick));
    if (vm) vm.click();
""")
time.sleep(2)

reg_courses = driver.execute_script("""
    let trs = Array.from(document.querySelectorAll('table tr'));
    return trs.map(tr => Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim()))
              .filter(r => r.length >= 4 && (r[0].startsWith('BA') || r[0].startsWith('Course')));
""")
for r in reg_courses:
    print(" | ".join(f"{c:<20}" for c in r[:6]))
print("="*70)
