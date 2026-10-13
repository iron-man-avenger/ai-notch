import os
import sys
import subprocess
import shutil

def build():
    print("=" * 60)
    print("[*] Building AI Assistant Desktop Executable (.exe)")
    print("=" * 60)

    # 1. Verify frontend dist exists
    frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
    if not os.path.exists(frontend_dist):
        print("[*] Building React frontend first...")
        subprocess.run(["npm", "run", "build"], cwd=os.path.join(os.path.dirname(__file__), "frontend"), check=True, shell=True)

    # 2. PyInstaller Command
    # We include:
    # - frontend/dist -> frontend/dist
    # - core package
    # - app icon
    # - noconsole (frameless desktop dock)
    icon_arg = []
    if os.path.exists("app_icon.ico"):
        icon_arg = ["--icon", "app_icon.ico"]

    add_data_delim = ";" if sys.platform.startswith("win") else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--name", "AssistantDock",
        "--onedir",
        "--clean",
        "--add-data", f"frontend/dist{add_data_delim}frontend/dist",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "engineio.async_drivers.asgi",
        *icon_arg,
        "dock_app.py"
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print("\n" + "=" * 60)
    print("[+] Build Complete!")
    print(f"[*] Standalone Executable located at: dist\\AssistantDock\\AssistantDock.exe")
    print("=" * 60)

if __name__ == "__main__":
    build()
