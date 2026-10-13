import os

def disable_autostart():
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    vbs_path = os.path.join(startup_dir, "LaunchAIAssistant.vbs")

    if os.path.exists(vbs_path):
        try:
            os.remove(vbs_path)
            print("=" * 60)
            print(" SUCCESS: AI Assistant Auto-Start has been REMOVED.")
            print("=" * 60)
            print(f"Deleted startup script: {vbs_path}")
            print("The assistant will no longer start automatically upon Windows boot.")
            print("You can run it manually anytime with: python main.py")
            print("=" * 60)
            return True
        except Exception as e:
            print(f"❌ Failed to delete startup script: {e}")
            return False
    else:
        print("Auto-start was not enabled (no startup script found).")
        return True

if __name__ == "__main__":
    disable_autostart()
