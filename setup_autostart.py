import os
import sys

def setup_autostart():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    vbs_path = os.path.join(startup_dir, "LaunchAIAssistant.vbs")

    # Python executable path (prefer pythonw.exe for silent execution without terminal window)
    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{project_dir}"
WshShell.Run """{pythonw_exe}"" main.py", 0, False
'''

    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        print("=" * 60)
        print(" SUCCESS: AI Assistant Auto-Start is now CONFIGURED!")
        print("=" * 60)
        print(f"Startup Script Created: {vbs_path}")
        print(f"Target Working Directory: {project_dir}")
        print(f"Silent Python Runtime: {pythonw_exe}")
        print("\nWhat happens now:")
        print("• Every time your laptop boots or restarts, the assistant will automatically start.")
        print("• It runs silently in the background with ZERO black command prompt windows.")
        print("• The Coucou notch will float cleanly at the top of your screen ready for your day.")
        print("\nTo disable autostart at any time, run: python disable_autostart.py")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"❌ Failed to set up startup shortcut: {e}")
        return False

if __name__ == "__main__":
    setup_autostart()
