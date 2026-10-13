import os
import sys

def enable_autostart():
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    if not os.path.exists(startup_dir):
        print(f"Startup folder does not exist: {startup_dir}")
        return False

    script_path = os.path.abspath("launch_silent.vbs")
    target_link = os.path.join(startup_dir, "MochiAssistant.vbs")

    content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{os.path.abspath('.')}"
WshShell.Run "C:\\Python314\\pythonw.exe main.py", 0, False
'''
    try:
        with open(target_link, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[Autostart Success] Created startup launcher at: {target_link}")
        return True
    except Exception as e:
        print(f"[Autostart Error] {e}")
        return False

if __name__ == "__main__":
    enable_autostart()
