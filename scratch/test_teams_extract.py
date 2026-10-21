import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import re

from core.db import get_setting

# Text transcribed from the user's uploaded Teams screenshot:
TEAMS_SCREEN_TEXT = """
1. AI Insight Investigation (Ticket: SUP-02337)
- Assigned to: Ayush & Malvi
- Issue: User reported seeing $ instead of £ for C2519 - Little Sourdough Kitchen Limited. While the KPI dashboard displays the correct currency, we need to verify whether the output was generated correctly or modified manually by the user.
- Action Required: Investigate the generation pipeline/logs and share findings by EOD.

2. STO Chatbot Updates
- Assigned to: Dhiraj / Bhumit Bhai Team
- Scope: Progress on the updates discussed on Friday.
- Deliverable: The "Create Order" action tool must be completed and tested with Bhumit Bhai's team today. Please include screenshots of the implemented changes with your EOD update.

3. STO Barscan API Deployment
- Assigned to: Dhiraj / Bhumit Bhai Team
- Scope: Verification of ProductID and PackSize API parameters.
- Deliverable: Confirm deployment status by EOD. If deployed, coordinate with Bhumit Bhai's team to confirm if any additional requirements remain on the Barscan side.

4. AI Review – Anomaly Detection
- Assigned to: Ayush
- Scope: Sales & COGS anomaly detection module.
- Deliverable: Confirm, If anomaly detection for sales & cogs require additional data or SP changes from JP, coordinate the fix and provide an EOD status update.

5. AI Insight & GL Commentary (Qwen 3.6 Formatting)
- Assigned to: Malvi (with support)
- Issue: Qwen 3.6 is not adhering to expected formatting constraints under the legacy prompt templates.
- Deliverable: Collaborate with Dhiraj & Ayush on prompt modifications to align the output with standard insight
"""

def test_extract_dhiraj_tasks():
    api_key = get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found.")
        return

    user_name = "Dhiraj"
    prompt = f"""You are an executive AI assistant for {user_name} (Senior AI / Software Engineer).
Analyze this chat message from Microsoft Teams and extract ALL action items or tasks specifically assigned to {user_name} (or their team/collaboration).

TEAMS MESSAGE:
{TEAMS_SCREEN_TEXT}

Instructions:
1. Identify all tasks where "Assigned to" includes {user_name} or where {user_name} is requested to act.
2. For each task, extract:
   - title: concise actionable title
   - project: matched project (e.g. STO AI Services, etc.)
   - description: what needs to be done, scope and deliverable
   - priority: High, Medium, or Low
   - reminder_interval_mins: suggested reminder interval (e.g. 30)
3. Ignore tasks assigned to other colleagues (e.g. Ayush, Malvi) unless {user_name} is explicitly assigned or collaborating.

Return ONLY a valid JSON list of tasks matching:
[
  {{
    "title": "Task title",
    "project": "STO AI Services",
    "description": "Details and deliverables",
    "priority": "High",
    "reminder_interval_mins": 30
  }}
]
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
            tasks = json.loads(clean)
            print(f"Successfully extracted {len(tasks)} tasks assigned to {user_name}:")
            for idx, t in enumerate(tasks, 1):
                print(f"\n[{idx}] {t.get('title')}")
                print(f"    Project: {t.get('project')}")
                print(f"    Priority: {t.get('priority')}")
                print(f"    Description: {t.get('description')}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_extract_dhiraj_tasks()
