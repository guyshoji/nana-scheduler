import os

dist_path = os.path.join("dist", "NanaScheduler")

if not os.path.exists(dist_path):
    print(f"Directory {dist_path} not found. Contents of dist/:")
    if os.path.exists("dist"):
        for item in os.listdir("dist"):
            print(f"  {item}")
    else:
        print("  dist/ folder does not exist at all")
    raise FileNotFoundError(f"PyInstaller output not found at {dist_path}")

lines = [
    "@echo off",
    "cd /d \"%~dp0\"",
    "timeout /t 2 /nobreak > nul",
    "start http://127.0.0.1:5001",
    "NanaScheduler.exe",
    "pause",
]

path = os.path.join(dist_path, "start.bat")
with open(path, "w") as f:
    f.write("\r\n".join(lines))
print(f"Created {path}")
