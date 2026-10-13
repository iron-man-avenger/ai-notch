import time
import threading
from typing import Dict, Any, Callable, Optional
import psutil

try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from core.db import log_activity, get_today_app_summary
from core.export_logger import save_daily_markdown_log

APP_NAME_MAP = {
    "code.exe": "Visual Studio Code",
    "antigravity.exe": "Antigravity IDE",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "slack.exe": "Slack",
    "explorer.exe": "File Explorer",
    "windowsterminal.exe": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "devenv.exe": "Visual Studio",
    "outlook.exe": "Outlook",
    "notion.exe": "Notion",
    "postman.exe": "Postman"
}

IGNORED_SYSTEM_PROCESSES = {
    "shellexperiencehost.exe", "searchhost.exe", "lockapp.exe", "searchapp.exe",
    "systemsettings.exe", "applicationframehost.exe", "taskmgr.exe", "textinputhost.exe",
    "screensketch.exe", "snippingtool.exe", "startmenuexperiencehost.exe", "ctfmon.exe",
    "dwm.exe", "runtimebroker.exe", "backgroundtaskhost.exe", "openwith.exe",
    "securityhealthsystray.exe", "smartscreen.exe", "explorer.exe"
}

def clean_app_name(raw_name: str) -> str:
    key = raw_name.lower().strip()
    return APP_NAME_MAP.get(key, raw_name.replace(".exe", "").capitalize())

def get_current_foreground_window() -> Dict[str, str]:
    if not HAS_WIN32:
        return {"app": "System", "title": "Mock Window (Win32 unavailable)"}
    
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"app": "Idle", "title": "Desktop / Lock Screen"}
        
        window_title = win32gui.GetWindowText(hwnd).strip()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        if pid <= 0:
            return {"app": "Idle", "title": "Desktop / System"}
            
        try:
            proc = psutil.Process(pid)
            raw_app_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            raw_app_name = "Unknown"
            
        if raw_app_name.lower() in IGNORED_SYSTEM_PROCESSES:
            return {"app": "Idle", "raw_app": raw_app_name, "title": "System / Desktop"}

        clean_name = clean_app_name(raw_app_name)
        return {
            "app": clean_name,
            "raw_app": raw_app_name,
            "title": window_title if window_title else clean_name
        }
    except Exception as e:
        return {"app": "Unknown", "title": str(e)}

class ActivityTracker:
    def __init__(self, poll_interval: float = 3.0):
        self.poll_interval = poll_interval
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.app_totals: Dict[str, int] = {}
        
        # Initialize cumulative app totals from today's DB records
        try:
            summary = get_today_app_summary()
            for s in summary:
                self.app_totals[s["app_name"]] = s["total_seconds"]
        except Exception:
            pass

        self.current_activity: Dict[str, Any] = {
            "app": "Initializing",
            "title": "Starting tracker...",
            "duration": 0,
            "session_duration": 0
        }
        self.on_tick_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._lock = threading.Lock()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.current_activity)

    def _run_loop(self):
        last_app = ""
        last_title = ""
        consecutive_seconds = 0
        tick_count = 0

        while self.is_running:
            tick_count += 1
            info = get_current_foreground_window()
            app = info["app"]
            title = info["title"]

            # If it's a valid app and not empty
            if app not in ["Idle", "Initializing"]:
                if app == last_app and title == last_title:
                    consecutive_seconds += int(self.poll_interval)
                else:
                    last_app = app
                    last_title = title
                    consecutive_seconds = int(self.poll_interval)

                # Maintain cumulative daily total for this app
                self.app_totals[app] = self.app_totals.get(app, 0) + int(self.poll_interval)

                # Persist incremental progress to SQLite
                log_activity(app, title, int(self.poll_interval))

                with self._lock:
                    self.current_activity = {
                        "app": app,
                        "title": title,
                        "duration": self.app_totals[app],          # Cumulative time today
                        "session_duration": consecutive_seconds     # Current consecutive focus
                    }

                if self.on_tick_callback:
                    try:
                        self.on_tick_callback(self.current_activity)
                    except Exception:
                        pass

            # Periodically auto-save markdown log every 30 ticks (~60 seconds)
            if tick_count % 30 == 0:
                try:
                    save_daily_markdown_log()
                except Exception:
                    pass

            time.sleep(self.poll_interval)
