# 🚀 VIT FFCS Instant Registration Bot — Quick-Start Guide
> **Student Manual & Fail-Safe Protocol for Winter Semester 2026–27**  
> *Keep this guide open on your phone or printed on your desk during FFCS.*

---

## 📋 Phase 1: One-Time Setup (Do This the Night Before)

### 1. Requirements Check
Make sure your Windows laptop has:
1. **Google Chrome** installed.
2. **Python 3.10 or newer** installed.
   * *Crucial check during install:* Ensure **`☑ Add python.exe to PATH`** was checked!

### 2. Install Selenium (Single Command)
Open **Command Prompt (CMD)** or **PowerShell** and run:
```cmd
pip install selenium
```
*(No other libraries needed — everything else uses standard built-in Python).*

---

## ⚙️ Phase 2: Customize Your Target Courses (If Needed)

The bot comes pre-configured with Ayush's zero-clash blueprint. If you want **different teachers or different courses**:
1. Right-click [`fast_ffcs_register.py`](file:///c:/Users/ayush/Downloads/files%20(5)/fast_ffcs_register.py) $\rightarrow$ **Open with Notepad** (or VS Code).
2. Go down to **Line 56**: `TARGET_COURSES = [...]`.
3. Change the `"faculty"` and `"theory_slot"` / `"lab_slot"` to your desired professors.
4. Save the file (`Ctrl + S`).

---

## ⏰ Phase 3: FFCS Morning Timeline (Minute-by-Minute)

```
 [ 10-15 Mins Before ] ──> Run vtop.bat & Log into VTOP Chrome
 [ 5 Mins Before ]     ──> Run LAUNCH_FFCS_BOOM.bat & Wait at [ENTER] prompt
 [ 10:00:00 AM SHARP ] ──> HIT [ ENTER ] & Watch it Blast!
 [ +30 Seconds ]       ──> 7/7 Registered or Switch to Manual Slot Filter
```

---

### Step 1: 10–15 Minutes Before Drop (e.g. 9:45 AM)
1. Double-click:
   ```cmd
   vtop.bat
   ```
2. A special Google Chrome window will open.
3. In that window:
   - Enter your **Registration Number** & **Password**.
   - Solve the **Captcha**.
   - Click **Sign In**.
   - Navigate to the **FFCS Registration Page**.
4. 📱 **Open your VIT student email on your phone screen now** (in case VTOP triggers an Email OTP).

---

### Step 2: 5 Minutes Before Drop (e.g. 9:55 AM)
1. Double-click:
   ```cmd
   LAUNCH_FFCS_BOOM.bat
   ```
2. The bot will connect to your open Chrome session and display:
   ```text
   [✅] Already logged in to VTOP!
   
   ######################################################################
     🎯 GET READY FOR THE DROP!
     When your FFCS registration window opens, simply press:
     ===> [ ENTER ] TO BLAST AND REGISTER ALL 7 COURSES <===
   ######################################################################
   
   Press [ENTER] to launch BOOM registration now...
   ```
3. 🛑 **STOP! DO NOT PRESS ENTER YET!**  
   Leave this terminal sitting right here on your screen.

---

### Step 3: EXACTLY When Registration Opens (10:00:00 AM Sharp)
1. The very second your registration time hits:
   👉 **HIT `[ENTER]` ON YOUR KEYBOARD!**
2. The bot will automatically:
   - Register **Technical English & India Studies first** (unlocking Programme Core).
   - Register **Discrete Math, Comp Struct, DSA, SOOP, and Physics** in milliseconds.
   - Automatically fall back to Plan B/C if a section fills up.
   - Automatically handle VTOP's SweetAlert popups.

---

## 🔍 Phase 4: Understanding Terminal Signals

| Signal in Terminal | What It Means | What You Should Do |
| :--- | :--- | :--- |
| **`[💥 BOOM!] BACSE105 (SUBRAMANYAM) REGISTERED in 1.8s!`** | Course is 100% secured on VTOP! | Relax, let the bot move to the next course. |
| **`[!] Dr. Monica C is FULL. Fallback in 10ms...`** | Primary teacher ran out of seats. | Nothing! Bot instantly pivots to your Tier-2 teacher on the exact same slot. |
| **`[🔑 OTP REQUIRED] Enter the 5-character OTP here:`** | VTOP triggered email security check. | Check your phone's email inbox immediately, type the 5 letters into terminal, hit `[ENTER]`. |
| **`[!] Session timeout detected!`** | VTOP logged you out due to server load. | Quickly switch to Chrome, re-enter password + captcha, bot resumes automatically. |

---

## 🛡️ Phase 5: The 30-Second Golden Rule (Manual Fallback)

If after **20–30 seconds** the bot is stuck or VTOP's servers crash the automation:
1. **Close the terminal window.**
2. Switch directly to your open Chrome window.
3. Use the **Slot-Filter Protocol**:
   * Register **BAENG101** first to unlock the rest of the courses.
   * Open each course and **type the slot in the search bar** (`E2` for DSA, `C2` for Comp Struct, `D2` for SOOP, `A2` for Math, `G2` for Physics).
   * Click your Tier 1 or Tier 2 teacher.
   * **Verify the `RGR` radio button is checked** right above the Register button.
   * Click **Register**!

---

### 🏁 Summary Checklist
- [ ] Python + Selenium installed (`pip install selenium`).
- [ ] VIT Email open on phone.
- [ ] Chrome opened via `vtop.bat` and logged into VTOP.
- [ ] `LAUNCH_FFCS_BOOM.bat` opened and waiting at `Press [ENTER]`.
- [ ] Hit `[ENTER]` the second the clock strikes 10:00:00 AM!
