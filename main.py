import os
import sys
import shutil
import time
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
import importlib.util
import signal
import sys

# ------------------------------------------------------------
# PyInstaller hidden-import helpers (ensures modules are bundled)
# ------------------------------------------------------------
import license_check  # noqa: F401
import update_check   # noqa: F401

def handle_interrupt(sig, frame):
    print("\n🛑  Keyboard interrupt detected. Exiting gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

# ============================================================
# ✅ 1️⃣ App constants
# ============================================================
APP_NAME = "SmartCOPY"
APP_VERSION = "1.0"
APP_PUBLISHER = "ThinkZone"
APPDATA_DIR = Path.home() / "AppData" / "Roaming" / "SmartCOPY"

# ============================================================
# ✅ 2️⃣ Import helper (for license_check.py & update_check.py)
# ============================================================
def import_module_safely(module_name, filename):
    """Import module safely — works both in source and PyInstaller bundle."""
    import importlib.util, sys, os
    try:
        if module_name in sys.modules:
            return sys.modules[module_name]

        try:
            return importlib.import_module(module_name)
        except ImportError:
            pass

        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        module_path = os.path.join(base_path, filename)

        if not os.path.exists(module_path):
            if os.path.exists(module_path + "c"):
                module_path = module_path + "c"
            else:
                print(f"⚠️ Missing file: {module_path}")
                return None

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return None

# ============================================================
# ✅ 3️⃣ License + Update Validation
# ============================================================
license_check = import_module_safely("license_check", "license_check.py")
update_check  = import_module_safely("update_check",  "update_check.py")

# --- License Validation ---
if license_check and hasattr(license_check, "check_license"):
    try:
        # 🔑 full trial + pro check logic
        valid = license_check.check_license()
        if not valid:
            sys.exit(0)
    except Exception as e:
        messagebox.showerror(APP_NAME, f"License check failed: {e}")
        sys.exit(1)
else:
    messagebox.showerror(APP_NAME, "License verification module missing or invalid.")
    sys.exit(1)

# --- Update Check (optional) ---
if update_check and hasattr(update_check, "check_for_update"):
    try:
        update_check.check_for_update(APP_VERSION)
    except Exception as e:
        print(f"⚠️ Update check failed: {e}")
else:
    print("⚠️ Update check skipped (module missing).")

# ============================================================
# ✅ 4️⃣ CORE LOGIC
# ============================================================
def copy_updated_files(source_folder, destination_folder, file_extensions, output_box, progress_bar, status_label):
    start_time = time.time()
    copied_files = []
    skipped_files = []
    total_files = 0

    for root, _, files in os.walk(source_folder):
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in file_extensions):
                total_files += 1

    if total_files == 0:
        messagebox.showinfo("No Files", "No files found with the selected extensions.")
        return

    progress_bar["maximum"] = total_files
    progress_bar["value"] = 0

    os.makedirs(destination_folder, exist_ok=True)
    count = 0
    for root, _, files in os.walk(source_folder):
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in file_extensions):
                source_path = os.path.join(root, file)
                rel_path = os.path.relpath(source_path, source_folder)
                dest_path = os.path.join(destination_folder, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if os.path.exists(dest_path):
                    src_mtime = os.path.getmtime(source_path)
                    dest_mtime = os.path.getmtime(dest_path)
                    if src_mtime > dest_mtime:
                        shutil.copy2(source_path, dest_path)
                        copied_files.append(rel_path)
                    else:
                        skipped_files.append(rel_path)
                else:
                    shutil.copy2(source_path, dest_path)
                    copied_files.append(rel_path)

                count += 1
                progress_bar["value"] = count
                status_label.config(text=f"Processing: {count}/{total_files} files")
                root_window.update_idletasks()

    elapsed = time.time() - start_time

    output_box.config(state="normal")
    output_box.delete(1.0, tk.END)
    output_box.insert(tk.END, f"=== COPY SUMMARY ===\n")
    output_box.insert(tk.END, f"Copied: {len(copied_files)}\n")
    output_box.insert(tk.END, f"Skipped: {len(skipped_files)}\n")
    output_box.insert(tk.END, f"Elapsed Time: {elapsed:.2f} seconds\n\n")

    if copied_files:
        output_box.insert(tk.END, "Copied Files:\n")
        for f in copied_files:
            output_box.insert(tk.END, f"  + {f}\n")

    if skipped_files:
        output_box.insert(tk.END, "\nSkipped Files:\n")
        for f in skipped_files:
            output_box.insert(tk.END, f"  - {f}\n")

    output_box.config(state="disabled")
    progress_bar["value"] = total_files
    status_label.config(text="✅ Operation Completed Successfully")
    messagebox.showinfo("Success", f"Copied: {len(copied_files)}, Skipped: {len(skipped_files)}")

# ============================================================
# ✅ 5️⃣ UI LOGIC
# ============================================================
def browse_source():
    folder = filedialog.askdirectory(title="Select Source Folder")
    if folder:
        source_entry.delete(0, tk.END)
        source_entry.insert(0, folder)

def browse_destination():
    folder = filedialog.askdirectory(title="Select Destination Folder")
    if folder:
        dest_entry.delete(0, tk.END)
        dest_entry.insert(0, folder)

def select_all():
    for var in ext_vars.values():
        var.set(1)

def deselect_all():
    for var in ext_vars.values():
        var.set(0)

def start_copy():
    source = source_entry.get().strip()
    destination = dest_entry.get().strip()
    if not source or not destination:
        messagebox.showerror("Error", "Please select both source and destination folders.")
        return

    selected_extensions = [ext for ext, var in ext_vars.items() if var.get() == 1]
    custom_exts = custom_entry.get().strip()

    if custom_exts:
        for ext in custom_exts.split(","):
            e = ext.strip()
            if e:
                if not e.startswith("."):
                    e = "." + e
                selected_extensions.append(e)

    if not selected_extensions:
        messagebox.showerror("Error", "Please select or enter at least one file extension.")
        return

    status_label.config(text="Copying files...")
    copy_updated_files(source, destination, selected_extensions, output_box, progress_bar, status_label)

# ============================================================
# ✅ 6️⃣ UI DESIGN
# ============================================================
root_window = tk.Tk()
root_window.title("🔷 SmartCOPY")
root_window.geometry("700x775")
root_window.configure(bg="#f0f4f7")

style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
style.configure("TLabel", background="#f0f4f7", font=("Segoe UI", 10))
style.configure("TProgressbar", thickness=18, troughcolor="#e0e0e0", background="#0078D7")

header_frame = tk.Frame(root_window, bg="#0078D7")
header_frame.pack(fill="x")
tk.Label(header_frame, text="📂 SmartCOPY Edition", bg="#0078D7", fg="white",
         font=("Segoe UI", 12, "bold"), pady=5).pack()

frame_main = tk.Frame(root_window, bg="#f0f4f7")
frame_main.pack(pady=10)

def labeled_entry(parent, label_text, browse_func):
    frame = tk.Frame(parent, bg="#f0f4f7")
    tk.Label(frame, text=label_text, font=("Segoe UI", 10, "bold"), bg="#f0f4f7").pack(anchor="w")
    entry = tk.Entry(frame, width=90)
    entry.pack(side="left", padx=5, pady=5)
    ttk.Button(frame, text="Browse", command=browse_func).pack(side="left", padx=5)
    frame.pack(pady=5)
    return entry

source_entry = labeled_entry(frame_main, "Source Folder:", browse_source)
dest_entry = labeled_entry(frame_main, "Destination Folder:", browse_destination)

# --- Extensions ---
categories = {
    "Documents": [".txt", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".md"],
    "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "Presentations": [".ppt", ".pptx", ".odp"],
    "Code / Web": [".py", ".java", ".js", ".ts", ".html", ".css", ".php", ".json", ".xml", ".yml", ".yaml", ".sh", ".bat", ".c", ".cpp", ".h"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".ico", ".psd"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma"],
    "Video": [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".webm"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".xz", ".iso", ".bz2"],
    "Database": [".db", ".sqlite", ".sql", ".mdb", ".accdb"],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
    "Config / Logs": [".ini", ".cfg", ".conf", ".log", ".bak", ".tmp"],
}

tk.Label(root_window, text="Select File Extensions:", font=("Segoe UI", 11, "bold"), bg="#f0f4f7").pack(pady=(8, 0))

canvas = tk.Canvas(root_window, height=10, bg="white", bd=0, highlightthickness=5, highlightbackground="#ccc")
scrollbar = ttk.Scrollbar(root_window, orient="vertical", command=canvas.yview)
scroll_frame = tk.Frame(canvas, bg="white")

scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=4)
scrollbar.pack(side="right", fill="y")

ext_vars = {}
for cat, exts in categories.items():
    tk.Label(scroll_frame, text=f"📁 {cat}", font=("Segoe UI", 10, "bold"), bg="white", fg="#0078D7").pack(anchor="w", pady=(5, 0))
    cat_frame = tk.Frame(scroll_frame, bg="white")
    cat_frame.pack(anchor="w", padx=6)
    for i, ext in enumerate(exts):
        var = tk.IntVar()
        ext_vars[ext] = var
        tk.Checkbutton(cat_frame, text=ext, variable=var, bg="white").grid(row=i // 7, column=i % 7, sticky="w", padx=1, pady=1)

btn_frame = tk.Frame(root_window, bg="#f0f4f7")
btn_frame.pack(pady=10)
ttk.Button(btn_frame, text="Select All", command=select_all).pack(side="left", padx=10)
ttk.Button(btn_frame, text="Deselect All", command=deselect_all).pack(side="left", padx=10)

tk.Label(root_window, text="Add Custom Extensions (comma-separated):", font=("Segoe UI", 10, "bold"), bg="#f0f4f7").pack(pady=(10, 0))
custom_entry = tk.Entry(root_window, width=80)
custom_entry.pack(pady=5)
custom_entry.insert(0, ".ini, .bak, .xyz")

ttk.Button(root_window, text="🚀 Start Copy", command=start_copy).pack(pady=10)
progress_bar = ttk.Progressbar(root_window, length=700, mode="determinate")
progress_bar.pack(pady=5)
status_label = tk.Label(root_window, text="Ready", bg="#f0f4f7", font=("Segoe UI", 9, "italic"), fg="#555")
status_label.pack()

tk.Label(root_window, text="Results:", font=("Segoe UI", 11, "bold"), bg="#f0f4f7").pack(pady=(5, 0))
output_box = scrolledtext.ScrolledText(root_window, width=110, height=16, state="disabled", wrap="word", font=("Consolas", 9))
output_box.pack(padx=20, pady=5)

status_bar = tk.Label(root_window, text="Developed by ThinkZone © 2025. All rights reserved.", bg="#0078D7", fg="white", anchor="center", font=("Segoe UI", 9))
status_bar.pack(fill="x", pady=(10, 0))

root_window.mainloop()
