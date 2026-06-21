"""Build script for JARVIS native executable using PyInstaller."""

import subprocess
import os
import sys

# Define path to the installed pyinstaller.exe in python installation scripts folder
pyi_path = os.path.join(
    os.path.dirname(sys.executable), "Scripts", "pyinstaller.exe"
)
if not os.path.exists(pyi_path):
    pyi_path = "pyinstaller"  # Fallback to environment PATH lookup

cmd = [
    pyi_path,
    "--noconsole",
    "--name=Jarvis",
    "--clean",
    "--add-data=assets;assets",
    "--add-data=plugins;plugins",
    "--add-data=skills;skills",
    "--add-data=tools;tools",
    "main.py",
]

print(f"Executing PyInstaller: {' '.join(cmd)}")
try:
    subprocess.run(cmd, check=True)
    print("Build successful! Executable located in 'dist/Jarvis/Jarvis.exe'.")
except subprocess.CalledProcessError as e:
    print(f"Error during compilation: {e}")
    sys.exit(1)
