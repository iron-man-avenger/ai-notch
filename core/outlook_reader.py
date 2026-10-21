import os
import sys
import json
import time
import subprocess
import threading
from typing import List, Dict, Any, Optional, Callable
import re

from core.db import get_setting
from core.project_manager import project_manager

PS_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "get_outlook_toasts.ps1")

class OutlookReader:
    """
    Monitors incoming Outlook emails in real-time using Windows Notification Listener
    and MAPI fallbacks, triaging each email against the user's active projects.
    """
    def __init__(self):
        self._seen_ids = set()
        self._attention_items: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def fetch_recent_emails(self) -> List[Dict[str, Any]]:
        """
        Fetches the latest email notifications directly from Windows Action Center / Toasts.
        Works with New Outlook (olk.exe) and Classic Outlook seamlessly.
        """
        if not os.path.exists(PS_SCRIPT_PATH):
            return []

        try:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS_SCRIPT_PATH]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12, check=False)
            if res.returncode == 0 and res.stdout.strip():
                out_text = res.stdout.strip()
                # If wrapped or multiple outputs, grab the JSON part
                start_bracket = out_text.find("[")
                end_bracket = out_text.rfind("]")
                if start_bracket != -1 and end_bracket != -1:
                    raw_json = out_text[start_bracket:end_bracket + 1]
                    items = json.loads(raw_json)
                    return items
        except Exception as e:
            print(f"[OutlookReader] Failed to fetch toasts: {e}")

        return []

    def triage_email_with_ai(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates whether an email requires immediate developer attention,
        identifies associated projects, and prepares a suggested action or reply.
        """
        sender = email.get("sender", "Unknown")
        subject = email.get("subject", "")
        preview = email.get("preview", "")
        combined_text = f"From: {sender}\nSubject: {subject}\nContent: {preview}"

        # 1. Match against known projects
        matched_proj = project_manager.match_project_by_text(f"{subject} {preview}")
        proj_context = ""
        proj_name = matched_proj.get("name") if matched_proj else None
        if matched_proj:
            proj_context = project_manager.get_claude_md_content(matched_proj, max_chars=1200)

        target_user = get_setting("user_name") or "Dhiraj"

        # Quick heuristic filter for obvious spam or automated noise
        lower_subj = subject.lower()
        lower_sender = sender.lower()
        if any(spam in lower_subj or spam in lower_sender for spam in ["fungus", "grades posted", "newsletter", "promotions", "no-reply", "marketing", "webinar"]):
            return {
                "needs_attention": False,
                "urgency": "low",
                "project": proj_name,
                "summary": "Automated notification/newsletter",
                "suggested_reply": "",
                "is_task": False,
                "task_title": None,
                "task_description": None,
                "task_priority": "Low"
            }

        api_key = get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Fallback heuristic
            is_task_item = any(k in lower_subj or k in preview.lower() for k in ["ticket", "task", "bug", "todo", "fix", "deploy", "implement", "create", "test"])
            needs_att = is_task_item or any(k in lower_subj or k in preview.lower() for k in ["pr", "pull request", "review", "urgent", "error", "access", "fw:", "re:", "failed", "help"])
            return {
                "needs_attention": needs_att,
                "urgency": "high" if "urgent" in lower_subj or "error" in lower_subj or "ticket" in lower_subj else "medium",
                "project": proj_name,
                "summary": subject[:80],
                "suggested_reply": f"Hi {sender.split()[0] if sender else ''}, thanks for reaching out. I am looking into this now.",
                "is_task": is_task_item,
                "task_title": f"Follow up on: {subject[:60]}" if is_task_item else None,
                "task_description": preview[:200] if is_task_item else None,
                "task_priority": "High" if "urgent" in lower_subj else "Medium"
            }

        prompt = f"""You are an executive AI co-pilot reviewing incoming Outlook emails for {target_user} (Senior AI / Software Engineer).
Determine if this incoming email requires {target_user}'s active attention, review, response, unblocking, or if it conveys an actionable task / ticket / bug fix / deliverable.

INCOMING EMAIL:
{combined_text}

ASSOCIATED PROJECT INFO:
{f"Project: {proj_name}" if proj_name else "No direct project match."}
{f"Architecture Summary:\n{proj_context}" if proj_context else ""}

Instructions:
1. Task / Ticket Identification:
   - Check if this email requests work, reports a bug, mentions a support ticket (e.g. SUP-XXXXX), asks for a review/deployment/fix, or gives deliverables.
   - If actionable work is requested, set "is_task": true, and generate a clear, professional English "task_title" (max 10 words) and "task_description".
   - If purely informational, conversation, or greeting, set "is_task": false.
2. Needs Attention & Urgency:
   - Set "needs_attention": true if it requires an engineer's action, response, or review.
   - Set "urgency": "high" (blocker/error/ticket/urgent PR/client issue) or "medium" (update/inquiry) or "low" (automated/FYI).
3. Suggested Reply:
   - Draft a polite, concise, professional reply in executive English (or empty string if not applicable).

Output ONLY valid JSON matching this schema:
{{
  "needs_attention": true or false,
  "urgency": "high" or "medium" or "low",
  "project": "{proj_name or 'General / Operations'}",
  "reason": "1-line explanation why this requires attention or why not",
  "summary": "Concise 1-sentence summary of the email",
  "suggested_reply": "Professional, concise suggested reply (or empty string)",
  "is_task": true or false,
  "task_title": "Concise actionable title in English if is_task is true, else null",
  "task_description": "Clear scope, ticket ID, or deliverable needed if is_task is true, else null",
  "task_priority": "High" or "Medium" or "Low"
}}
DO NOT wrap in markdown or commentary. Output raw JSON only.
"""

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            if resp and resp.text:
                clean = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                clean = re.sub(r"\s*```$", "", clean)
                data = json.loads(clean)
                return data
        except Exception as e:
            print(f"[Outlook AI Triage Warning] {e}")

        # Fallback if LLM call fails
        return {
            "needs_attention": True,
            "urgency": "medium",
            "project": proj_name or "General",
            "reason": "Direct message received",
            "summary": subject,
            "suggested_reply": "Thank you, noted."
        }

    def process_latest(self) -> List[Dict[str, Any]]:
        """Fetches unseen emails, triages them, and returns newly detected attention items."""
        emails = self.fetch_recent_emails()
        new_attention = []

        with self._lock:
            # Filter unseen
            unseen = [item for item in emails if str(item.get("id")) not in self._seen_ids]
            # Prioritize the most recent 3 for deep LLM triage to keep latency low (<4s)
            for idx, item in enumerate(unseen):
                item_id = str(item.get("id"))
                self._seen_ids.add(item_id)
                
                if idx < 3:
                    triage = self.triage_email_with_ai(item)
                else:
                    # Fast heuristic for older backlogged items
                    subj = (item.get("subject") or "").lower()
                    needs_att = any(k in subj for k in ["pr", "review", "bug", "error", "urgent", "access", "fw:", "re:"])
                    triage = {
                        "needs_attention": needs_att,
                        "urgency": "medium",
                        "project": None,
                        "reason": "Recent work email",
                        "summary": item.get("subject"),
                        "suggested_reply": "Thank you, reviewing this."
                    }

                record = {
                    "id": item_id,
                    "sender": item.get("sender"),
                    "subject": item.get("subject"),
                    "preview": item.get("preview"),
                    "created": item.get("created"),
                    "needs_attention": triage.get("needs_attention", False),
                    "urgency": triage.get("urgency", "low"),
                    "project": triage.get("project"),
                    "reason": triage.get("reason", ""),
                    "summary": triage.get("summary", item.get("subject")),
                    "suggested_reply": triage.get("suggested_reply", ""),
                    "is_task": triage.get("is_task", False),
                    "task_title": triage.get("task_title"),
                    "task_description": triage.get("task_description"),
                    "task_priority": triage.get("task_priority", "Medium")
                }

                if record["needs_attention"]:
                    self._attention_items.insert(0, record)
                    # Keep max 30 items
                    if len(self._attention_items) > 30:
                        self._attention_items.pop()
                    new_attention.append(record)

        return new_attention

    def get_attention_items(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._attention_items)

    def mark_item_handled(self, item_id: str):
        with self._lock:
            self._attention_items = [it for it in self._attention_items if str(it.get("id")) != str(item_id)]

class OutlookWatcher:
    """Background polling thread for Outlook notifications."""
    def __init__(self, check_interval_seconds: float = 20.0):
        self.interval = check_interval_seconds
        self.reader = OutlookReader()
        self.on_attention_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[OutlookWatcher] Started background monitoring (interval: {self.interval}s)")

    def stop(self):
        self._running = False

    def _run(self):
        # Initial run after 5s startup delay
        time.sleep(5)
        while self._running:
            try:
                new_items = self.reader.process_latest()
                for it in new_items:
                    if self.on_attention_callback:
                        self.on_attention_callback(it)
            except Exception as e:
                print(f"[OutlookWatcher Loop Error] {e}")

            time.sleep(self.interval)

outlook_reader = OutlookReader()
outlook_watcher = OutlookWatcher(check_interval_seconds=20.0)
