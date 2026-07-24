@echo off
cd /d "%~dp0"

if not exist venv (
    echo Setting up for the first time - this may take a minute...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

python init_db.py

echo Starting scheduler - opening in browser...
timeout /t 2 /nobreak > nul
start http://127.0.0.1:5001
python app.py
pause
