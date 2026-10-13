import os
import re
import json
import time
import threading
from typing import Optional, Callable, Dict, Any
from dotenv import load_dotenv

try:
    import win32clipboard
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from core.db import get_setting

load_dotenv()

# Common action verbs/indicators in team chat
ACTION_INDICATORS = [
    "update", "pass", "change", "fix", "implement", "create", "add", "remove",
    "replace", "test", "check", "please", "can you", "could you", "need to",
    "todo", "task", "api", "bug", "deploy", "review", "send", "share"
]

def is_likely_code_or_junk(text: str) -> bool:
    """Filter out code snippets, SQL, tracebacks, raw JSON, URLs, and shell commands."""
    t = text.strip()
    if len(t) < 12 or len(t) > 3000:
        return True
    # JSON or dictionary/array dumps
    if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
        return True
    # Stack traces / errors
    if "Traceback (most recent call last):" in t or "Error:" in t and "\n" in t:
        return True
    # Common code keywords (if found with multiline indentation or punctuation)
    code_indicators = [
        "def ", "class ", "import ", "from ", "const ", "let ", "function(",
        "SELECT ", "INSERT INTO ", "UPDATE ", "WHERE ", "console.log(",
        "return ", "public static ", "namespace ", "using namespace"
    ]
    if any(ci in t for ci in code_indicators):
        if t.count("\n") >= 2 or t.count(";") >= 2 or t.count("{") >= 1:
            return True
    # Pure URLs
    if t.startswith("http://") or t.startswith("https://"):
        return True
    return False

def get_clipboard_text() -> str:
    if not HAS_WIN32:
        return ""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return data.strip() if data else ""
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return ""

def get_active_teams_sender() -> str:
    """Extracts sender/contact from active Teams window title (e.g. 'Chat | Bimal Desai | Microsoft Teams')."""
    if not HAS_WIN32:
        return "Teams Colleague"
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "Teams Colleague"
        title = win32gui.GetWindowText(hwnd).strip()
        # Look for "Chat | Person Name | Microsoft Teams"
        match = re.search(r"Chat\s*\|\s*([^|]+)\s*\|", title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Look for "Person Name | Microsoft Teams"
        match2 = re.search(r"^([^|]+)\s*\|\s*Microsoft Teams", title, re.IGNORECASE)
        if match2 and match2.group(1).strip().lower() not in ["chat", "teams", "activity", "calendar"]:
            return match2.group(1).strip()
    except Exception:
        pass
    return "Teams Colleague"

def analyze_teams_text_with_gemini(text: str, sender: Optional[str] = None, custom_api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Analyzes a message to determine if it contains an engineering/work action item, extracting structured task details."""
    clean_text = text.strip()
    if len(clean_text) < 8 or len(clean_text) > 3000:
        return None

    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback heuristic if no Gemini API key
        return {
            "is_task": True,
            "title": f"Task from {sender or 'Teams'}: {clean_text[:60]}",
            "sender": sender or "Teams",
            "description": clean_text,
            "priority": "Medium"
        }

    detected_sender = sender or get_active_teams_sender()

    prompt = f"""
You are an intelligent desktop executive assistant analyzing chat messages from Microsoft Teams.
Message received from: {detected_sender}
Message text:
\"\"\"{clean_text}\"\"\"

Task:
Determine whether this message conveys an actionable work request, engineering instruction, bug fix, task, or to-do.
(For example: "updated the API .. pass X-User-Id with their portal user id instead of X-User-Email" IS a clear engineering task).
If it is merely conversational greeting or chit-chat (e.g. "hi", "good morning", "thanks", "ok"), set is_task to false.

Bilingual Instruction:
The message may be written in English, Hindi, or Hinglish.
If a task is detected, ALWAYS translate and write the "title" and "description" strictly in clear, professional ENGLISH.

Return ONLY a valid JSON object matching this structure:
{{
  "is_task": true,
  "title": "Concise, actionable task title in English (max 10 words, e.g. Update API: Pass X-User-Id with portal ID instead of X-User-Email)",
  "sender": "{detected_sender}",
  "description": "Clear explanation of what needs to be changed or performed in English",
  "priority": "High"
}}

If not an action item, return:
{{
  "is_task": false
}}

DO NOT include markdown backticks or commentary. Return raw JSON only.
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        for model in ["gemini-flash-latest", "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.6-flash"]:
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                if resp and resp.text:
                    raw = resp.text.strip()
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    data = json.loads(raw)
                    if data.get("is_task"):
                        return data
                    return None
            except Exception:
                continue
    except Exception as e:
        print(f"[TeamsTaskDetector Warning] Gemini parsing error: {e}")

    return None

def is_teams_window_active() -> bool:
    """Returns True ONLY if Microsoft Teams is the current active foreground window."""
    if not HAS_WIN32:
        return False
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        title = win32gui.GetWindowText(hwnd).lower()
        if "teams" in title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid > 0:
            import psutil
            proc_name = psutil.Process(pid).name().lower()
            if "teams" in proc_name:
                return True
    except Exception:
        pass
    return False

class TeamsTaskWatcher:
    """Watches for copied text and incoming messages strictly in Microsoft Teams, auto-extracting tasks."""
    def __init__(self, check_interval: float = 1.5):
        self.check_interval = check_interval
        self.is_running = False
        self.last_clipboard = ""
        self.recent_proposals = set()
        self.thread: Optional[threading.Thread] = None
        self.on_task_detected: Optional[Callable[[Dict[str, Any]], None]] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.last_clipboard = get_clipboard_text()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _run_loop(self):
        while self.is_running:
            try:
                # ONLY inspect clipboard if the user is actively working inside Microsoft Teams
                if is_teams_window_active():
                    current_clip = get_clipboard_text()
                    if current_clip and current_clip != self.last_clipboard:
                        self.last_clipboard = current_clip
                        
                        lower = current_clip.lower()
                        has_indicator = any(word in lower for word in ACTION_INDICATORS)

                        if has_indicator and len(current_clip) >= 15 and not is_likely_code_or_junk(current_clip):
                            sender = get_active_teams_sender()
                            task = analyze_teams_text_with_gemini(current_clip, sender=sender)
                            
                            if task and task.get("is_task"):
                                title_key = task.get("title", "").strip().lower()
                                # Deduplication: prevent repeated proposals of the same task
                                if title_key and title_key not in self.recent_proposals:
                                    self.recent_proposals.add(title_key)
                                    if len(self.recent_proposals) > 50:
                                        self.recent_proposals.pop()

                                    if self.on_task_detected:
                                        try:
                                            self.on_task_detected(task)
                                        except Exception as e:
                                            print(f"[TaskWatcher Callback Error] {e}")

            except Exception:
                pass

            time.sleep(self.check_interval)
