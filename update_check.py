import urllib.request
import json
import webbrowser
from tkinter import messagebox

def normalize_version(v):
    """Convert version string like '1.0.1' → tuple of ints (1, 0, 1)."""
    try:
        return tuple(map(int, v.strip().split(".")))
    except ValueError:
        return (0,)

def check_for_update(current_version):
    # 🔗 Use your Pro update file here
    url = "https://thinkzone18.github.io/SmartCOPY-update/pro/version.json"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
            latest = data.get("latest_version", "").strip()
            download_url = data.get("download_url", "")
            notes = data.get("notes", "")

            current_tuple = normalize_version(current_version)
            latest_tuple = normalize_version(latest)

            if latest_tuple > current_tuple:
                msg = (
                    f"A new version of SmartCOPY (v{latest}) is available!\n\n"
                    f"Would you like to open the download page now?"
                )
                if messagebox.askyesno("SmartCOPY Update Available", msg):
                    webbrowser.open(download_url)
            # else: you can quietly skip if up-to-date
    except Exception:
        # Silently ignore update check failures (for offline use)
        pass
