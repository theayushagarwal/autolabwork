import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

COURSES_TO_CHECK = [
    {
        "code": "BAENG101",
        "name": "Technical English",
        "category": "UCC",
        "target_theory_slot": "B2+TB2",
        "target_lab_slot": "L21+L22",
        "teachers": ["SARASWATHY S", "DENISH RAJA DURAI K", "SENTHIL BABU M K"]
    },
    {
        "code": "BAMAT205",
        "name": "Discrete Mathematics",
        "category": "PCC",
        "target_theory_slot": "A2+TA2+TAA2",
        "target_lab_slot": None,
        "teachers": ["MONICA C", "REENU RANI", "TABINDA NAHID", "PARTHIBAN A", "RAJESH BHATT"]
    },
    {
        "code": "BACSE103",
        "name": "Computation Structures",
        "category": "PCC",
        "target_theory_slot": "C2+TC2",
        "target_lab_slot": "L9+L10",
        "teachers": ["PRABHU R", "ARUN DEV DHAR DWIVEDI", "VIKAS VIJAYVARGIYA"]
    },
    {
        "code": "BACSE104",
        "name": "SOOP",
        "category": "PCC",
        "target_theory_slot": "D2",
        "target_lab_slot": "L3+L4",  # or L3+L4+L19+L20
        "teachers": ["ANURADHA G", "VINILA JINNY", "GUNASEKAR M"]
    },
    {
        "code": "BACSE105",
        "name": "DSA",
        "category": "PCC",
        "target_theory_slot": "E2+TE2",
        "target_lab_slot": "L45+L46",
        "teachers": ["SUBRAMANYAM REDDY A", "SHARIEF BASHA S", "SARAVANARAJAN M C"]
    },
    {
        "code": "BAPHY105",
        "name": "Engineering Physics",
        "category": "UCC",
        "target_theory_slot": "G2+TG2",
        "target_lab_slot": "L13+L14",
        "teachers": ["PANDEY", "SAMUEL P", "SANGEM RAJESH"]
    }
]

def go_home():
    driver.execute_script("""
        let swalEl = document.querySelector('.sweet-alert, .swal2-modal');
        if (typeof swal !== 'undefined' && swal.close) { try { swal.close(); } catch(e){} }
        let overlay = document.querySelector('.sweet-overlay, .swal2-container');
        if (overlay) overlay.remove();
        let modal = document.querySelector('.sweet-alert, .swal2-modal');
        if (modal) modal.remove();
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
    time.sleep(1.2)

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

def extract_all_sections():
    return driver.execute_script("""
        let trs = Array.from(document.querySelectorAll('table tr'));
        return trs.map(tr => {
            let cells = Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim());
            let r = tr.querySelector('input[type="radio"]');
            return {
                cells: cells,
                has_radio: !!r,
                radio_name: r ? r.name : '',
                radio_val: r ? r.value : '',
                raw_text: tr.innerText.replace(/\\s+/g, ' ').trim()
            };
        }).filter(row => row.cells.length >= 4);
    """)

print("="*80)
print(" LIVE VTOP BLUEPRINT VERIFICATION (TIER 1, 2, 3)")
print("="*80)

for c in COURSES_TO_CHECK:
    code = c["code"]
    name = c["name"]
    cat = c["category"]
    print(f"\n[{code} - {name}] Checking on VTOP ({cat})...")
    
    go_home()
    select_cat(cat)
    if not open_course(code):
        print(f"  [-] Could not open {code}. Checking if already in View/Modify...")
        continue
    
    rows = extract_all_sections()
    print(f"  [+] Loaded {len(rows)} rows from VTOP.")
    
    for fac in c["teachers"]:
        fac_upper = fac.upper()
        # Find matching rows
        matching = [r for r in rows if fac_upper in r["raw_text"].upper()]
        if not matching:
            # Try partial matching on last name
            last_token = fac_upper.split()[-1] if len(fac_upper.split()) > 1 else fac_upper
            first_token = fac_upper.split()[0]
            matching = [r for r in rows if (last_token in r["raw_text"].upper() and first_token in r["raw_text"].upper()) or fac_upper in r["raw_text"].upper()]
            
        if matching:
            print(f"  * FACULTY: {fac}")
            for m in matching:
                print(f"      -> {m['raw_text']}")
        else:
            print(f"  * FACULTY: {fac} ==> [NOT FOUND IN VTOP CURRENT TABLE]")

print("\n" + "="*80)
print(" VERIFICATION COMPLETE")
print("="*80)
