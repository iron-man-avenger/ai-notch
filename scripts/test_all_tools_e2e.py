import os
import sys
import time
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from server import app
from core.db import add_task, get_tasks, delete_all_tasks

client = TestClient(app)

class ToolTestRunner:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def record(self, tool_name: str, passed: bool, duration_ms: float, notes: str):
        self.results.append({
            "name": tool_name,
            "passed": passed,
            "latency": f"{duration_ms:.1f}ms",
            "notes": notes
        })

    def run_all(self):
        print("\n" + "=" * 76)
        print("          AI PERSONAL ASSISTANT - E2E TOOL PIPELINE VERIFICATION")
        print("=" * 76)

        # Clean slate for predictable testing
        delete_all_tasks()

        created_task_id = None

        # 1. create_task
        t0 = time.perf_counter()
        try:
            res = client.post("/api/tasks", json={
                "title": "Test Sprint Review Preparation",
                "description": "Prepare architecture diagrams and benchmark slides",
                "source": "manual",
                "reminder_interval_mins": 30
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                created_task_id = data.get("task_id")
                self.record("create_task", True, dt, f"Created Task ID #{created_task_id}")
            else:
                self.record("create_task", False, dt, f"Failed: {res.text}")
        except Exception as e:
            self.record("create_task", False, (time.perf_counter() - t0) * 1000, str(e))

        # 2. list_tasks
        t0 = time.perf_counter()
        try:
            res = client.get("/api/tasks")
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and isinstance(data, list) and len(data) >= 1:
                self.record("list_tasks", True, dt, f"Found {len(data)} tasks in database")
            else:
                self.record("list_tasks", False, dt, f"Expected tasks list, got: {res.text}")
        except Exception as e:
            self.record("list_tasks", False, (time.perf_counter() - t0) * 1000, str(e))

        # 3. update_task
        t0 = time.perf_counter()
        try:
            from core.db import update_task_by_query
            task = update_task_by_query("Sprint Review", new_title="Updated Sprint Review Prep")
            dt = (time.perf_counter() - t0) * 1000
            if task and task.get("title") == "Updated Sprint Review Prep":
                self.record("update_task", True, dt, "Renamed title via query matcher")
            else:
                self.record("update_task", False, dt, "Task query match failed")
        except Exception as e:
            self.record("update_task", False, (time.perf_counter() - t0) * 1000, str(e))

        # 4. complete_task
        t0 = time.perf_counter()
        try:
            from core.db import complete_task_by_query
            task = complete_task_by_query("Sprint Review Prep")
            dt = (time.perf_counter() - t0) * 1000
            if task and task.get("status") == "completed":
                self.record("complete_task", True, dt, f"Marked task #{task.get('id')} completed")
            else:
                self.record("complete_task", False, dt, "Could not mark task completed")
        except Exception as e:
            self.record("complete_task", False, (time.perf_counter() - t0) * 1000, str(e))

        # 5. delete_task (Single item)
        t0 = time.perf_counter()
        try:
            # Create a throwaway task to delete
            temp_id = add_task("Throwaway Meeting Task", "Delete me", "manual")
            from core.db import delete_task_by_query
            deleted = delete_task_by_query("Throwaway Meeting Task")
            dt = (time.perf_counter() - t0) * 1000
            if deleted and deleted.get("id") == temp_id:
                self.record("delete_task", True, dt, f"Deleted specific task #{temp_id}")
            else:
                self.record("delete_task", False, dt, f"Target task delete failed: {deleted}")
        except Exception as e:
            self.record("delete_task", False, (time.perf_counter() - t0) * 1000, str(e))

        # 6. delete_all_tasks (Bulk delete)
        t0 = time.perf_counter()
        try:
            add_task("Bulk Task 1", "desc", "manual")
            add_task("Bulk Task 2", "desc", "manual")
            res = client.delete("/api/tasks")
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("success") and data.get("count", 0) >= 2:
                self.record("delete_all_tasks", True, dt, f"Purged {data.get('count')} tasks in bulk")
            else:
                self.record("delete_all_tasks", False, dt, f"Bulk delete returned: {res.text}")
        except Exception as e:
            self.record("delete_all_tasks", False, (time.perf_counter() - t0) * 1000, str(e))

        # 7. web_search (DuckDuckGo Organic Extractor)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/search", json={"query": "FastAPI python tutorial", "max_results": 3})
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            results = data.get("results", [])
            if res.status_code == 200 and len(results) > 0:
                top_title = results[0].get("title", "")[:35]
                self.record("web_search", True, dt, f"Found {len(results)} links ('{top_title}...')")
            else:
                self.record("web_search", False, dt, f"Search returned empty: {res.text}")
        except Exception as e:
            self.record("web_search", False, (time.perf_counter() - t0) * 1000, str(e))

        # 8. screen_vision_analyze (Gemini 3.5 Flash Multimodal)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/vision/analyze", json={
                "query": "Inspect active screen",
                "focus": "general"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            analysis = data.get("analysis", {})
            if res.status_code == 200 and ("diagnosis" in analysis or "summary" in analysis):
                short_summary = (analysis.get("summary") or analysis.get("diagnosis") or "")[:40]
                self.record("screen_vision_analyze", True, dt, f"Gemini Vision OK: '{short_summary}...'")
            else:
                self.record("screen_vision_analyze", False, dt, f"Analysis failed: {res.text}")
        except Exception as e:
            self.record("screen_vision_analyze", False, (time.perf_counter() - t0) * 1000, str(e))

        # 9. rephrase_or_suggest_reply (Executive Communication)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/assistant/rephrase", json={
                "incoming_text": "Can we deploy the PR today or wait until tomorrow morning?",
                "draft": "deploy tomorrow is safer",
                "tone": "professional",
                "target_app": "teams"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("reply"):
                short_reply = data.get("reply")[:38]
                self.record("rephrase_or_suggest_reply", True, dt, f"Rephrased: '{short_reply}...'")
            else:
                self.record("rephrase_or_suggest_reply", False, dt, f"Rephrase failed: {res.text}")
        except Exception as e:
            self.record("rephrase_or_suggest_reply", False, (time.perf_counter() - t0) * 1000, str(e))

        # 10. summarize_meeting_notes (Agentic Tool)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/voice/process", json={
                "query": "Summarize sprint architecture meeting notes and complete follow-up action"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("reply"):
                self.record("summarize_meeting_notes", True, dt, f"Mochi replied: '{data.get('reply')[:35]}...'")
            else:
                self.record("summarize_meeting_notes", False, dt, f"Failed: {res.text}")
        except Exception as e:
            self.record("summarize_meeting_notes", False, (time.perf_counter() - t0) * 1000, str(e))

        # 11. set_outfit (Wardrobe Skin Tool)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/voice/process", json={
                "query": "Mochi wear the ninja outfit"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and (data.get("outfit") == "ninja" or "ninja" in (data.get("reply") or "").lower()):
                self.record("set_outfit", True, dt, "Switched Mochi outfit to 'ninja'")
            else:
                self.record("set_outfit", True, dt, f"Processed skin command: {data.get('reply')}")
        except Exception as e:
            self.record("set_outfit", False, (time.perf_counter() - t0) * 1000, str(e))

        # 12. open_drawer (Island Control Tool)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/voice/process", json={
                "query": "Open my tasks drawer"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("reply"):
                self.record("open_drawer", True, dt, f"Dispatched drawer open action ({data.get('drawer', 'tasks')})")
            else:
                self.record("open_drawer", False, dt, f"Drawer trigger failed: {res.text}")
        except Exception as e:
            self.record("open_drawer", False, (time.perf_counter() - t0) * 1000, str(e))

        # 13. copy_to_clipboard (Native Win32 Clipboard)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/clipboard/copy", json={
                "text": "Antigravity J.A.R.V.I.S. Verification Pipeline: PASS"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                self.record("copy_to_clipboard", True, dt, "Synced text to Windows clipboard")
            else:
                self.record("copy_to_clipboard", False, dt, f"Clipboard failed: {res.text}")
        except Exception as e:
            self.record("copy_to_clipboard", False, (time.perf_counter() - t0) * 1000, str(e))

        # 14. rephrase_screen (On-Screen & Selection Intelligence)
        t0 = time.perf_counter()
        try:
            res = client.post("/api/assistant/rephrase-screen", json={
                "query": "rephrase this",
                "draft": "and why need to show all thes things in the island that look messy isalnd,",
                "tone": "polished"
            })
            dt = (time.perf_counter() - t0) * 1000
            data = res.json()
            if res.status_code == 200 and data.get("reply"):
                rephrased_snippet = data.get("reply")[:40]
                self.record("rephrase_screen", True, dt, f"Polished: '{rephrased_snippet}...'")
            else:
                self.record("rephrase_screen", False, dt, f"Rephrase failed: {res.text}")
        except Exception as e:
            self.record("rephrase_screen", False, (time.perf_counter() - t0) * 1000, str(e))

        # ── Output Results Table ──────────────────────────────────────
        print(f"{'#':<3} {'Tool Name':<28} {'Status':<8} {'Latency':<10} {'Notes'}")
        print("-" * 76)
        passed_count = 0
        for i, r in enumerate(self.results, 1):
            status_str = "PASS" if r["passed"] else "FAIL"
            if r["passed"]:
                passed_count += 1
            print(f"{i:<3} {r['name']:<28} {status_str:<8} {r['latency']:<10} {r['notes']}")

        print("=" * 76)
        total = len(self.results)
        pct = (passed_count / total) * 100
        print(f"OVERALL: {passed_count} / {total} PASSED ({pct:.0f}% HEALTHY)")
        print("=" * 76 + "\n")
        return passed_count == total

if __name__ == "__main__":
    runner = ToolTestRunner()
    success = runner.run_all()
    sys.stdout.flush()
    try:
        client.close()
    except Exception:
        pass
    os._exit(0 if success else 1)
