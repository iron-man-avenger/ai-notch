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

def analyze_teams_text_with_gemini(
    text: str,
    sender: Optional[str] = None,
    user_name: Optional[str] = None,
    custom_api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Analyzes Teams chat/standup messages to extract actionable tasks.
    Specifically prioritizes action items assigned to the user (e.g. Dhiraj / Bhumit Bhai Team / Dhiraj Kumar).
    """
    clean_text = text.strip()
    if len(clean_text) < 8 or len(clean_text) > 5000:
        return []

    target_user = user_name or get_setting("user_name") or "Dhiraj"
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return [{
            "title": f"Task from {sender or 'Teams'}: {clean_text[:60]}",
            "sender": sender or "Teams",
            "description": clean_text,
            "project": "General",
            "priority": "Medium",
            "source": "teams_text"
        }]

    detected_sender = sender or get_active_teams_sender()

    prompt = f"""You are an executive AI assistant for {target_user} (Senior AI / Software Engineer).
Analyze this chat/standup message from Microsoft Teams (sender: {detected_sender}).
Extract ALL actionable work items, bug fixes, or tasks specifically assigned to {target_user} (or their team, or where {target_user} is asked to act/collaborate).

MESSAGE TEXT:
\"\"\"{clean_text}\"\"\"

Instructions:
1. Check each task or point. If "Assigned to" includes {target_user} or if {target_user} is mentioned to collaborate/deliver, extract it.
2. Ignore tasks assigned exclusively to other colleagues (e.g., Ayush, Malvi) unless {target_user} is explicitly mentioned.
3. If this message is a single task or request directed at {target_user}, extract it.
4. If it is only casual conversation or greetings ("hi", "good morning", "thanks"), return an empty list [].
5. The message may be in English, Hindi, or Hinglish. Always write the output title and description in clean, professional English.

Return ONLY a valid JSON array of tasks matching this schema:
[
  {{
    "title": "Concise actionable title in English (max 10 words)",
    "project": "Project name or General",
    "description": "Clear explanation of what needs to be changed, tested, or delivered",
    "priority": "High",
    "sender": "{detected_sender}",
    "source": "teams_chat"
  }}
]

If no tasks are assigned to {target_user}, return: []
DO NOT include markdown backticks or commentary outside the JSON array.
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        for model in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]:
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                if resp and resp.text:
                    raw = resp.text.strip()
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    data = json.loads(raw)
                    if isinstance(data, list):
                        return [t for t in data if isinstance(t, dict) and t.get("title")]
                    elif isinstance(data, dict):
                        if data.get("is_task") is False:
                            return []
                        if data.get("title"):
                            return [data]
            except Exception:
                continue
    except Exception as e:
        print(f"[TeamsTaskDetector Warning] Gemini parsing error: {e}")

    return []

def extract_teams_tasks_from_screen(
    jpeg_bytes: bytes,
    user_name: Optional[str] = None,
    custom_api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Uses Gemini Vision to inspect an on-screen Microsoft Teams window or desktop capture,
    extracting all work items / standup tasks assigned to the user.
    """
    if not jpeg_bytes:
        return []

    target_user = user_name or get_setting("user_name") or "Dhiraj"
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []

    prompt = f"""You are an executive AI assistant for {target_user} (Senior AI / Software Engineer).
Examine this desktop / Microsoft Teams screen capture.
Look for chat messages, standup lists, sprint tasks, or tickets.
Extract ALL action items specifically assigned to {target_user} (or {target_user}'s team, or where {target_user} is requested to act or collaborate).

Instructions:
1. Read the messages and task lists visible on screen.
2. Find every item where "Assigned to" includes {target_user} or mentions {target_user}.
3. Ignore items assigned exclusively to other team members unless {target_user} is collaborating.
4. For each detected task, extract:
   - title: concise, actionable task title in English (under 12 words)
   - project: project name or module (e.g. STO AI Services, STO Chatbot, Barscan, etc.)
   - description: detailed description of scope, deliverable, and EOD requirements
   - priority: High, Medium, or Low
   - sender: person or channel name from Teams
   - source: "teams_screen"

Return ONLY a valid JSON array matching this format:
[
  {{
    "title": "Actionable task title",
    "project": "Project Name",
    "description": "Details of the task and deliverables",
    "priority": "High",
    "sender": "Teams Chat",
    "source": "teams_screen"
  }}
]

If no tasks are assigned to {target_user} on this screen, return: []
DO NOT include markdown backticks or commentary outside JSON.
"""

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")

        for model in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]:
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=[prompt, part]
                )
                if resp and resp.text:
                    raw = resp.text.strip()
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    data = json.loads(raw)
                    if isinstance(data, list):
                        return [t for t in data if isinstance(t, dict) and t.get("title")]
                    elif isinstance(data, dict):
                        if data.get("title"):
                            return [data]
            except Exception as me:
                print(f"[TeamsScreenVision Warning] Model {model} failed: {me}")
                continue
    except Exception as e:
        print(f"[TeamsScreenVision Error] {e}")

    return []

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
    """Watches Microsoft Teams window: auto-scans for tasks on window focus and clipboard changes."""
    def __init__(self, check_interval: float = 1.2):
        self.check_interval = check_interval
        self.is_running = False
        self.last_clipboard = ""
        self.recent_proposals = set()
        self.thread: Optional[threading.Thread] = None
        self.on_task_detected: Optional[Callable[[Dict[str, Any]], None]] = None

        # Auto-scan state
        self.was_teams_active = False
        self.last_auto_scan_ts = 0.0
        self.auto_scan_cooldown = 45.0  # seconds between auto-scans
        self.last_scanned_img_hash = None
        self.is_scanning = False
        self.last_teams_title = ""

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.last_clipboard = get_clipboard_text()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _dispatch_detected_tasks(self, tasks: list, sender: str = "Teams"):
        new_tasks = []
        for t in tasks:
            title_key = t.get("title", "").strip().lower()
            if title_key and title_key not in self.recent_proposals:
                self.recent_proposals.add(title_key)
                new_tasks.append(t)

        if len(self.recent_proposals) > 60:
            self.recent_proposals = set(list(self.recent_proposals)[-30:])

        if new_tasks and self.on_task_detected:
            payload = {
                "is_task": True,
                "title": new_tasks[0].get("title", ""),
                "description": new_tasks[0].get("description", ""),
                "priority": new_tasks[0].get("priority", "High"),
                "sender": new_tasks[0].get("sender", sender),
                "project": new_tasks[0].get("project", ""),
                "tasks": new_tasks
            }
            try:
                self.on_task_detected(payload)
            except Exception as e:
                print(f"[TaskWatcher Callback Error] {e}")

    def _delayed_auto_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        try:
            # Wait 2.0s for the Teams window and chat messages to finish rendering on screen
            time.sleep(2.0)
            if not is_teams_window_active():
                return

            from core.screen_vision import capture_desktop_bytes
            screen_bytes = capture_desktop_bytes()
            if not screen_bytes or len(screen_bytes) < 1000:
                return

            import hashlib
            img_hash = hashlib.md5(screen_bytes[:6000]).hexdigest()
            if img_hash == self.last_scanned_img_hash:
                return
            self.last_scanned_img_hash = img_hash

            target_user = get_setting("user_name") or "Dhiraj"
            print(f"[Teams Auto-Scan] Teams window activated. Inspecting screen for tasks assigned to {target_user}...")
            tasks = extract_teams_tasks_from_screen(screen_bytes, user_name=target_user)
            if tasks:
                print(f"[Teams Auto-Scan] Found {len(tasks)} tasks assigned to {target_user}!")
                sender = get_active_teams_sender() or "Teams Screen"
                self._dispatch_detected_tasks(tasks, sender=sender)
        except Exception as e:
            print(f"[Teams Auto-Scan Error] {e}")
        finally:
            self.is_scanning = False

    def _run_loop(self):
        while self.is_running:
            try:
                teams_active = is_teams_window_active()
                now = time.time()

                if teams_active:
                    current_title = ""
                    if HAS_WIN32:
                        try:
                            hwnd = win32gui.GetForegroundWindow()
                            if hwnd:
                                current_title = win32gui.GetWindowText(hwnd).strip()
                        except Exception:
                            pass

                    # Automatic screen scan trigger when Teams window becomes active or chat switches
                    should_scan = False
                    if not self.was_teams_active:
                        if (now - self.last_auto_scan_ts) >= 15.0:
                            should_scan = True
                    elif current_title and current_title != self.last_teams_title:
                        if (now - self.last_auto_scan_ts) >= self.auto_scan_cooldown:
                            should_scan = True

                    if should_scan and not self.is_scanning:
                        self.last_auto_scan_ts = now
                        self.last_teams_title = current_title
                        threading.Thread(target=self._delayed_auto_scan, daemon=True).start()

                    # Clipboard monitoring fallback
                    current_clip = get_clipboard_text()
                    if current_clip and current_clip != self.last_clipboard:
                        self.last_clipboard = current_clip
                        lower = current_clip.lower()
                        has_indicator = any(word in lower for word in ACTION_INDICATORS)

                        if has_indicator and len(current_clip) >= 15 and not is_likely_code_or_junk(current_clip):
                            sender = get_active_teams_sender()
                            target_user = get_setting("user_name") or "Dhiraj"
                            tasks = analyze_teams_text_with_gemini(current_clip, sender=sender, user_name=target_user)
                            if tasks:
                                self._dispatch_detected_tasks(tasks, sender=sender)

                self.was_teams_active = teams_active

            except Exception:
                pass

            time.sleep(self.check_interval)
