import os
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from core.db import get_setting

load_dotenv()

def format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

IGNORED_SYSTEM_PROCESSES = {
    "shellexperiencehost", "searchhost", "lockapp", "searchapp", 
    "systemsettings", "applicationframehost", "taskmgr", "textinputhost",
    "screensketch", "snippingtool", "startmenuexperiencehost", "ctfmon",
    "dwm", "idle", "unknown", "openwith", "system", "runtimebroker",
    "backgroundtaskhost", "securityhealthsystray", "smartscreen", "explorer"
}

def is_meaningful_activity(act: Dict[str, Any]) -> bool:
    app = act.get("app_name", "").lower().strip()
    secs = act.get("total_seconds", 0)
    # Ignore any transient activity under 60 seconds (no 0m tasks)
    if secs < 60:
        return False
    clean_app = app.replace(".exe", "")
    if clean_app in IGNORED_SYSTEM_PROCESSES:
        return False
    return True

def rule_based_summary(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups activities by application and prominent window titles into clean R&D tasks."""
    valid_activities = [a for a in activities if is_meaningful_activity(a)]
    if not valid_activities:
        return [{
            "title": "Research & Development Engineering",
            "description": "- Core feature implementation and code refactoring\n- Technical documentation review and debugging",
            "tags": ["Engineering", "R&D"],
            "time_spent": "1h"
        }]

    app_groups: Dict[str, Dict[str, Any]] = {}
    for act in valid_activities:
        app = act.get("app_name", "Unknown")
        title = act.get("window_title", "")
        secs = act.get("total_seconds", 0)
        
        if app not in app_groups:
            app_groups[app] = {"total_seconds": 0, "titles": {}}
        app_groups[app]["total_seconds"] += secs
        app_groups[app]["titles"][title] = app_groups[app]["titles"].get(title, 0) + secs

    tasks = []
    for app, data in sorted(app_groups.items(), key=lambda x: x[1]["total_seconds"], reverse=True):
        total_time = format_seconds(data["total_seconds"])
        top_titles = sorted(data["titles"].items(), key=lambda x: x[1], reverse=True)[:4]
        
        # Build description bullets
        bullets = []
        for t, s in top_titles:
            clean_t = t.split(" - ")[0] if " - " in t else t
            bullets.append(f"- {clean_t} ({format_seconds(s)})")

        task_title = f"R&D & Engineering in {app}"
        if "Code" in app or "Antigravity" in app:
            task_title = f"Development & Debugging in {app}"
        elif "Chrome" in app or "Edge" in app:
            task_title = f"Technical Research & Pull Request Reviews in {app}"
        elif "Teams" in app:
            task_title = f"Team Collaboration & Technical Meetings in {app}"
        elif "Postman" in app:
            task_title = f"API Testing & Integration in {app}"

        tasks.append({
            "title": task_title,
            "description": "\n".join(bullets),
            "tags": [app.replace(" ", "")],
            "time_spent": total_time
        })

    return tasks

def summarize_activities_with_gemini(activities: List[Dict[str, Any]], custom_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Uses Gemini 3.8/flash-lite to group raw logs into high-level Research & Development tasks."""
    valid_activities = [a for a in activities if is_meaningful_activity(a)]
    if not valid_activities:
        return rule_based_summary([])

    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return rule_based_summary(valid_activities)

    # Format activity logs into a concise prompt text
    log_lines = []
    for a in valid_activities[:40]: # Top 40 meaningful activities
        log_lines.append(f"- App: {a.get('app_name')}, Title: {a.get('window_title')}, Time: {format_seconds(a.get('total_seconds', 0))}")
    raw_logs = "\n".join(log_lines)

    prompt = f"""
You are a Principal Engineering & R&D Lead reviewing today's developer activity logs.
Below is the raw timeline of applications and documents worked on today:
---
{raw_logs}
---

Your instructions:
1. Synthesize these activities into 2 to 5 high-impact, professional Research & Development (R&D) work items suitable for Azure DevOps.
2. Focus strictly on real engineering: Software development, Architecture, API integration, Bug fixes, Code reviews, and Technical meetings.
3. Completely exclude any incidental system utilities or empty tasks.
4. Return ONLY a valid JSON list of objects matching this exact structure:
[
  {{
    "title": "Clear action-oriented work item title (e.g. Coucou Desktop Dock UI & Animation Engineering)",
    "description": "- Built responsive top-notch dock animations\\n- Integrated native Windows clipboard and eye tracking",
    "tags": ["Frontend", "R&D"],
    "time_spent": "2h 30m"
  }}
]

DO NOT wrap the response in markdown backticks or commentary. Output raw JSON only.
"""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Test models supported by Google GenAI endpoint
        for model_name in ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.6-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    text = response.text.strip()
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                    parsed = json.loads(text)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
            except Exception as model_err:
                print(f"[Gemini Summarizer] {model_name} failed: {model_err}, trying fallback...")
                continue
        
        return rule_based_summary(valid_activities)
    except Exception as e:
        print(f"[Gemini Summarizer Warning] {e}. Falling back to rule-based summary.")
        return rule_based_summary(valid_activities)

def ask_assistant_gemini_full(
    message: str, 
    activities: Optional[List[Dict[str, Any]]] = None, 
    custom_api_key: Optional[str] = None,
    file_name: Optional[str] = None,
    file_content: Optional[str] = None,
    model_override: Optional[str] = None
) -> Dict[str, Any]:
    """Answers user queries using Gemini with context about today's work, attached files, and optional web search results."""
    from datetime import datetime
    api_key = custom_api_key or get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "reply": "Please configure your Gemini API Key in Settings (⚙️) to chat with me!",
            "sources": [],
            "is_research": False
        }
    
    activity_summary = ""
    if activities:
        valid_acts = [a for a in activities if is_meaningful_activity(a)]
        top_items = []
        for a in valid_acts[:15]:
            top_items.append(f"- {a.get('app_name')}: {a.get('window_title')} ({format_seconds(a.get('total_seconds', 0))})")
        activity_summary = "\nToday's tracked activity so far:\n" + "\n".join(top_items)

    # Attached file context (from Coucou file drop)
    file_context_str = ""
    if file_name and file_content:
        file_context_str = f"\n[User Attached File: {file_name}]\n```\n{file_content[:15000]}\n```\n"

    # Automatic Web Research Integration
    web_context = ""
    search_sources: List[Dict[str, Any]] = []
    is_research = any(w in message.lower() for w in ["research", "search web", "search on web", "look up", "web search", "google", "find on web", "latest", "what is", "tell me about"])
    if is_research:
        try:
            import re
            from core.web_searcher import search_web_organic, format_search_results_for_llm
            q_clean = re.sub(r"(?i)\b(please|research|search|web|on|about|google|find|for|look|up|the|can you)\b", " ", message).strip()
            if not q_clean or len(q_clean) < 3:
                q_clean = message
            search_sources = search_web_organic(q_clean, max_results=5)
            if search_sources:
                web_context = f"\nLive Web Search Results for '{q_clean}':\n" + format_search_results_for_llm(search_sources) + "\n"
        except Exception as e_s:
            print(f"[Chat Web Search Warning] {e_s}")

    now_dt = datetime.now()
    prompt = f"""
You are Mochi, a smart, friendly desktop productivity AI assistant inside a Coucou-style desktop notch.
Current Date & Time: {now_dt.strftime('%A, %B %d, %Y, %I:%M %p')}
Today is {now_dt.strftime('%A')}, {now_dt.strftime('%d %B %Y')}.
{activity_summary}
{file_context_str}
{web_context}
User query: {message}

Instructions:
- Keep your answer punchy, clear, and formatted in clean markdown bullet points or short paragraphs.
- If an attached file is provided above, analyze, summarize, or refactor it based on the user's instructions.
- If live web search results are provided above, synthesize them thoroughly to answer the user's research request.
- If asked what day or date it is, use the exact Current Date & Time provided above.
- If the user asks about what they worked on, their time, or tasks, use the tracked context above.
- Provide actionable, polite answers.
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        candidate_models = ["gemini-flash-latest", "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
        if model_override and model_override not in candidate_models:
            candidate_models.insert(0, model_override)
        elif model_override:
            candidate_models.remove(model_override)
            candidate_models.insert(0, model_override)

        for model in candidate_models:
            try:
                res = client.models.generate_content(model=model, contents=prompt)
                if res and res.text:
                    return {
                        "reply": res.text.strip(),
                        "sources": search_sources,
                        "is_research": is_research
                    }
            except Exception:
                continue
        return {
            "reply": "Could not reach Gemini service. Please check your network connection.",
            "sources": search_sources,
            "is_research": is_research
        }
    except Exception as e:
        return {
            "reply": f"Gemini error: {str(e)}",
            "sources": search_sources,
            "is_research": is_research
        }

def ask_assistant_gemini(message: str, activities: Optional[List[Dict[str, Any]]] = None, custom_api_key: Optional[str] = None) -> str:
    """Answers quick user queries using Gemini with context about today's work."""
    res = ask_assistant_gemini_full(message, activities, custom_api_key)
    return res.get("reply", "")


