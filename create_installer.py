"""Builder script that compresses the JARVIS build and creates JarvisSetup.exe."""

import os
import sys
import zipfile
import subprocess
import shutil

# Paths
DIST_DIR = os.path.join("dist", "Jarvis")
ZIP_PATH = os.path.join("dist", "app.zip")
PAYLOAD_PY = os.path.join("dist", "installer_payload.py")
SETUP_EXE = os.path.join("dist", "JarvisSetup.exe")


def compress_build(src_dir, dest_zip):
    print(f"Compressing application build from {src_dir} to {dest_zip}...")
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, src_dir)
                zipf.write(abs_path, rel_path)
    print("Compression complete!")


def generate_installer_payload(zip_path, payload_path):
    print("Generating installer script payload...")
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    # Generate Python script that embeds these bytes
    script_content = f"""# Embedded zip bytes and extraction logic
import os
import sys
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox
import win32com.client

ZIP_DATA = {repr(zip_bytes)}

def install_app():
    try:
        install_dir = os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\Jarvis")
        os.makedirs(install_dir, exist_ok=True)
        
        # Write zip to temp file
        temp_zip = os.path.join(install_dir, "temp.zip")
        with open(temp_zip, "wb") as f:
            f.write(ZIP_DATA)
            
        # Extract files
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(install_dir)
            
        os.remove(temp_zip)
        
        # Create shortcuts
        desktop_dir = os.path.expandvars(r"%USERPROFILE%\\Desktop")
        desktop_shortcut = os.path.join(desktop_dir, "JARVIS.lnk")
        target = os.path.join(install_dir, "Jarvis.exe")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        
        # Desktop shortcut
        shortcut = shell.CreateShortCut(desktop_shortcut)
        shortcut.TargetPath = target
        shortcut.WorkingDirectory = install_dir
        shortcut.Description = "JARVIS - Digital Chief of Staff"
        shortcut.Save()
        
        # Start Menu shortcut
        start_menu_dir = os.path.expandvars(r"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs")
        os.makedirs(start_menu_dir, exist_ok=True)
        start_shortcut = os.path.join(start_menu_dir, "JARVIS.lnk")
        
        shortcut = shell.CreateShortCut(start_shortcut)
        shortcut.TargetPath = target
        shortcut.WorkingDirectory = install_dir
        shortcut.Description = "JARVIS - Digital Chief of Staff"
        shortcut.Save()
        
        return True
    except Exception as e:
        print("Installation failed:", e)
        return str(e)

def run_gui():
    root = tk.Tk()
    root.title("JARVIS Setup")
    root.geometry("400x200")
    root.configure(bg="#0a192f")
    root.overrideredirect(True) # Borderless
    
    # Center
    w, h = 420, 200
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2
    root.geometry(f"{{w}}x{{h}}+{{x}}+{{y}}")
    
    # Border
    b = tk.Frame(root, bg="#00f2fe", bd=1)
    b.pack(fill="both", expand=True)
    
    inner = tk.Frame(b, bg="#0a192f")
    inner.pack(fill="both", expand=True, padx=2, pady=2)
    
    tk.Label(inner, text="JARVIS Installation", bg="#0a192f", fg="#00f2fe", font=("Consolas", 18, "bold")).pack(pady=(20, 10))
    lbl_status = tk.Label(inner, text="Installing JARVIS to AppData...", bg="#0a192f", fg="#8892b0", font=("Consolas", 10))
    lbl_status.pack(pady=5)
    
    progress = ttk.Progressbar(inner, mode="indeterminate", length=300)
    progress.pack(pady=10)
    progress.start()
    
    def start_install():
        res = install_app()
        progress.stop()
        if res is True:
            messagebox.showinfo("JARVIS Setup", "Installation completed successfully! Shortcut created on Desktop.")
        else:
            messagebox.showerror("JARVIS Setup", f"Installation failed: {{res}}")
        root.destroy()
        
    root.after(1000, start_install)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
"""
    with open(payload_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    print("Installer script generated at:", payload_path)


def compile_installer():
    print("Compiling installer payload into standalone setup executable...")
    pyi_path = os.path.join(
        os.path.dirname(sys.executable), "Scripts", "pyinstaller.exe"
    )
    if not os.path.exists(pyi_path):
        pyi_path = "pyinstaller"

    cmd = [
        pyi_path,
        "--onefile",
        "--noconsole",
        "--name=JarvisSetup",
        "--clean",
        PAYLOAD_PY,
    ]
    subprocess.run(cmd, check=True)
    print("Installer built successfully! JarvisSetup.exe is in 'dist/JarvisSetup.exe'.")


if __name__ == "__main__":
    if not os.path.exists(DIST_DIR):
        print(f"Error: Build folder {DIST_DIR} not found. Build executable first.")
        sys.exit(1)

    # Ensure dist folder exists
    os.makedirs("dist", exist_ok=True)

    # Step 1: Compress the compiled folder
    compress_build(DIST_DIR, ZIP_PATH)

    # Step 2: Write installer script payload
    generate_installer_payload(ZIP_PATH, PAYLOAD_PY)

    # Step 3: Compile installer script to standalone setup.exe
    compile_installer()
