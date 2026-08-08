import os

lines = [
    "@echo off",
    "cd /d \"%~dp0\"",
    "timeout /t 2 /nobreak > nul",
    "start http://127.0.0.1:5001",
    "NanaScheduler.exe",
    "pause",
]

path = os.path.join("dist", "NanaScheduler", "start.bat")
with open(path, "w") as f:
    f.write("\r\n".join(lines))
print(f"Created {path}")
