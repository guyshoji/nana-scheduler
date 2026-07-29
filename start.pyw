import subprocess
import sys
import os
import webbrowser
import time
import venv

# Change to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

VENV_DIR = "venv"
PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")

# Create venv if needed
if not os.path.exists(VENV_DIR):
    print("Setting up for the first time...")
    venv.create(VENV_DIR, with_pip=True)
    subprocess.run([PIP, "install", "-r", "requirements.txt"], check=True)

# Initialize DB if needed
subprocess.run([PYTHON, "init_db.py"], check=True)

# Open browser after short delay
time.sleep(2)
webbrowser.open("http://127.0.0.1:5001")

# Start Flask
subprocess.run([PYTHON, "app.py"])