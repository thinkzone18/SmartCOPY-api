import json, os, sys, webbrowser, hashlib, requests
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, Tk, simpledialog

APP_NAME = "SmartCOPY"
APP_DIR = Path(os.getenv("APPDATA", "")) / APP_NAME
TRIAL_FILE = APP_DIR / "trial.json"
LICENSE_FILE = APP_DIR / "license.json"

MONGO_API_URL = "http://127.0.0.1:8000/validate"  # Update to hosted FastAPI URL later
UPGRADE_URL = "https://thinkzone18.gumroad.com/l/smartcopy-pro"

def show_message(title, text, exit_app=False, upgrade=False):
    root = Tk(); root.withdraw()
    messagebox.showinfo(title, text)
    root.destroy()
    if upgrade:
        webbrowser.open(UPGRADE_URL)
    if exit_app:
        sys.exit(0)

def ask_license_key():
    root = Tk(); root.withdraw()
    key = simpledialog.askstring(APP_NAME + " Activation", "Enter your Pro license key:")
    root.destroy()
    return key

def save_license(data):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f)

def load_license():
    if LICENSE_FILE.exists():
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)
    return None

def verify_with_server(key):
    try:
        res = requests.post(MONGO_API_URL, json={"license_key": key}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("valid"):
                return True, data.get("expiry")
            else:
                return False, data.get("message")
    except Exception:
        return None, "Connection error"
    return False, "Invalid license"

def check_license():
    lic = load_license()
    if lic and lic.get("type") == "pro":
        expiry = datetime.strptime(lic["expiry"], "%Y-%m-%d").date()
        if datetime.now().date() <= expiry:
            show_message(APP_NAME, f"✅ Pro license active\nValid until {expiry}")
            return True
        else:
            show_message(APP_NAME, "⚠️ License expired. Please renew.", exit_app=True, upgrade=True)
            return False

    choice = messagebox.askquestion(APP_NAME, "Do you have a Pro license key?\nYes = Enter key\nNo = Start 7-day trial")
    if choice == "yes":
        return activate_license()
    else:
        return check_trial()

def activate_license():
    key = ask_license_key()
    if not key:
        show_message(APP_NAME, "No key entered."); return False
    valid, info = verify_with_server(key)
    if valid:
        save_license({"type": "pro", "key": hashlib.sha256(key.encode()).hexdigest(), "expiry": info})
        show_message(APP_NAME, f"✅ License activated!\nValid until {info}")
        return True
    elif valid is None:
        show_message(APP_NAME, "⚠️ Could not reach server. Check internet.")
        return False
    else:
        show_message(APP_NAME, f"❌ Invalid license: {info}")
        return False

def check_trial():
    os.makedirs(APP_DIR, exist_ok=True)
    if not TRIAL_FILE.exists():
        with open(TRIAL_FILE, "w") as f:
            json.dump({"start": datetime.now().strftime("%Y-%m-%d")}, f)
        show_message(APP_NAME, "🎉 7-day SmartCOPY trial started!")
        return True

    with open(TRIAL_FILE, "r") as f:
        data = json.load(f)
    start = datetime.strptime(data["start"], "%Y-%m-%d")
    days = (datetime.now() - start).days
    if days >= 7:
        if messagebox.askyesno(APP_NAME, "Trial expired. Activate Pro now?"):
            return activate_license()
        show_message(APP_NAME, "Trial expired. Please upgrade.", exit_app=True, upgrade=True)
        return False
    show_message(APP_NAME, f"Trial active — {7 - days} day(s) left.")
    return True
