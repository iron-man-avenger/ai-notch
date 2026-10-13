import os
import json
import re
import time
import threading
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Windows Win32 API for keystrokes & mouse clicks
import ctypes
user32 = ctypes.windll.user32

VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def simulate_enter_press():
    """Simulates pressing and releasing the Enter (Return) key."""
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.06)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)

def simulate_mouse_click(screen_x: int, screen_y: int):
    """Moves cursor to screen coordinates and performs a left-click."""
    user32.SetCursorPos(int(screen_x), int(screen_y))
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def detect_approval_dialog_with_vision(jpeg_bytes: bytes, custom_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses Gemini Multimodal Vision to inspect screen capture for approval modals,
    evaluating command safety and pinpointing button coordinates.
    """
    from core.db import get_setting
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"has_approval_dialog": False, "error": "Gemini API key missing"}

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg") if jpeg_bytes else None

    prompt = """
You are Mochi's Safety & Approval Inspector.
Analyze the provided screen capture:
1. Is there an active approval dialog, confirmation prompt, or command permission modal? (e.g. "Allow running ...", "Confirm", "Do you want to run", "Yes/No", "[Submit (Enter)]", UAC prompt)
2. What is the title and the exact command or action requesting approval?
3. Safety Check: Is this action safe to auto-approve?
   - SAFE: Running local test scripts, pytest, python dev commands, npm build/test, git status/log, reading files.
   - UNSAFE / DANGEROUS: Deleting production DB, disk wipe, formatting, broad rm -rf, dropping tables, sending external emails.
4. Locate the exact normalized coordinates of the "Submit" or "Allow" button (box_2d: [ymin, xmin, ymax, xmax] on scale 0 to 1000).

Return ONLY valid JSON matching this schema:
{
  "has_approval_dialog": true or false,
  "dialog_title": "Title of prompt or modal",
  "command": "The specific command requesting execution",
  "is_safe": true or false,
  "safety_reason": "Concise 1-sentence safety assessment",
  "approval_method": "press_enter or click_button",
  "button_box_2d": [ymin, xmin, ymax, xmax] or null
}
DO NOT include markdown backticks. Return raw JSON only.
"""
    contents = [prompt]
    if part:
        contents.append(part)

    for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
        try:
            cfg = types.GenerateContentConfig(response_mime_type="application/json")
            res = client.models.generate_content(model=m, contents=contents, config=cfg)
            if res and res.text:
                raw = res.text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw)
                return data
        except Exception as e:
            print(f"[Approval Vision Model {m} Error] {e}")
            continue

    return {"has_approval_dialog": False, "is_safe": False}


class AutoApprovalManager:
    """
    Manages autonomous and on-demand approvals for desktop dialogs.
    Can auto-approve the next N safe commands with quota countdown and safety verification.
    """
    def __init__(self):
        self.remaining_quota: int = 0
        self.is_monitoring: bool = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.on_approval_callback = None
        self.history = []
        self._lock = threading.Lock()

    def set_quota(self, count: int = 10, controller=None):
        """Sets the remaining auto-approval quota (e.g. next 10 approvals)."""
        with self._lock:
            self.remaining_quota = max(0, count)
        print(f"[AutoApprover] Quota set to {self.remaining_quota} safe approvals.")
        self.start_monitoring(controller)
        return {
            "success": True,
            "remaining_quota": self.remaining_quota,
            "message": f"Auto-approver active for the next {self.remaining_quota} safe approvals."
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "remaining_quota": self.remaining_quota,
                "is_monitoring": self.is_monitoring,
                "total_approved": len(self.history),
                "recent_history": self.history[-5:]
            }

    def approve_current(self, controller=None, force: bool = False) -> Dict[str, Any]:
        """
        One-shot: Inspects screen right now, checks safety, and approves the visible dialog.
        """
        from core.screen_vision import capture_desktop_bytes
        screen_bytes = capture_desktop_bytes(controller)
        if not screen_bytes:
            return {"success": False, "message": "Could not capture screen."}

        dialog_info = detect_approval_dialog_with_vision(screen_bytes)
        if not dialog_info.get("has_approval_dialog"):
            # If vision couldn't find a dialog but user explicitly said 'approve it', send Enter as fallback
            if force:
                simulate_enter_press()
                return {
                    "success": True,
                    "approved": True,
                    "dialog_title": "Generic Focused Dialog",
                    "command": "Active Window Confirmation",
                    "method": "press_enter",
                    "message": "Sent Enter key to active window."
                }
            return {
                "success": False,
                "has_approval_dialog": False,
                "message": "No approval dialog detected on screen."
            }

        # Safety evaluation
        is_safe = dialog_info.get("is_safe", True)
        if not is_safe and not force:
            return {
                "success": False,
                "is_safe": False,
                "dialog_title": dialog_info.get("dialog_title"),
                "command": dialog_info.get("command"),
                "message": f"Safety warning: Command '{dialog_info.get('command')}' flagged unsafe! Refusing auto-approval."
            }

        # Perform approval
        method = dialog_info.get("approval_method", "press_enter")
        btn_box = dialog_info.get("button_box_2d")

        # If button coordinates found, click button
        if btn_box and len(btn_box) == 4:
            try:
                screen_w = user32.GetSystemMetrics(0)
                screen_h = user32.GetSystemMetrics(1)
                ymin, xmin, ymax, xmax = btn_box
                center_y = int(((ymin + ymax) / 2000.0) * screen_h)
                center_x = int(((xmin + xmax) / 2000.0) * screen_w)
                simulate_mouse_click(center_x, center_y)
            except Exception as e:
                print(f"[AutoApprover Click Error] {e}, falling back to Enter")
                simulate_enter_press()
        else:
            simulate_enter_press()

        record = {
            "timestamp": time.time(),
            "dialog_title": dialog_info.get("dialog_title", "Approval Prompt"),
            "command": dialog_info.get("command", "Unknown"),
            "safety_reason": dialog_info.get("safety_reason", "Verified safe"),
            "method": method
        }
        with self._lock:
            self.history.append(record)

        if self.on_approval_callback:
            try:
                self.on_approval_callback(record)
            except Exception as e:
                print("[AutoApprover Callback Error]", e)

        return {
            "success": True,
            "approved": True,
            "dialog_title": record["dialog_title"],
            "command": record["command"],
            "safety_reason": record["safety_reason"],
            "message": f"Approved '{record['dialog_title']}' successfully."
        }

    def start_monitoring(self, controller=None):
        """Starts background daemon loop to monitor and auto-approve while quota > 0."""
        if self.is_monitoring:
            return
        self.is_monitoring = True

        def _monitor_loop():
            from core.screen_vision import capture_desktop_bytes
            print("[AutoApprover Daemon] Monitoring active for on-screen approvals...")
            while self.is_monitoring:
                with self._lock:
                    quota = self.remaining_quota
                if quota <= 0:
                    break

                try:
                    time.sleep(2.5) # Check every 2.5 seconds
                    screen_bytes = capture_desktop_bytes(controller)
                    if screen_bytes:
                        dialog = detect_approval_dialog_with_vision(screen_bytes)
                        if dialog.get("has_approval_dialog") and dialog.get("is_safe"):
                            print(f"[AutoApprover Daemon] Detected safe dialog: {dialog.get('dialog_title')}")
                            res = self.approve_current(controller=controller)
                            if res.get("approved"):
                                with self._lock:
                                    self.remaining_quota -= 1
                                    remaining = self.remaining_quota
                                print(f"[AutoApprover Daemon] Auto-approved! {remaining} approvals remaining.")
                except Exception as e:
                    print(f"[AutoApprover Loop Warning] {e}")

            self.is_monitoring = False
            print("[AutoApprover Daemon] Monitoring stopped (quota exhausted or cancelled).")

        self.monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def cancel_monitoring(self):
        """Stops auto-approval monitoring and resets quota."""
        with self._lock:
            self.remaining_quota = 0
            self.is_monitoring = False
        return {"success": True, "message": "Auto-approval monitoring cancelled."}

# Global singleton
auto_approver = AutoApprovalManager()
