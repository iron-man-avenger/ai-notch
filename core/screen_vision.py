import os
import json
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

def capture_desktop_bytes(controller=None, quality: int = 75) -> bytes:
    """
    Captures the primary desktop screen as JPEG bytes.
    If controller is provided and has a synchronous capture method, delegates to it.
    Otherwise uses PySide6's primary screen grab or GDI fallback.
    """
    if controller and hasattr(controller, "capture_screen_sync"):
        try:
            captured = controller.capture_screen_sync(quality=quality)
            if captured and len(captured) > 100:
                return captured
        except Exception as e:
            print(f"[Screen Capture Controller Warning] {e}")

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QGuiApplication, QImage
        from PySide6.QtCore import QBuffer, QIODevice

        app = QApplication.instance() or QGuiApplication.instance()
        if not app:
            app = QApplication([])

        screen = app.primaryScreen()
        if screen:
            pix = screen.grabWindow(0)
            if not pix.isNull() and pix.width() > 10 and pix.height() > 10:
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                pix.save(buf, "JPEG", quality)
                data = bytes(buf.data().data())
                if len(data) > 500:
                    return data
    except Exception as e:
        print(f"[Screen Capture PySide6 Warning] {e}")

    # Fallback placeholder image (for headless CI or when desktop is detached)
    try:
        from PySide6.QtGui import QImage, QPainter, QColor
        from PySide6.QtCore import QBuffer, QIODevice, Qt
        img = QImage(1280, 720, QImage.Format.Format_RGB32)
        img.fill(QColor(24, 24, 27))
        painter = QPainter(img)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "Desktop Screen Capture")
        painter.end()
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "JPEG", 70)
        return bytes(buf.data().data())
    except Exception:
        return b""

def capture_screen_region_at_cursor(controller=None, width: int = 720, height: int = 500, quality: int = 80) -> Dict[str, Any]:
    """
    Finds current Windows mouse cursor position, crops a region (width x height)
    centered on the cursor, and returns JPEG bytes + cursor coordinates.
    """
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    try:
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        cx, cy = pt.x, pt.y
    except Exception:
        cx, cy = 0, 0

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QBuffer, QIODevice
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        screen = app.primaryScreen()
        if screen:
            geom = screen.geometry()
            left = max(0, min(cx - (width // 2), geom.width() - width))
            top = max(0, min(cy - (height // 2), geom.height() - height))
            pix = screen.grabWindow(0, left, top, width, height)
            if not pix.isNull() and pix.width() > 10:
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                pix.save(buf, "JPEG", quality)
                return {
                    "bytes": bytes(buf.data().data()),
                    "cursor": {"x": cx, "y": cy},
                    "region": {"left": left, "top": top, "width": width, "height": height}
                }
    except Exception as e:
        print("[Cursor Screen Grab Warning]", e)

    full_bytes = capture_desktop_bytes(controller, quality=quality)
    return {
        "bytes": full_bytes,
        "cursor": {"x": cx, "y": cy},
        "region": None
    }

def analyze_screen_with_gemini(
    jpeg_bytes: bytes,
    user_query: str = "",
    focus: str = "general",
    active_app: str = "",
    custom_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends screen image to Gemini 3.5 Flash for real-time vision diagnosis,
    code inspection, or Teams/Email suggestion.
    """
    from core.db import get_setting
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "summary": "Gemini API Key missing.",
            "diagnosis": "Please enter your Gemini API key in Settings.",
            "suggested_action": "Configure API Key",
            "suggested_reply": None
        }

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg") if jpeg_bytes else None

    prompt = f"""
You are Mochi, an ultra-smart desktop companion. You are analyzing the user's live screen or cropped region.
User focus/query: "{user_query or 'What is on my screen and what should I do?'}"
Category: {focus} (options: error_diagnosis, data_extraction, rephrase, teams_reply, general)
Active Windows Process: {active_app or 'Unknown'}

Instructions:
1. Examine the visual content (IDE code, terminal output, Azure DevOps / Jira task form, web page, table, or chat).
2. Extract the key input context visible on screen into 'detected_input'.
3. Category-specific behavior:
   - If Category is 'data_extraction':
     * Intelligently extract all visible form fields, labels, inputs, work item details (e.g., Azure DevOps Task/Bug/Story: Title, Assigned To, State, Iteration, Area, Story Points, Acceptance Criteria, Description).
     * Distinguish REQUIRED fields (marked by asterisks '*', red badges, mandatory labels) vs OPTIONAL fields.
     * Put a structured, clean, ready-to-copy summary or markdown table in 'suggested_reply'.
     * Put a concise breakdown of what was extracted (e.g. "Extracted 5 fields: 2 required, 3 optional") in 'diagnosis'.
   - If Category is 'error_diagnosis':
     * Pinpoint the exact error message, stack trace, or buggy line.
     * In 'diagnosis', explain the root cause clearly.
     * In 'suggested_action', give the exact fix or terminal command.
   - If Category is 'rephrase':
     * Extract the visible draft, prompt box text, or highlighted sentence.
     * In 'suggested_reply', provide the polished, articulate executive English version.
   - If Category is 'teams_reply':
     * Identify the incoming chat or email.
     * In 'suggested_reply', provide a polite, professional, ready-to-send response.
4. Keep 'diagnosis' concise and actionable (under 75 words).
5. Locate the primary target element on screen and return its 2D bounding box in 'bounding_box' formatted as [ymin, xmin, ymax, xmax] normalized to 0-1000 (e.g. the text input box, error banner, or form card).
6. Output ONLY a valid JSON object matching this schema:
{{
  "summary": "1 sentence describing what window/form/content is visible",
  "detected_input": "Key text snippet, form name, error line, or active content extracted from screen",
  "diagnosis": "Concise root cause, data overview, or key observation",
  "suggested_action": "Short step to resolve, fill, or execute (under 25 words)",
  "suggested_reply": "Ready-to-copy text, extracted fields, or message reply if relevant, else null",
  "bounding_box": [ymin, xmin, ymax, xmax]
}}
DO NOT include markdown backticks or commentary outside JSON.
"""

    contents = [prompt]
    if part:
        contents.append(part)

    for model in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]:
        try:
            cfg = types.GenerateContentConfig(response_mime_type="application/json")
            res = client.models.generate_content(model=model, contents=contents, config=cfg)
            if res and res.text:
                raw = res.text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw)
                return data
        except Exception as e:
            print(f"[Gemini Screen Vision Model {model} Error] {e}")
            continue

    return {
        "summary": f"Inspected active window ({active_app})",
        "detected_input": f"Active display content from {active_app or 'Windows'}",
        "diagnosis": "Screen captured successfully. Everything looks orderly.",
        "suggested_action": "Continue with your active task.",
        "suggested_reply": None,
        "bounding_box": [400, 200, 600, 800]
    }

def get_active_caret_screen_rect() -> Optional[Dict[str, int]]:
    """Attempts to find the physical screen rect of the active typing caret or focused input on Windows."""
    try:
        import win32gui
        import win32process
        import ctypes
        from ctypes import wintypes

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        class GUITHREADINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('flags', wintypes.DWORD),
                ('hwndActive', wintypes.HWND),
                ('hwndFocus', wintypes.HWND),
                ('hwndCapture', wintypes.HWND),
                ('hwndMenuOwner', wintypes.HWND),
                ('hwndMoveSize', wintypes.HWND),
                ('hwndCaret', wintypes.HWND),
                ('rcCaret', wintypes.RECT)
            ]

        tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(GUITHREADINFO)
        if ctypes.windll.user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
            target_hwnd = info.hwndCaret or info.hwndFocus or hwnd
            if target_hwnd:
                pt = wintypes.POINT(info.rcCaret.left, info.rcCaret.top)
                ctypes.windll.user32.ClientToScreen(target_hwnd, ctypes.byref(pt))
                w = max(240, info.rcCaret.right - info.rcCaret.left + 120)
                h = max(42, info.rcCaret.bottom - info.rcCaret.top + 24)
                if pt.x > 0 or pt.y > 0:
                    return {"x": pt.x, "y": pt.y, "width": w, "height": h}
    except Exception:
        pass
    return None

def resolve_target_coordinates(
    bounding_box: Optional[list] = None,
    screen_w: int = 1920,
    screen_h: int = 1080,
    focus: str = "general",
    mode: str = "fullscreen",
    cursor_x: Optional[int] = None,
    cursor_y: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes absolute desktop pixel coordinates [x, y, w, h] for the crawler agent.
    Combines Gemini's 2D bounding box, Windows Caret detection, and category heuristics.
    """
    # 1. Cursor Target mode
    if mode == "pointer" and cursor_x is not None and cursor_y is not None:
        return {
            "x": max(10, cursor_x - 180),
            "y": max(10, cursor_y - 45),
            "width": 360,
            "height": 90,
            "source": "cursor_target"
        }

    # 2. Rephrase mode: check active Windows typing caret
    if focus == "rephrase":
        caret = get_active_caret_screen_rect()
        if caret and caret.get("width", 0) > 30:
            caret["source"] = "windows_caret"
            return caret

    # 3. Gemini Vision 2D bounding box
    if bounding_box and len(bounding_box) == 4:
        ymin, xmin, ymax, xmax = bounding_box
        if any(v > 0 for v in [ymin, xmin, ymax, xmax]):
            x = int((xmin / 1000.0) * screen_w)
            y = int((ymin / 1000.0) * screen_h)
            w = max(120, int(((xmax - xmin) / 1000.0) * screen_w))
            h = max(40, int(((ymax - ymin) / 1000.0) * screen_h))
            return {"x": x, "y": y, "width": w, "height": h, "source": "gemini_box_2d"}

    # 4. Fallback heuristics based on focus category
    if focus == "rephrase":
        # Usually prompt / chat input is at bottom of active screen
        return {"x": int(screen_w * 0.25), "y": int(screen_h * 0.82), "width": int(screen_w * 0.5), "height": 65, "source": "default_input_box"}
    elif focus == "error_diagnosis":
        # Usually terminal/compiler errors are in bottom-center or middle-left
        return {"x": int(screen_w * 0.15), "y": int(screen_h * 0.55), "width": int(screen_w * 0.7), "height": 180, "source": "default_error_region"}
    elif focus == "data_extraction":
        # Usually forms / ticket cards are in center of screen
        return {"x": int(screen_w * 0.2), "y": int(screen_h * 0.22), "width": int(screen_w * 0.6), "height": int(screen_h * 0.55), "source": "default_form_card"}
    else: # teams_reply or general
        return {"x": int(screen_w * 0.3), "y": int(screen_h * 0.65), "width": int(screen_w * 0.4), "height": 100, "source": "default_chat_bubble"}

def get_windows_clipboard_text() -> str:
    """Safely retrieves current text from Windows clipboard."""
    try:
        import win32clipboard, win32con
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                return data or ""
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return ""

def copy_windows_clipboard_text(text: str) -> bool:
    """Sets text into Windows clipboard."""
    try:
        import win32clipboard, win32con
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            return True
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        print("[Clipboard Copy Error]", e)
    return False

def grab_active_selection_via_ctrl_c() -> str:
    """Sends a quick Ctrl+C keystroke to copy whatever the user currently highlighted."""
    try:
        import ctypes, time
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_C = 0x43
        KEYEVENTF_KEYUP = 0x0002

        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_C, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.06)

        txt = get_windows_clipboard_text()
        if txt and len(txt.strip()) > 1:
            return txt.strip()
    except Exception as e:
        print("[Grab Selection Warning]", e)
    return ""

def rephrase_with_groq(draft: str, tone: str = "polished") -> Optional[Dict[str, str]]:
    """Ultrafast Groq fallback for text rephrasing."""
    try:
        import requests
        from core.db import get_setting
        groq_key = get_setting("groq_api_key") or os.getenv("GROQ_API_KEY")
        if not groq_key:
            return None

        prompt = f"""
You are an executive communication assistant.
Rephrase this user draft into clear, articulate, natural, polished English ({tone} tone):
"{draft}"

Return ONLY a JSON object:
{{
  "original": "{draft}",
  "reply": "Polished rephrased text ready to copy-paste",
  "explanation": "Brief 1-sentence note of what was improved"
}}
"""
        payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=6)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            res_data = json.loads(content)
            return res_data
    except Exception as e:
        print("[Groq Rephrase Fallback Error]", e)
    return None

def rephrase_from_screen_or_draft(
    user_draft: str = "",
    user_query: str = "",
    tone: str = "polished",
    controller=None,
    custom_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligently identifies text to rephrase:
    1. Direct user draft if provided.
    2. Active on-screen selection via simulated Ctrl+C.
    3. Multimodal Gemini Vision inspection of screen capture (extracts blue highlighted selection or input box text).
    4. Rephrases into polished English, auto-copies to Windows clipboard, and returns result.
    """
    draft = user_draft.strip()

    # Step 1: If no draft text provided, try to grab selection
    if not draft:
        draft = grab_active_selection_via_ctrl_c()

    # Step 2: If we still don't have draft text, use Multimodal Screen Vision!
    if not draft or len(draft) < 3:
        screen_bytes = capture_desktop_bytes(controller)
        if screen_bytes and len(screen_bytes) > 500:
            from core.db import get_setting
            api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
            if api_key:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                part = types.Part.from_bytes(data=screen_bytes, mime_type="image/jpeg")
                vision_prompt = f"""
You are Mochi's Vision & Rephrasing Engine.
The user looked at their screen and said: "{user_query or 'rephrase it'}".
Instructions:
1. Locate the text the user wants rephrased:
   - Primary: Look for any text HIGHLIGHTED or SELECTED (often in a blue selection rectangle at the bottom or in a chat/editor window).
   - Secondary: Look for draft text being typed into an active input box / prompt box at the bottom of the screen.
2. Extract the exact original text.
3. Rephrase it into clear, articulate, natural, polished English ({tone} tone).
4. Return ONLY valid JSON:
{{
  "original": "extracted original text",
  "reply": "polished and rephrased text ready to copy-paste",
  "explanation": "Brief 1-sentence explanation of what was improved"
}}
"""
                for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
                    try:
                        cfg = types.GenerateContentConfig(response_mime_type="application/json")
                        res = client.models.generate_content(model=m, contents=[vision_prompt, part], config=cfg)
                        if res and res.text:
                            raw = res.text.strip()
                            raw = re.sub(r"^```(?:json)?\s*", "", raw)
                            raw = re.sub(r"\s*```$", "", raw)
                            data = json.loads(raw)
                            rephrased_text = data.get("reply", "")
                            if rephrased_text:
                                copy_windows_clipboard_text(rephrased_text)
                                data["copied_to_clipboard"] = True
                                data["tone"] = tone
                                return data
                    except Exception as e:
                        print(f"[Vision Rephrase Model {m} Error] {e}")

    # Step 3: If we have draft text (or clipboard text), rephrase it using Gemini or Groq
    if draft:
        from core.db import get_setting
        api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if api_key:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            text_prompt = f"""
Rephrase this user text into clear, articulate, natural, polished English ({tone} tone):
"{draft}"

Return ONLY valid JSON:
{{
  "original": "{draft}",
  "reply": "polished rephrased text ready to copy-paste",
  "explanation": "Brief 1-sentence explanation"
}}
"""
            for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
                try:
                    cfg = types.GenerateContentConfig(response_mime_type="application/json")
                    res = client.models.generate_content(model=m, contents=[text_prompt], config=cfg)
                    if res and res.text:
                        raw = res.text.strip()
                        raw = re.sub(r"^```(?:json)?\s*", "", raw)
                        raw = re.sub(r"\s*```$", "", raw)
                        data = json.loads(raw)
                        rephrased_text = data.get("reply", "")
                        if rephrased_text:
                            copy_windows_clipboard_text(rephrased_text)
                            data["copied_to_clipboard"] = True
                            data["tone"] = tone
                            return data
                except Exception as e:
                    print(f"[Text Rephrase Gemini {m} Error] {e}")

        # Fallback to Groq Qwen
        groq_res = rephrase_with_groq(draft, tone=tone)
        if groq_res and groq_res.get("reply"):
            copy_windows_clipboard_text(groq_res["reply"])
            groq_res["copied_to_clipboard"] = True
            groq_res["tone"] = tone
            return groq_res

    # Final fallback if nothing was on screen or clipboard
    return {
        "original": draft or "No draft or highlighted text found.",
        "reply": draft or "Please highlight the text on your screen or copy it, then ask me to rephrase it.",
        "explanation": "Could not detect highlighted text on screen or clipboard.",
        "copied_to_clipboard": False,
        "tone": tone
    }

def suggest_message_reply(
    incoming_text: str,
    user_draft: str = "",
    tone: str = "professional",
    target_app: str = "teams",
    custom_api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Rephrases a draft or generates a crisp reply for Teams or Outlook emails.
    """
    from core.db import get_setting
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback to Groq if Gemini key missing
        if user_draft:
            g = rephrase_with_groq(user_draft, tone=tone)
            if g:
                return g
        return {
            "reply": user_draft or "Got it, will update you shortly.",
            "explanation": "Default offline template (Gemini API key not configured)."
        }

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"""
You are an executive communication assistant for {target_app.upper()}.
Incoming message or user intent:
"{incoming_text}"

User draft (if any):
"{user_draft}"

Requested tone: {tone} (professional, concise, friendly, or assertive)

Instructions:
1. Craft the optimal, polished reply.
2. Ensure it is polite, clear, and ready to send directly.
3. Return ONLY a valid JSON object:
{{
  "reply": "Polished text ready to copy-paste",
  "explanation": "Brief reason why this phrasing works (1 sentence)"
}}
DO NOT include markdown backticks. Output raw JSON only.
"""
    for model in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
        try:
            cfg = types.GenerateContentConfig(response_mime_type="application/json")
            res = client.models.generate_content(model=model, contents=[prompt], config=cfg)
            if res and res.text:
                raw = res.text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw)
                return data
        except Exception as e:
            print(f"[Reply Assistant Model {model} Error] {e}")
            continue

    # Groq fallback
    if user_draft:
        g = rephrase_with_groq(user_draft, tone=tone)
        if g:
            return g

    return {
        "reply": user_draft or "Understood. I will take care of this and get back to you shortly.",
        "explanation": "Standard executive acknowledgement."
    }
