import os
import sys

STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Startup"
)
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VBS_TARGET_NAME = "Mochi_AI_Assistant.vbs"
VBS_PATH = os.path.join(STARTUP_FOLDER, VBS_TARGET_NAME)

def get_vbs_content() -> str:
    # Uses pythonw.exe if available to prevent any console window, or python.exe with 0 window style
    python_exe = sys.executable
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    exe_to_use = pythonw_exe if os.path.exists(pythonw_exe) else python_exe

    return f"""' Auto-generated silent launcher for Mochi AI Assistant
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{PROJECT_DIR}"
WshShell.Run Chr(34) & "{exe_to_use}" & Chr(34) & " main.py", 0, False
"""

def enable_autostart() -> bool:
    try:
        os.makedirs(STARTUP_FOLDER, exist_ok=True)
        content = get_vbs_content()
        with open(VBS_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Also create a local silent launcher in project root for convenience
        local_vbs = os.path.join(PROJECT_DIR, "start_assistant_silent.vbs")
        with open(local_vbs, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[Autostart] Successfully registered in Windows Startup:")
        print(f"  -> {VBS_PATH}")
        print(f"  -> Local silent launcher: {local_vbs}")
        return True
    except Exception as e:
        print(f"[Autostart Error] Failed to enable autostart: {e}")
        return False

def disable_autostart() -> bool:
    try:
        if os.path.exists(VBS_PATH):
            os.remove(VBS_PATH)
            print(f"[Autostart] Removed from Windows Startup: {VBS_PATH}")
        else:
            print("[Autostart] Assistant is not currently in Windows Startup.")
        return True
    except Exception as e:
        print(f"[Autostart Error] Failed to disable autostart: {e}")
        return False

def is_autostart_enabled() -> bool:
    return os.path.exists(VBS_PATH)

if __name__ == "__main__":
    if "--disable" in sys.argv:
        disable_autostart()
    elif "--status" in sys.argv:
        status = "ENABLED" if is_autostart_enabled() else "DISABLED"
        print(f"[Autostart Status] {status}")
    else:
        # Default is enable
        enable_autostart()
