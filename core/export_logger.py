import os
import atexit
from datetime import datetime
from typing import List, Dict, Any

from core.db import get_today_activities, get_today_app_summary, get_tasks

DAILY_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "daily_logs")

def ensure_logs_dir():
    os.makedirs(DAILY_LOGS_DIR, exist_ok=True)

def format_duration(seconds: int) -> str:
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    if hrs > 0:
        return f"{hrs}h {mins}m"
    return f"{mins}m"

def save_daily_markdown_log():
    """Auto-saves all tracked daily activities and tasks into a clean Markdown log in daily_logs/ folder."""
    try:
        ensure_logs_dir()
        today_str = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(DAILY_LOGS_DIR, f"activity_{today_str}.md")

        app_summary = get_today_app_summary()
        tasks = get_tasks()
        activities = get_today_activities()

        total_tracked_sec = sum(a["total_seconds"] for a in app_summary)

        lines = [
            f"# 📅 Work Log - {today_str}",
            f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}",
            f"**Total Tracked Time:** {format_duration(total_tracked_sec)}",
            "",
            "## ⏱️ Time Spent by Application",
            "| Application | Total Time | Percentage |",
            "|---|---|---|"
        ]

        for app in app_summary:
            pct = (app["total_seconds"] / total_tracked_sec * 100) if total_tracked_sec > 0 else 0
            lines.append(f"| **{app['app_name']}** | {format_duration(app['total_seconds'])} | {pct:.1f}% |")

        lines.append("")
        lines.append("## 📌 Action Items & Tasks")
        if tasks:
            for t in tasks:
                status_icon = "✅" if t["status"] == "completed" else "⏳"
                source_tag = f" `[{t.get('source', 'Manual')}]`" if t.get('source') else ""
                lines.append(f"- {status_icon} **{t['title']}**{source_tag}")
                if t.get("description"):
                    lines.append(f"  > {t['description']}")
        else:
            lines.append("_No tasks recorded yet today._")

        lines.append("")
        lines.append("## 🔍 Detailed Activity Breakdown")
        for act in activities[-30:]: # Last 30 distinct window sessions
            last_seen = act.get('last_seen', '')[:19] if act.get('last_seen') else ''
            duration_sec = act.get('total_seconds', 0)
            lines.append(f"- `{last_seen}` **{act['app_name']}**: {act['window_title']} ({format_duration(duration_sec)})")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    except Exception as e:
        print(f"[ExportLogger Error] Failed to write daily log: {e}")

def save_ai_bulleted_summary(summary_proposals: List[Dict[str, Any]]) -> str:
    """Saves a structured AI summary with bullet points into daily_logs/summary_YYYY-MM-DD.md."""
    try:
        ensure_logs_dir()
        today_str = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(DAILY_LOGS_DIR, f"summary_{today_str}.md")

        lines = [
            f"# 🎯 Daily Work Summary - {today_str}",
            f"**Generated:** {datetime.now().strftime('%H:%M:%S')}",
            "",
            "## 📌 Key Accomplishments & Tasks",
            ""
        ]

        for idx, task in enumerate(summary_proposals, 1):
            lines.append(f"### {idx}. {task.get('title', 'Work Task')} (`{task.get('time_spent', '0m')}`)")
            lines.append(f"{task.get('description', '')}")
            if task.get("tags"):
                tags_str = " ".join([f"`#{t}`" for t in task["tags"]])
                lines.append(f"\n*Tags:* {tags_str}")
            lines.append("")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path
    except Exception as e:
        print(f"[ExportLogger Error] Failed to write AI summary: {e}")
        return ""

# Auto-save whenever Python shuts down
atexit.register(save_daily_markdown_log)
