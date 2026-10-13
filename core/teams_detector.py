import time
import threading
from typing import Optional, Callable, List, Dict

try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

CALL_TITLE_KEYWORDS = [
    "meeting |",
    "call with",
    "in call",
    "teams call",
    "microsoft teams meeting",
    "(meeting)",
    "(call)"
]

def find_teams_call_windows() -> List[str]:
    """Inspects all open top-level windows for active Teams call windows."""
    if not HAS_WIN32:
        return []
    
    call_windows = []
    
    def enum_windows_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return True
            
        lower_title = title.lower()
        if "teams" in lower_title:
            for kw in CALL_TITLE_KEYWORDS:
                if kw in lower_title:
                    call_windows.append(title)
                    break
        return True

    try:
        win32gui.EnumWindows(enum_windows_callback, None)
    except Exception:
        pass
        
    return call_windows

def find_teams_chat_windows() -> List[str]:
    """Finds active Teams chat/message windows to understand active conversation context."""
    if not HAS_WIN32:
        return []
    
    chats = []
    
    def enum_windows_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return True
            
        lower_title = title.lower()
        if "microsoft teams" in lower_title and not any(kw in lower_title for kw in CALL_TITLE_KEYWORDS):
            # Clean up title like "Chat | John Doe | Microsoft Teams" or "Dev Team | Microsoft Teams"
            clean = title.replace("| Microsoft Teams", "").replace("- Microsoft Teams", "").strip()
            if clean and clean.lower() not in ["microsoft teams", "teams", "activity"]:
                chats.append(clean)
        return True

    try:
        win32gui.EnumWindows(enum_windows_callback, None)
    except Exception:
        pass
        
    return chats

class TeamsCallDetector:
    def __init__(self, check_interval: float = 3.5):
        self.check_interval = check_interval
        self.is_running = False
        self.in_meeting = False
        self.meeting_subject = ""
        self.active_chat_context = ""
        self.thread: Optional[threading.Thread] = None
        self.on_call_started: Optional[Callable[[str], None]] = None
        self.on_call_ended: Optional[Callable[[str], None]] = None
        self.on_chat_detected: Optional[Callable[[str], None]] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def trigger_mock_call_ended(self, subject: str = "Project Sync"):
        """Allows testing call completion trigger from UI or API."""
        if self.on_call_ended:
            self.on_call_ended(subject)

    def _run_loop(self):
        consecutive_missing = 0
        
        while self.is_running:
            # 1. Check for active Teams Call / Meeting
            call_windows = find_teams_call_windows()
            
            if call_windows:
                consecutive_missing = 0
                subject = call_windows[0]
                if not self.in_meeting:
                    self.in_meeting = True
                    self.meeting_subject = subject
                    if self.on_call_started:
                        try:
                            self.on_call_started(subject)
                        except Exception:
                            pass
            else:
                if self.in_meeting:
                    consecutive_missing += 1
                    # Require 2 consecutive checks of no call window to confirm meeting ended
                    if consecutive_missing >= 2:
                        self.in_meeting = False
                        ended_subject = self.meeting_subject or "Teams Meeting"
                        self.meeting_subject = ""
                        consecutive_missing = 0
                        
                        if self.on_call_ended:
                            try:
                                self.on_call_ended(ended_subject)
                            except Exception:
                                pass

            # 2. Check for active Teams Chat / Conversation window
            chat_windows = find_teams_chat_windows()
            if chat_windows:
                latest_chat = chat_windows[0]
                if latest_chat != self.active_chat_context:
                    self.active_chat_context = latest_chat
                    if self.on_chat_detected:
                        try:
                            self.on_chat_detected(latest_chat)
                        except Exception:
                            pass
                                
            time.sleep(self.check_interval)
