import asyncio
import json
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import threading
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from core.db import (
    init_db, get_today_activities, get_today_app_summary,
    add_task, get_tasks, update_task_status, update_task_interval, delete_task,
    set_task_devops_id, get_all_settings, get_setting, set_setting,
    find_task_by_query, complete_task_by_query, delete_task_by_query, update_task_by_query,
    delete_all_tasks
)
from core.tracker import ActivityTracker
from core.teams_detector import TeamsCallDetector
from core.ai_summarizer import summarize_activities_with_gemini, ask_assistant_gemini, ask_assistant_gemini_full
from core.devops_client import AzureDevOpsClient
from core.news_fetcher import fetch_relevant_news
from core.export_logger import save_daily_markdown_log, save_ai_bulleted_summary
from core.teams_task_detector import TeamsTaskWatcher, analyze_teams_text_with_gemini
from core.voice_listener import WindowsJarvisListener
from core.web_searcher import search_web_organic, format_search_results_for_llm
from core.screen_vision import capture_desktop_bytes, analyze_screen_with_gemini, suggest_message_reply
from core.document_extractor import document_extractor
from core.rag_engine import rag_engine
from core.rag_chat import generate_rag_response, stream_rag_tokens

# Initialize DB
init_db()

app = FastAPI(title="AI Personal Assistant Dock API")

# Path to built frontend
if getattr(sys, 'frozen', False):
    FRONTEND_DIST = os.path.join(sys._MEIPASS, "frontend", "dist")
else:
    FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# Enable CORS for React Vite frontend (localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background Engines
tracker = ActivityTracker(poll_interval=2.0)
teams_detector = TeamsCallDetector(check_interval=3.0)

# Connected WebSocket clients (for React dock UI)
connected_clients: List[WebSocket] = []
main_loop: Optional[asyncio.AbstractEventLoop] = None

def broadcast_sync(message: Dict[str, Any]):
    """Helper to broadcast messages to all connected WebSocket clients from any thread safely."""
    global main_loop
    loop = main_loop
    if not loop or not loop.is_running():
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

    if loop and loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(_broadcast_async(message), loop)
        except Exception:
            pass

async def _broadcast_async(message: Dict[str, Any]):
    data_str = json.dumps(message)
    dead_clients = []
    for ws in list(connected_clients):
        try:
            await ws.send_text(data_str)
        except Exception:
            dead_clients.append(ws)
    for dc in dead_clients:
        if dc in connected_clients:
            connected_clients.remove(dc)

def generate_screen_thumbnail(screen_bytes: bytes) -> Optional[str]:
    """Generates a compact base64 JPEG thumbnail of the captured desktop screen."""
    if not screen_bytes:
        return None
    try:
        import base64
        from PySide6.QtGui import QImage
        from PySide6.QtCore import QBuffer, QIODevice, Qt
        qimg = QImage.fromData(screen_bytes)
        if not qimg.isNull() and qimg.width() > 10:
            thumb = qimg.scaled(240, 135, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            thumb.save(buf, "JPEG", 70)
            return base64.b64encode(bytes(buf.data().data())).decode('utf-8')
    except Exception as e:
        print("[Thumbnail Generation Warning]", e)
    return None

# Wire callbacks from Tracker & Teams Detector to WebSocket
def on_tracker_tick(activity: Dict[str, Any]):
    broadcast_sync({
        "type": "ACTIVITY_TICK",
        "data": activity
    })

def on_teams_call_started(subject: str):
    broadcast_sync({
        "type": "TEAMS_CALL_STARTED",
        "data": {"subject": subject}
    })

def on_teams_call_ended(subject: str):
    # Also log a system reminder task prompt
    broadcast_sync({
        "type": "TEAMS_CALL_ENDED",
        "data": {"subject": subject}
    })

teams_task_watcher = TeamsTaskWatcher(check_interval=1.5)

class TaskReminderWatcher:
    """Proactively checks pending tasks and broadcasts reminders over WebSocket."""
    def __init__(self, check_interval_seconds: float = 30.0):
        self.check_interval = check_interval_seconds
        self.is_running = False
        self.last_reminded_tasks: Dict[int, float] = {}
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _run_loop(self):
        import time
        from datetime import datetime
        while self.is_running:
            try:
                self._check_reminders()
            except Exception as e:
                print(f"[TaskReminderWatcher Warning] {e}")
            time.sleep(self.check_interval)

    def _check_reminders(self):
        import time
        from datetime import datetime
        pending = get_tasks(status="pending")
        if not pending:
            return
        now_ts = time.time()
        for task in pending:
            tid = task["id"]
            interval_mins = task.get("reminder_interval_mins") or 30
            interval_sec = max(60, interval_mins * 60) # Support 1m, 2m, 5m, 15m, 30m, 60m
            last_ts = self.last_reminded_tasks.get(tid, 0)
            
            created_str = task.get("created_at")
            created_ts = now_ts
            if created_str:
                try:
                    created_ts = datetime.fromisoformat(created_str).timestamp()
                except Exception:
                    pass

            needs_remind = False
            # Remind if at least interval_sec has passed since creation or last reminder
            if last_ts == 0 and (now_ts - created_ts) >= interval_sec:
                needs_remind = True
            elif last_ts > 0 and (now_ts - last_ts) >= interval_sec:
                needs_remind = True

            if needs_remind:
                self.last_reminded_tasks[tid] = now_ts
                broadcast_sync({
                    "type": "TASK_REMINDER",
                    "data": {
                        "task": task,
                        "title": task["title"],
                        "message": f"Task reminder: '{task['title']}'",
                        "interval_mins": interval_mins,
                        "silent": True
                    }
                })
                break

task_reminder_watcher = TaskReminderWatcher(check_interval_seconds=15.0)

def on_teams_task_detected(task_data: Dict[str, Any]):
    broadcast_sync({
        "type": "TEAMS_TASK_PROPOSAL",
        "data": task_data
    })

tracker.on_tick_callback = on_tracker_tick
teams_detector.on_call_started = on_teams_call_started
teams_detector.on_call_ended = on_teams_call_ended
teams_task_watcher.on_task_detected = on_teams_task_detected

from core.auto_approver import auto_approver
def on_auto_approval_event(record):
    broadcast_sync({
        "type": "AUTO_APPROVAL_TRIGGERED",
        "data": record
    })
auto_approver.on_approval_callback = on_auto_approval_event

@app.on_event("startup")
async def startup_event():
    global main_loop
    try:
        main_loop = asyncio.get_running_loop()
    except Exception:
        pass
    tracker.start()
    teams_detector.start()
    teams_task_watcher.start()
    task_reminder_watcher.start()
    # Note: Voice engine does NOT start by default. Starts on click only from chat!
    print("[Assistant Server] Tracker, Teams detector, Task watcher, and Reminder engines started.")
    
    # Warmup FastEmbed RAG model in background so first query has zero cold-start delay
    def warmup_rag():
        try:
            from core.embeddings import get_embedding
            get_embedding("warmup")
            print("[RAG Engine] Warmup complete. High-speed vector retrieval ready.")
        except Exception:
            pass
    threading.Thread(target=warmup_rag, daemon=True).start()

@app.on_event("shutdown")
def shutdown_event():
    tracker.stop()
    teams_detector.stop()
    teams_task_watcher.stop()
    task_reminder_watcher.stop()
    jarvis_listener.stop()

# ----------------- REST API Endpoints -----------------

@app.get("/api/status")
def get_status():
    status = tracker.get_status()
    pending_tasks = get_tasks(status="pending")
    return {
        "tracker": status,
        "in_meeting": teams_detector.in_meeting,
        "meeting_subject": teams_detector.meeting_subject,
        "pending_tasks_count": len(pending_tasks)
    }

@app.get("/api/activities/today")
def get_activities():
    return get_today_activities()

@app.get("/api/activities/summary")
def get_app_summary():
    return get_today_app_summary()

# Tasks
class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    source: str = "manual"
    reminder_interval_mins: int = 30

@app.get("/api/tasks")
def list_tasks():
    return get_tasks()

@app.post("/api/tasks")
def create_task(req: TaskCreateRequest):
    task_id = add_task(
        title=req.title,
        description=req.description,
        source=req.source,
        reminder_interval_mins=req.reminder_interval_mins
    )
    # Broadcast to notify dock UI in real-time
    broadcast_sync({
        "type": "TASK_CREATED",
        "data": {
            "id": task_id,
            "title": req.title,
            "description": req.description,
            "source": req.source,
            "pending_count": len(get_tasks(status="pending"))
        }
    })
    return {"success": True, "task_id": task_id}

@app.post("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: int):
    tasks = get_tasks()
    current = next((t for t in tasks if t["id"] == task_id), None)
    if not current:
        raise HTTPException(status_code=404, detail="Task not found")
    new_status = "completed" if current["status"] == "pending" else "pending"
    update_task_status(task_id, new_status)
    broadcast_sync({
        "type": "TASK_UPDATED",
        "data": {"id": task_id, "status": new_status, "pending_count": len(get_tasks(status="pending"))}
    })
    return {"success": True, "status": new_status}

class TaskIntervalRequest(BaseModel):
    reminder_interval_mins: int

@app.post("/api/tasks/{task_id}/interval")
def set_task_interval(task_id: int, req: TaskIntervalRequest):
    update_task_interval(task_id, req.reminder_interval_mins)
    if hasattr(task_reminder_watcher, "last_reminded_tasks"):
        task_reminder_watcher.last_reminded_tasks.pop(task_id, None)
    broadcast_sync({
        "type": "TASK_UPDATED",
        "data": {
            "id": task_id,
            "reminder_interval_mins": req.reminder_interval_mins,
            "pending_count": len(get_tasks(status="pending"))
        }
    })
    return {"success": True, "reminder_interval_mins": req.reminder_interval_mins}

class TaskExtendRequest(BaseModel):
    mins: int = 5

@app.post("/api/tasks/{task_id}/extend")
def extend_task(task_id: int, req: TaskExtendRequest = TaskExtendRequest()):
    import time
    tasks = get_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    current_interval = task.get("reminder_interval_mins") or 30
    new_interval = current_interval + req.mins
    update_task_interval(task_id, new_interval)
    
    if hasattr(task_reminder_watcher, "last_reminded_tasks"):
        task_reminder_watcher.last_reminded_tasks[task_id] = time.time()
        
    broadcast_sync({
        "type": "TASK_UPDATED",
        "data": {
            "id": task_id,
            "reminder_interval_mins": new_interval,
            "extended_mins": req.mins,
            "pending_count": len(get_tasks(status="pending"))
        }
    })
    return {"success": True, "task_id": task_id, "new_interval_mins": new_interval, "extended_mins": req.mins}

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    delete_task(task_id)
    broadcast_sync({
        "type": "TASK_DELETED",
        "data": {"id": task_id, "pending_count": len(get_tasks(status="pending"))}
    })
    return {"success": True}

@app.delete("/api/tasks")
def remove_all_tasks():
    count = delete_all_tasks()
    broadcast_sync({
        "type": "ALL_TASKS_DELETED",
        "data": {"count": count, "pending_count": 0}
    })
    return {"success": True, "count": count}

# EOD & Gemini Summarizer
@app.post("/api/eod/generate")
def generate_eod():
    activities = get_today_activities()
    tasks = summarize_activities_with_gemini(activities)
    saved_path = save_ai_bulleted_summary(tasks)
    return {"tasks": tasks, "saved_path": saved_path}

class ChatAskRequest(BaseModel):
    message: str
    file_name: Optional[str] = None
    file_content: Optional[str] = None
    model: Optional[str] = None
    doc_ref: Optional[str] = None

class RAGUploadRequest(BaseModel):
    file_name: str
    file_content: Optional[str] = None
    file_base64: Optional[str] = None

@app.post("/api/rag/upload")
def api_rag_upload(req: RAGUploadRequest):
    import base64
    file_bytes = b""
    if req.file_base64:
        try:
            file_bytes = base64.b64decode(req.file_base64)
        except Exception:
            pass
    if not file_bytes and req.file_content:
        file_bytes = req.file_content.encode("utf-8")

    doc = document_extractor.extract(req.file_name, file_bytes, req.file_content)
    res = rag_engine.vectorize_document(
        doc_ref=doc["doc_ref"],
        title=doc["title"],
        text=doc["content"]
    )
    return {
        "success": True,
        "doc_ref": doc["doc_ref"],
        "title": doc["title"],
        "chunk_count": res.get("chunk_count", 0),
        "char_count": doc.get("char_count", 0)
    }

@app.get("/api/rag/documents")
def api_rag_list():
    return {"documents": rag_engine.list_documents()}

@app.delete("/api/rag/documents/{doc_ref}")
def api_rag_delete(doc_ref: str):
    ok = rag_engine.delete_document(doc_ref)
    return {"success": ok}

@app.post("/api/chat/ask")
def chat_ask(req: ChatAskRequest):
    # 1. If an attached file was sent, ingest into RAG engine automatically with OCR/chunking
    doc_ref = req.doc_ref
    if req.file_name and req.file_content:
        doc = document_extractor.extract(req.file_name, req.file_content.encode("utf-8"), req.file_content)
        rag_engine.vectorize_document(
            doc_ref=doc["doc_ref"],
            title=doc["title"],
            text=doc["content"]
        )
        doc_ref = doc["doc_ref"]

    # 2. Execute Hybrid RAG + Live Web Search + Dual LLM (Groq / Gemini)
    res = generate_rag_response(
        query=req.message,
        doc_ref=doc_ref,
        model_choice=req.model,
        include_web_search=True
    )
    return res

@app.post("/api/chat/stream")
def chat_stream(req: ChatAskRequest):
    doc_ref = req.doc_ref
    if req.file_name and req.file_content:
        doc = document_extractor.extract(req.file_name, req.file_content.encode("utf-8"), req.file_content)
        rag_engine.vectorize_document(
            doc_ref=doc["doc_ref"],
            title=doc["title"],
            text=doc["content"]
        )
        doc_ref = doc["doc_ref"]

    return StreamingResponse(
        stream_rag_tokens(query=req.message, doc_ref=doc_ref, model_choice=req.model),
        media_type="text/event-stream"
    )


# Real-Time Voice Processing & Living Mochi AI
class VoiceProcessRequest(BaseModel):
    query: Optional[str] = None
    audio_base64: Optional[str] = None
    mime_type: Optional[str] = "audio/webm"

def transcribe_with_groq_whisper(audio_bytes: bytes, filename: str = "speech.wav") -> Optional[str]:
    """Transcribes audio using Groq Cloud Whisper-large-v3-turbo (ultrafast ~150ms latency)."""
    import requests
    groq_key = get_setting("groq_api_key") or os.getenv("GROQ_API_KEY")
    if not groq_key:
        return None
    try:
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "json",
            "temperature": "0.0"
        }
        headers = {"Authorization": f"Bearer {groq_key}"}
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=headers,
            timeout=5.0
        )
        if resp.status_code == 200:
            result = resp.json()
            text = (result.get("text") or "").strip()
            noise_hallucinations = {"thank you.", "thank you", "thanks for watching", "subtitles by", "bye.", ".", ""}
            if text and text.lower() not in noise_hallucinations:
                return text
    except Exception as e:
        print(f"[Groq Whisper Warning] {e}")
    return None

def transcribe_speech_audio(audio_bytes: bytes, filename: str = "speech.wav") -> Optional[str]:
    """
    Unified Speech-to-Text Pipeline:
    1. Primary: Groq Cloud Whisper (~150ms latency, high accuracy, Hindi/Hinglish/English bilingual).
    2. Local Fallback: Cactus Whistle / needle (~45ms on-device CPU, 100% offline for English voice commands).
    """
    # 1. Primary fast cloud Whisper
    groq_text = transcribe_with_groq_whisper(audio_bytes, filename)
    if groq_text:
        return groq_text

    # 2. Local on-device offline fallback via Cactus Whistle
    try:
        from core.local_stt import transcribe_with_cactus_whistle
        local_text = transcribe_with_cactus_whistle(audio_bytes, filename)
        if local_text:
            return local_text
    except Exception as e:
        print(f"[Local STT Fallback Error] {e}")

    return None

@app.post("/api/voice/process")
def process_voice_interaction(req: VoiceProcessRequest):
    """Real-time voice processing: converts speech or text into natural conversational Mochi responses
    with full agentic tool control across all notch services (Tasks CRUD, Teams meeting notes, Wardrobe, Drawers)."""
    import os
    import re
    from datetime import datetime
    from google import genai
    from google.genai import types

    api_key = get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"reply": "Please add your Gemini API key in Settings to chat with me.", "tool_calls": [], "is_noise": false}

    client = genai.Client(api_key=api_key)
    status = tracker.get_status()
    pending = get_tasks(status="pending")
    completed = get_tasks(status="completed")
    app_summaries = get_today_app_summary()
    app_times_str = ", ".join([f"{a['app_name']}: {a['total_seconds'] // 60}m" for a in app_summaries[:8]]) or "None tracked yet."

    now_dt = datetime.now()
    live_time_str = now_dt.strftime("%A, %B %d, %Y, %I:%M %p")
    day_name = now_dt.strftime("%A")
    date_name = now_dt.strftime("%d %B %Y")

    pending_list_str = "\n".join([f"- [ID: {t['id']}] {t['title']} (source: {t.get('source', 'manual')})" for t in pending[:15]]) or "No pending tasks."
    recent_completed_str = "\n".join([f"- [ID: {t['id']}] {t['title']}" for t in completed[:5]]) or "None."

    system_context = f"""
You are Mochi, a warm, witty, ultra-smart AI companion on Windows, inspired by J.A.R.V.I.S.
The user speaks to you hands-free via continuous ambient voice or typed text.

LIVE SYSTEM DATE & TIME (Exact ground truth from Windows clock):
- Current Live Date & Time: {live_time_str}
- Current Day of Week: {day_name}
- Current Date: {date_name}
- If the user asks what day, date, or time it is (in English, Hindi, or Hinglish), ALWAYS give this exact real-time day and date!

CURRENT NOTCH SERVICES & TASKS STATE:
- Active Windows Application: {status.get('app', 'Desktop')}
- In Teams Meeting: {teams_detector.in_meeting} (Subject: {teams_detector.meeting_subject or 'None'})
- Tracked App Times Today: {app_times_str} (STRICT: ONLY mention this if user explicitly asks about their time or work)
- Pending Tasks ({len(pending)}):
{pending_list_str}
- Recently Completed Tasks:
{recent_completed_str}

BILINGUAL TRANSLATION & CONVERSATIONAL RULES:
- The user speaks to you in English, Hindi, or Hinglish (e.g. "meeting note complete kar do", "aaj kaun sa din hai?", "ek task add kar do...", "mochi ninja outfit pehno").
- You understand Hindi and Hinglish with 100% precision.
- ALWAYS reply in clear, natural, friendly spoken ENGLISH (JARVIS style).
- NEVER output Devanagari script unless explicitly asked to speak in Hindi.
- Keep spoken replies SHORT and natural (under 25 words).
- DO NOT use markdown asterisks, bullet points, or code formatting because this will be spoken aloud via Text-to-Speech.

CRITICAL ANTI-SPAM & RELEVANCE RULES:
- NEVER mention the user's active window or how long they have been working UNLESS the user EXPLICITLY asks ("how long have I been working?", "how much time did I spend on Python?").
- If the audio is silence, keyboard typing clicks, sighs, coughing, breathing, or background noise not addressed to you, RETURN: {{"reply": null, "tool_calls": [], "is_noise": true}}
- If the user gives a greeting or wake word (e.g. "Mochi", "Jarvis", "Hello"), reply: "Online and ready, sir." or "Right here, what can I do for you?"

AGENTIC TOOLS AVAILABLE FOR YOU TO CALL (You have FULL control over notch services):
1. create_task: args: {{"title": "...", "description": "...", "reminder_interval_mins": 30}}
2. complete_task: args: {{"query": "keyword or task ID to mark done"}} (e.g. "doctor", "meeting note", "10")
3. delete_task: args: {{"query": "keyword, title, or task ID to remove (e.g. 'doctor', '10')"}}
4. delete_all_tasks: args: {{}} (Call this when user says "delete all tasks", "clear all tasks", "remove all tasks", "saare tasks delete kar do", "clear my tasks")
5. update_task: args: {{"query": "...", "new_title": "...", "status": "pending|completed"}}
6. summarize_meeting_notes: args: {{"query": "meeting subject or person", "complete_followup": true/false}}
   (When user asks to summarize meeting notes and complete it, call this with complete_followup: true!)
7. set_outfit: args: {{"outfit": "default|developer|formal|ninja|cyberpunk|wizard|casual"}}
8. open_drawer: args: {{"drawer": "tasks|wardrobe|settings|eod|news"}}
9. collapse_notch: args: {{}}
10. get_focus_stats: args: {{"app_name": "..."}} (ONLY when user explicitly asks about their time)
11. web_search: args: {{"query": "search query to find relevant info or solutions"}}
    (Call when user asks to search the web, research an issue/library, or look up information)
12. screen_vision_analyze: args: {{"focus": "error_diagnosis|teams_reply|general", "user_query": "..."}}
    (Call when user says "look at my screen", "inspect this error", "check this", "what is on my screen", "screen dekho")
13. rephrase_or_suggest_reply: args: {{"incoming_text": "...", "draft": "...", "tone": "professional|concise|friendly", "target_app": "teams|outlook"}}
    (Call when user asks how to reply, or asks to rephrase their message or email)
14. auto_approve_dialog: args: {{"action": "approve_current|set_quota", "count": 10}}
    (Call when user says "approve it", "approve this dialog", "click submit", "allow it", or "approve the next 10 approvals", "auto approve 10")

OUTPUT FORMAT:
Return a single valid JSON object strictly matching this schema:
{{
  "reply": "Spoken English sentence under 25 words confirming action or answering query (or null if noise)",
  "tool_calls": [
    {{"name": "tool_name", "args": {{...}}}}
  ],
  "is_noise": false
}}
"""
    try:
        contents = []
        user_spoken_text = req.query or ""
        if req.audio_base64:
            import base64
            audio_bytes = base64.b64decode(req.audio_base64)
            # Fast-Path: Transcribe via Groq Whisper or Local Cactus Whistle
            ext = "wav" if "wav" in (req.mime_type or "") else "webm"
            stt_text = transcribe_speech_audio(audio_bytes, f"speech.{ext}")
            if stt_text:
                user_spoken_text = stt_text
                print(f"[Speech STT Engine] Transcribed: \"{stt_text}\"")
                contents = [system_context, f"User said: \"{stt_text}\""]
            else:
                # Multimodal Fallback: Direct Gemini audio ingestion
                part = types.Part.from_bytes(data=audio_bytes, mime_type=req.mime_type or "audio/webm")
                contents = [system_context, part, "User spoke hands-free. Listen carefully to user audio and respond as Mochi in raw JSON."]
        elif req.query:
            contents = [system_context, f"User said: \"{req.query}\""]
        else:
            return {"reply": "I'm listening! What can I help with?", "tool_calls": [], "is_noise": False}

        resp = None
        for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
            try:
                cfg = types.GenerateContentConfig(response_mime_type="application/json")
                resp = client.models.generate_content(model=m, contents=contents, config=cfg)
                if resp and resp.text:
                    break
            except Exception as err:
                print(f"[Voice Gemini Model {m} Error] {err}")
                continue

        if resp and resp.text:
            raw = resp.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            try:
                data = json.loads(raw)
            except Exception:
                data = {"reply": raw, "tool_calls": [], "is_noise": False}

            # If model classified as background noise, discard silently
            if data.get("is_noise"):
                return {"reply": None, "tool_calls": [], "is_noise": True}

            # ── AGENTIC TOOL EXECUTION ENGINE ─────────────────────────────
            tool_calls = data.get("tool_calls", [])
            primary_action = None
            outfit_to_set = None
            drawer_to_open = None

            # Fast-path intent check: If user explicitly asked to rephrase or rewrite text on screen
            user_low = user_spoken_text.lower()
            if any(k in user_low for k in ["rephrase", "rewrite", "polish this", "improve this line", "is line ko theek", "is line ko rephrase", "line theek karo", "rephrase it", "rephrase this"]):
                if not any(tc.get("name") == "rephrase_or_suggest_reply" for tc in tool_calls):
                    tool_calls.insert(0, {"name": "rephrase_or_suggest_reply", "args": {"tone": "polished"}})

            # Fast-path intent check: Approvals & Allow dialogs
            if any(k in user_low for k in ["approve it", "approve this", "click submit", "allow it", "allow this", "auto approve", "approvals", "approve next"]):
                m_cnt = re.search(r'(\d+)\s*approval', user_low)
                count = int(m_cnt.group(1)) if m_cnt else (10 if ("next" in user_low or "set" in user_low) else 1)
                act = "set_quota" if ("next" in user_low or "quota" in user_low or count > 1) else "approve_current"
                if not any(tc.get("name") == "auto_approve_dialog" for tc in tool_calls):
                    tool_calls.insert(0, {"name": "auto_approve_dialog", "args": {"action": act, "count": count}})

            for tc in tool_calls:
                name = tc.get("name") or tc.get("tool")
                args = tc.get("args", {})

                if name == "create_task":
                    primary_action = "create_task"
                    title = args.get("title", "").strip()
                    if title:
                        tid = add_task(
                            title=title,
                            description=args.get("description", ""),
                            source="voice_mochi",
                            reminder_interval_mins=args.get("reminder_interval_mins", 30)
                        )
                        broadcast_sync({
                            "type": "TASK_CREATED",
                            "data": {"id": tid, "title": title, "source": "voice_mochi"}
                        })

                elif name == "complete_task":
                    primary_action = "complete_task"
                    query = args.get("query", "")
                    task = complete_task_by_query(query)
                    if task:
                        broadcast_sync({
                            "type": "TASK_UPDATED",
                            "data": task
                        })

                elif name == "delete_task":
                    primary_action = "delete_task"
                    query = str(args.get("query", "")).strip()
                    if query.lower() in ["all", "all tasks", "all task", "everything", "every task", "sab", "saare", "saare tasks", "clear all", "delete all"]:
                        count = delete_all_tasks()
                        broadcast_sync({
                            "type": "ALL_TASKS_DELETED",
                            "data": {"count": count, "pending_count": 0}
                        })
                    else:
                        task = delete_task_by_query(query)
                        if task:
                            if task.get("id") == -1:
                                broadcast_sync({
                                    "type": "ALL_TASKS_DELETED",
                                    "data": {"count": task.get("count", 0), "pending_count": 0}
                                })
                            else:
                                broadcast_sync({
                                    "type": "TASK_DELETED",
                                    "data": task
                                })

                elif name == "delete_all_tasks":
                    primary_action = "delete_all_tasks"
                    count = delete_all_tasks()
                    broadcast_sync({
                        "type": "ALL_TASKS_DELETED",
                        "data": {"count": count, "pending_count": 0}
                    })

                elif name == "update_task":
                    primary_action = "update_task"
                    query = args.get("query", "")
                    task = update_task_by_query(query, new_title=args.get("new_title"), new_status=args.get("status"))
                    if task:
                        broadcast_sync({
                            "type": "TASK_UPDATED",
                            "data": task
                        })

                elif name == "summarize_meeting_notes":
                    primary_action = "summarize_meeting_notes"
                    query = args.get("query") or "meeting"
                    if args.get("complete_followup", False):
                        task = complete_task_by_query(query)
                        if task:
                            broadcast_sync({
                                "type": "TASK_UPDATED",
                                "data": task
                            })

                elif name == "set_outfit":
                    primary_action = "set_outfit"
                    outfit_to_set = args.get("outfit", "default").lower()
                    broadcast_sync({
                        "type": "SET_OUTFIT",
                        "data": {"outfit": outfit_to_set}
                    })

                elif name == "open_drawer":
                    primary_action = "open_drawer"
                    drawer_to_open = args.get("drawer", "tasks").lower()
                    broadcast_sync({
                        "type": "OPEN_DRAWER",
                        "data": {"drawer": drawer_to_open}
                    })

                elif name == "collapse_notch":
                    primary_action = "collapse_notch"
                    broadcast_sync({
                        "type": "COLLAPSE_NOTCH",
                        "data": {}
                    })

                elif name == "web_search":
                    primary_action = "web_search"
                    s_query = args.get("query", "")
                    if s_query:
                        broadcast_sync({
                            "type": "RESEARCH_STARTED",
                            "data": {"query": s_query, "user_text": user_spoken_text}
                        })
                        s_results = search_web_organic(s_query)
                        data["search_results"] = s_results
                        formatted_context = format_search_results_for_llm(s_results)

                        # Synthesize comprehensive research findings with Gemini
                        research_prompt = f"""You are Mochi, desktop AI research assistant.
User query: "{user_spoken_text or s_query}".
Live web search results from Google / DuckDuckGo:
{formatted_context}

Task:
1. Provide a comprehensive, accurate research summary answering the user's question with key facts and bullet points.
2. Provide a 1-sentence spoken answer under 20 words for text-to-speech.

Return JSON strictly:
{{
  "spoken_reply": "1-sentence summary under 20 words to speak aloud",
  "detailed_answer": "Comprehensive, structured research findings with bullet points"
}}
"""
                        try:
                            r_cfg = types.GenerateContentConfig(response_mime_type="application/json")
                            r_resp = client.models.generate_content(model="gemini-3.1-flash-lite", contents=[research_prompt], config=r_cfg)
                            if r_resp and r_resp.text:
                                r_raw = r_resp.text.strip()
                                r_raw = re.sub(r"^```(?:json)?\s*", "", r_raw)
                                r_raw = re.sub(r"\s*```$", "", r_raw)
                                r_data = json.loads(r_raw)
                                data["reply"] = r_data.get("spoken_reply") or f"Here is what I found on the web about {s_query}."
                                data["detailed_answer"] = r_data.get("detailed_answer") or formatted_context
                        except Exception as e_res:
                            print(f"[Research Synthesis Error] {e_res}")
                            data["reply"] = f"Here is what I found on the web about {s_query}."
                            data["detailed_answer"] = formatted_context

                        broadcast_sync({
                            "type": "RESEARCH_COMPLETED",
                            "data": {
                                "query": s_query,
                                "user_text": user_spoken_text,
                                "spoken_reply": data.get("reply"),
                                "detailed_answer": data.get("detailed_answer"),
                                "results": s_results
                            }
                        })

                elif name == "screen_vision_analyze":
                    primary_action = "screen_vision_analyze"
                    v_focus = args.get("focus", "general")
                    v_query = args.get("user_query") or user_spoken_text
                    cur_st = tracker.get_status()
                    screen_bytes = capture_desktop_bytes(window_controller)
                    v_analysis = analyze_screen_with_gemini(
                        jpeg_bytes=screen_bytes,
                        user_query=v_query,
                        focus=v_focus,
                        active_app=cur_st.get("app", "")
                    )
                    v_analysis["active_app"] = cur_st.get("app", "Active Desktop")
                    import time
                    v_analysis["captured_at"] = time.strftime("%H:%M:%S")
                    thumb = generate_screen_thumbnail(screen_bytes)
                    if thumb:
                        v_analysis["thumbnail_b64"] = thumb

                    broadcast_sync({
                        "type": "VISION_ANALYSIS_READY",
                        "data": v_analysis
                    })
                    data["vision_analysis"] = v_analysis

                elif name == "rephrase_or_suggest_reply":
                    primary_action = "rephrase_or_suggest_reply"
                    r_incoming = args.get("incoming_text", "")
                    r_draft = args.get("draft", "")
                    r_tone = args.get("tone", "polished")
                    r_app = args.get("target_app", "teams")

                    from core.screen_vision import rephrase_from_screen_or_draft, suggest_message_reply
                    # If draft is missing, empty, or user asks to rephrase the line on screen:
                    user_wants_screen_rephrase = (
                        not r_draft 
                        or len(r_draft.strip()) < 3 
                        or any(w in (str(r_draft).lower() + " " + user_spoken_text.lower()) for w in ["rephrase", "rewrite", "polish", "improve", "this line", "it", "screen", "theek"])
                    )

                    if user_wants_screen_rephrase:
                        clean_draft = r_draft if (r_draft and not any(w in r_draft.lower() for w in ["rephrase", "rewrite", "this"])) else ""
                        r_res = rephrase_from_screen_or_draft(
                            user_draft=clean_draft,
                            user_query=user_spoken_text,
                            tone=r_tone,
                            controller=window_controller
                        )
                    else:
                        r_res = suggest_message_reply(
                            incoming_text=r_incoming,
                            user_draft=r_draft,
                            tone=r_tone,
                            target_app=r_app
                        )

                    broadcast_sync({
                        "type": "REPLY_SUGGESTION_READY",
                        "data": r_res
                    })
                    data["reply_suggestion"] = r_res
                    data["reply"] = "I've rephrased your text. Click Copy in your notch or press paste."

                elif name == "auto_approve_dialog":
                    primary_action = "auto_approve_dialog"
                    from core.auto_approver import auto_approver
                    action = args.get("action", "approve_current")
                    count = int(args.get("count", 10))

                    if action == "set_quota":
                        res = auto_approver.set_quota(count=count, controller=window_controller)
                        broadcast_sync({
                            "type": "AUTO_APPROVAL_STATUS",
                            "data": res
                        })
                        data["auto_approval_status"] = res
                        data["reply"] = f"Auto-approver active for your next {count} safe approvals, sir."
                    else:
                        res = auto_approver.approve_current(controller=window_controller, force=True)
                        broadcast_sync({
                            "type": "AUTO_APPROVAL_TRIGGERED",
                            "data": res
                        })
                        data["approval_result"] = res
                        if res.get("approved"):
                            data["reply"] = f"Approved '{res.get('dialog_title', 'dialog')}' for you, sir."
                        else:
                            data["reply"] = res.get("message", "No approval dialog detected.")

            data["action"] = primary_action
            data["user_text"] = user_spoken_text
            if outfit_to_set:
                data["outfit"] = outfit_to_set
            if drawer_to_open:
                data["drawer"] = drawer_to_open

            return data

    except Exception as e:
        print("[Voice Process Error]", e)
        return {"reply": "Sorry, I had trouble processing that.", "tool_calls": [], "is_noise": False}

    return {"reply": "I'm right here in your notch. What would you like to do?", "tool_calls": [], "is_noise": False}

# ── Native Windows JARVIS Microphone Engine ─────────────────────────
def on_native_speech_captured(wav_bytes: bytes):
    try:
        import base64
        req = VoiceProcessRequest(
            audio_base64=base64.b64encode(wav_bytes).decode("ascii"),
            mime_type="audio/wav"
        )
        result = process_voice_interaction(req)
        # Discard if noise, no reply, or ignored error strings
        if not result or result.get("is_noise"):
            return
        reply_text = (result.get("reply") or "").strip()
        if not reply_text:
            return
        if any(ign in reply_text.lower() for ign in ["sorry, i had trouble", "i'm right here in your notch"]):
            return

        broadcast_sync({
            "type": "JARVIS_VOICE_RESULT",
            "data": result
        })
    except Exception as err:
        print(f"[JARVIS Speech Process Error] {err}")

jarvis_listener = WindowsJarvisListener(on_speech_captured=on_native_speech_captured)

class SpeakingStateReq(BaseModel):
    is_speaking: bool

@app.post("/api/voice/speaking-state")
def set_speaking_state(req: SpeakingStateReq):
    jarvis_listener.set_speaking(req.is_speaking)
    return {"success": True}

@app.post("/api/voice/listen-once")
def api_voice_listen_once():
    """Records a single speech utterance on demand (Click-to-Speak from Chat)."""
    try:
        wav_bytes = jarvis_listener.record_single_utterance(max_seconds=6.0)
        if not wav_bytes:
            return {"success": False, "text": "", "error": "No speech detected."}
        
        # Fast-path STT via Groq Whisper or Local Cactus Whistle
        stt_text = transcribe_speech_audio(wav_bytes, "chat_voice.wav")
        if stt_text:
            return {"success": True, "text": stt_text.strip()}
        
        # Multimodal Gemini fallback
        import base64
        req = VoiceProcessRequest(
            audio_base64=base64.b64encode(wav_bytes).decode("ascii"),
            mime_type="audio/wav"
        )
        res = process_voice_interaction(req)
        user_txt = res.get("user_text") or res.get("query") or ""
        return {"success": True, "text": user_txt, "reply": res.get("reply", "")}
    except Exception as e:
        print(f"[listen-once Error] {e}")
        return {"success": False, "text": "", "error": str(e)}

@app.post("/api/voice/toggle-listening")
def api_voice_toggle():
    if jarvis_listener.is_running:
        jarvis_listener.stop()
        active = False
    else:
        jarvis_listener.start()
        active = True
    return {"active": active}

@app.get("/api/voice/status")
def api_voice_status():
    return {"active": jarvis_listener.is_running}

@app.post("/api/assistant/proactive-update")
def get_proactive_update():
    status = tracker.get_status()
    pending = get_tasks(status="pending")
    app_name = status.get('app', 'Desktop')
    duration_mins = status.get('duration', 0) // 60

    if len(pending) > 0:
        return {"reply": f"You've been focused on {app_name} for {duration_mins} minutes, with {len(pending)} pending tasks waiting."}
    return {"reply": f"You're in flow on {app_name} with {duration_mins} minutes tracked today. All tasks are clear!"}

class PushDevOpsRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    work_item_type: Optional[str] = "Task"

@app.post("/api/eod/push-devops")
def push_to_devops(req: PushDevOpsRequest):
    client = AzureDevOpsClient()
    results = []
    for item in req.tasks:
        res = client.create_work_item(
            title=item.get("title", "Work Completed"),
            description=item.get("description", ""),
            tags=item.get("tags", []),
            work_item_type=req.work_item_type
        )
        # If successfully pushed, save to local tasks table as well
        if res.get("success"):
            tid = add_task(
                title=item.get("title"),
                description=item.get("description"),
                source="eod_gemini"
            )
            update_task_status(tid, "completed")
            if res.get("id"):
                set_task_devops_id(tid, str(res["id"]))
        results.append(res)
    return {"results": results}

# News / Context Feed
@app.get("/api/news")
def get_news():
    current = tracker.get_status()
    articles = fetch_relevant_news(
        current_title=current.get("title", ""),
        app_name=current.get("app", "")
    )
    return {"articles": articles}

# Settings
@app.get("/api/settings")
def list_settings():
    return get_all_settings()

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, str]

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    for k, v in req.settings.items():
        set_setting(k, v)
    return {"success": True}

@app.get("/api/settings/autostart")
def get_autostart_status():
    try:
        from scripts.setup_autostart import is_autostart_enabled
        return {"enabled": is_autostart_enabled()}
    except Exception as e:
        return {"enabled": False, "error": str(e)}

class AutostartRequest(BaseModel):
    enabled: bool

@app.post("/api/settings/autostart")
def set_autostart_status(req: AutostartRequest):
    try:
        from scripts.setup_autostart import enable_autostart, disable_autostart
        if req.enabled:
            ok = enable_autostart()
        else:
            ok = disable_autostart()
        return {"success": ok, "enabled": req.enabled}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Simulate Call Completion for Testing
@app.post("/api/teams/simulate-call-end")
def simulate_call():
    teams_detector.trigger_mock_call_ended("Sprint Architecture Review")
    return {"success": True, "message": "Simulated Teams Call Ended event broadcasted!"}

# Simulate / Trigger Teams Task Detection (like Bimal Desai's message)
class AnalyzeTeamsTextRequest(BaseModel):
    text: str
    sender: Optional[str] = "Bimal Desai"

@app.post("/api/teams/analyze-text")
def api_analyze_teams_text(req: AnalyzeTeamsTextRequest):
    task = analyze_teams_text_with_gemini(req.text, sender=req.sender)
    if task:
        broadcast_sync({
            "type": "TEAMS_TASK_PROPOSAL",
            "data": task
        })
        return {"success": True, "task": task}
    return {"success": False, "message": "No actionable task found in text."}

@app.post("/api/teams/simulate-task")
def api_simulate_task():
    sample_text = "updated the API .. pass X-User-Id with their portal user id instead of X-User-Email"
    task = analyze_teams_text_with_gemini(sample_text, sender="Bimal Desai")
    if not task:
        task = {
            "is_task": True,
            "title": "Update API: Use X-User-Id instead of X-User-Email",
            "sender": "Bimal Desai",
            "description": "Pass X-User-Id with portal user id instead of X-User-Email in API requests.",
            "priority": "High"
        }
    broadcast_sync({
        "type": "TEAMS_TASK_PROPOSAL",
        "data": task
    })
    return {"success": True, "task": task}


# Window resizing and dragging endpoints (Native Qt Dock)
window_controller = None

def set_window_controller(controller):
    global window_controller
    window_controller = controller

class WindowResizeReq(BaseModel):
    width: int
    height: int

class WindowMoveReq(BaseModel):
    dx: int
    dy: int

@app.post("/api/window/resize")
def api_window_resize(req: WindowResizeReq):
    if window_controller:
        window_controller.sig_resize.emit(req.width, req.height)
    return {"success": True}

@app.post("/api/window/move")
def api_window_move(req: WindowMoveReq):
    if window_controller:
        window_controller.sig_move.emit(req.dx, req.dy)
    return {"success": True}

@app.post("/api/window/snap-top")
def api_window_snap_top():
    if window_controller and hasattr(window_controller, "sig_snap_top"):
        window_controller.sig_snap_top.emit()
    return {"success": True}

class ClipboardCopyReq(BaseModel):
    text: str

@app.post("/api/clipboard/copy")
def api_clipboard_copy(req: ClipboardCopyReq):
    # 1. Native PySide6 Qt GUI main thread clipboard (100% reliable)
    if window_controller and hasattr(window_controller, "sig_copy_clipboard"):
        try:
            window_controller.sig_copy_clipboard.emit(req.text)
            return {"success": True}
        except Exception as e:
            print("[Clipboard WindowController Warning]", e)

    # 2. Windows win32clipboard fallback
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(req.text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return {"success": True}
    except Exception as e:
        print("[Clipboard win32 error]", e)

    # 3. Windows clip.exe CLI fallback
    try:
        import subprocess
        subprocess.run(['clip.exe'], input=req.text.encode('utf-16le'), shell=True, check=True)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Smart Web Search, Screen Vision & Reply Assistant Endpoints ──────
class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

@app.post("/api/search")
def api_search_web(req: SearchRequest):
    results = search_web_organic(req.query, max_results=req.max_results or 5)
    formatted = format_search_results_for_llm(results)
    broadcast_sync({
        "type": "WEB_SEARCH_RESULTS",
        "data": {"query": req.query, "results": results}
    })
    return {"results": results, "formatted": formatted}

class VisionAnalyzeRequest(BaseModel):
    query: Optional[str] = "Inspect active screen"
    focus: Optional[str] = "general"
    mode: Optional[str] = "fullscreen"
    delay: Optional[float] = 0.0

@app.post("/api/vision/analyze")
def api_vision_analyze(req: VisionAnalyzeRequest):
    import time
    if req.mode == "pointer" and req.delay and req.delay > 0:
        time.sleep(req.delay)

    current = tracker.get_status()
    cursor_info = None

    if req.mode == "pointer":
        from core.screen_vision import capture_screen_region_at_cursor
        res_crop = capture_screen_region_at_cursor(window_controller, width=720, height=500)
        screen_bytes = res_crop["bytes"]
        cursor_info = res_crop.get("cursor")
    else:
        screen_bytes = capture_desktop_bytes(window_controller)

    analysis = analyze_screen_with_gemini(
        jpeg_bytes=screen_bytes,
        user_query=req.query or "Inspect active screen",
        focus=req.focus or "general",
        active_app=current.get("app", "")
    )
    analysis["active_app"] = current.get("app", "Active Desktop")
    if cursor_info:
        analysis["inspection_mode"] = f"Pointer Region ({cursor_info['x']}, {cursor_info['y']})"
    else:
        analysis["inspection_mode"] = "Full Screen"
    analysis["captured_at"] = time.strftime("%H:%M:%S")
    thumb = generate_screen_thumbnail(screen_bytes)
    if thumb:
        analysis["thumbnail_b64"] = thumb

    broadcast_sync({
        "type": "VISION_ANALYSIS_READY",
        "data": analysis
    })
    return {"analysis": analysis}

class RephraseScreenRequest(BaseModel):
    query: Optional[str] = "rephrase it"
    draft: Optional[str] = ""
    tone: Optional[str] = "polished"

@app.post("/api/assistant/rephrase-screen")
def api_assistant_rephrase_screen(req: RephraseScreenRequest):
    from core.screen_vision import rephrase_from_screen_or_draft
    res = rephrase_from_screen_or_draft(
        user_draft=req.draft or "",
        user_query=req.query or "rephrase it",
        tone=req.tone or "polished",
        controller=window_controller
    )
    broadcast_sync({
        "type": "REPLY_SUGGESTION_READY",
        "data": res
    })
    return res

class RephraseRequest(BaseModel):
    incoming_text: str
    draft: Optional[str] = ""
    tone: Optional[str] = "professional"
    target_app: Optional[str] = "teams"

@app.post("/api/assistant/rephrase")
def api_assistant_rephrase(req: RephraseRequest):
    from core.screen_vision import rephrase_from_screen_or_draft, suggest_message_reply
    if not req.draft or len(req.draft.strip()) < 3 or any(w in (req.draft.lower() + " " + req.incoming_text.lower()) for w in ["rephrase", "rewrite", "polish", "it"]):
        res = rephrase_from_screen_or_draft(
            user_draft=req.draft if (req.draft and not any(w in req.draft.lower() for w in ["rephrase", "rewrite"])) else "",
            user_query=req.incoming_text,
            tone=req.tone or "polished",
            controller=window_controller
        )
    else:
        res = suggest_message_reply(
            incoming_text=req.incoming_text,
            user_draft=req.draft or "",
            tone=req.tone or "professional",
            target_app=req.target_app or "teams"
        )
    broadcast_sync({
        "type": "REPLY_SUGGESTION_READY",
        "data": res
    })
    return res

class ApprovalQuotaReq(BaseModel):
    quota: int = 10

@app.post("/api/approvals/set-quota")
def api_set_approval_quota(req: ApprovalQuotaReq):
    from core.auto_approver import auto_approver
    res = auto_approver.set_quota(count=req.quota, controller=window_controller)
    broadcast_sync({
        "type": "AUTO_APPROVAL_STATUS",
        "data": res
    })
    return res

@app.post("/api/approvals/approve-current")
def api_approve_current():
    from core.auto_approver import auto_approver
    res = auto_approver.approve_current(controller=window_controller, force=True)
    broadcast_sync({
        "type": "AUTO_APPROVAL_TRIGGERED",
        "data": res
    })
    return res

@app.get("/api/approvals/status")
def api_get_approval_status():
    from core.auto_approver import auto_approver
    return auto_approver.get_status()

@app.post("/api/app/quit")
def api_app_quit():
    save_daily_markdown_log()
    if window_controller and hasattr(window_controller, "sig_quit"):
        window_controller.sig_quit.emit()
    return {"success": True}

# WebSocket for Dock UI
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        # Send initial state on connection
        await websocket.send_text(json.dumps({
            "type": "INITIAL_STATE",
            "data": {
                "tracker": tracker.get_status(),
                "in_meeting": teams_detector.in_meeting,
                "pending_tasks": len(get_tasks(status="pending"))
            }
        }))
        while True:
            # Keep connection alive & listen for client pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# Serve Frontend static assets and index.html fallback
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

