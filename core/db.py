import sqlite3
import os
import re
from datetime import datetime, date
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assistant.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Activity tracking table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT NOT NULL,
        window_title TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_seconds INTEGER DEFAULT 0
    )
    """)
    
    # Tasks table (manual, Teams call follow-ups, EOD items)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        source TEXT DEFAULT 'manual', -- 'manual', 'teams_call', 'eod_gemini'
        status TEXT DEFAULT 'pending', -- 'pending', 'completed'
        reminder_interval_mins INTEGER DEFAULT 30,
        next_reminder_time TEXT,
        devops_id TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Key-value settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Document Chunks Table for RAG & Vector Search
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_ref TEXT NOT NULL,
        title TEXT NOT NULL,
        heading TEXT DEFAULT '',
        content TEXT NOT NULL,
        embedding TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_ref ON document_chunks(doc_ref)")
    
    conn.commit()
    conn.close()

def log_activity(app_name: str, window_title: str, duration_seconds: int = 5):
    """Logs or accumulates time for the active app and window."""
    today_start = date.today().isoformat() + "T00:00:00"
    now_iso = datetime.now().isoformat()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if the last record matches current app & window within the last 15 seconds
    cursor.execute("""
    SELECT id, duration_seconds FROM activities 
    WHERE app_name = ? AND window_title = ? AND start_time >= ?
    ORDER BY id DESC LIMIT 1
    """, (app_name, window_title, today_start))
    
    row = cursor.fetchone()
    if row:
        new_duration = row["duration_seconds"] + duration_seconds
        cursor.execute("""
        UPDATE activities 
        SET duration_seconds = ?, end_time = ?
        WHERE id = ?
        """, (new_duration, now_iso, row["id"]))
    else:
        cursor.execute("""
        INSERT INTO activities (app_name, window_title, start_time, end_time, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
        """, (app_name, window_title, now_iso, now_iso, duration_seconds))
        
    conn.commit()
    conn.close()

def get_today_activities() -> List[Dict[str, Any]]:
    today_start = date.today().isoformat() + "T00:00:00"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT app_name, window_title, SUM(duration_seconds) as total_seconds, MAX(end_time) as last_seen
    FROM activities
    WHERE start_time >= ?
    GROUP BY app_name, window_title
    ORDER BY total_seconds DESC
    """, (today_start,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_today_app_summary() -> List[Dict[str, Any]]:
    today_start = date.today().isoformat() + "T00:00:00"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT app_name, SUM(duration_seconds) as total_seconds
    FROM activities
    WHERE start_time >= ?
    GROUP BY app_name
    ORDER BY total_seconds DESC
    """, (today_start,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_task(title: str, description: str = "", source: str = "manual", reminder_interval_mins: int = 30) -> int:
    clean_title = title.strip()
    now_iso = datetime.now().isoformat()
    conn = get_db()
    cursor = conn.cursor()

    # Deduplication: Avoid creating duplicate tasks (pending or created today)
    today_prefix = date.today().isoformat()
    cursor.execute("""
    SELECT id FROM tasks 
    WHERE LOWER(TRIM(title)) = LOWER(TRIM(?)) 
      AND (status = 'pending' OR created_at >= ?)
    ORDER BY id DESC LIMIT 1
    """, (clean_title, today_prefix))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    cursor.execute("""
    INSERT INTO tasks (title, description, source, status, reminder_interval_mins, created_at)
    VALUES (?, ?, ?, 'pending', ?, ?)
    """, (clean_title, description, source, reminder_interval_mins, now_iso))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,))
    else:
        cursor.execute("SELECT * FROM tasks ORDER BY status ASC, id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def update_task_status(task_id: int, status: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()

def update_task_interval(task_id: int, reminder_interval_mins: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET reminder_interval_mins = ? WHERE id = ?", (int(reminder_interval_mins), task_id))
    conn.commit()
    conn.close()

def set_task_devops_id(task_id: int, devops_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET devops_id = ? WHERE id = ?", (str(devops_id), task_id))
    conn.commit()
    conn.close()

def delete_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def find_task_by_query(query: str, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds a task by ID or keyword in title/description."""
    clean_q = query.strip().lower()
    if not clean_q:
        return None
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Try numeric ID
    if clean_q.isdigit():
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (int(clean_q),))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
            
    # 2. Try exact or substring match in title
    status_filter = "AND status = ?" if status else ""
    params: List[Any] = [f"%{clean_q}%"]
    if status:
        params.append(status)
    
    cursor.execute(f"SELECT * FROM tasks WHERE LOWER(title) LIKE ? {status_filter} ORDER BY id DESC LIMIT 1", params)
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)
        
    # 3. Try match by individual words (e.g. 'doctor' in 'visit doctor')
    words = [w for w in re.split(r"[\s\-_]+", clean_q) if len(w) >= 3 and w not in ["task", "the", "and", "please", "mark", "done", "complete", "finish", "delete", "remove"]]
    for w in words:
        p: List[Any] = [f"%{w}%"]
        if status:
            p.append(status)
        cursor.execute(f"SELECT * FROM tasks WHERE LOWER(title) LIKE ? {status_filter} ORDER BY id DESC LIMIT 1", p)
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
            
    conn.close()
    return None

def complete_task_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Finds a matching task (prioritizing pending) and marks it completed."""
    task = find_task_by_query(query, status="pending") or find_task_by_query(query)
    if task:
        update_task_status(task["id"], "completed")
        task["status"] = "completed"
        return task
    return None

def delete_all_tasks(status: Optional[str] = None) -> int:
    """Deletes all tasks (or filtered by status e.g. pending/completed), returning deleted count."""
    conn = get_db()
    cursor = conn.cursor()
    if status:
        cursor.execute("DELETE FROM tasks WHERE status = ?", (status,))
    else:
        cursor.execute("DELETE FROM tasks")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def delete_task_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Finds a matching task and deletes it, or deletes all tasks if query is 'all'."""
    clean_q = query.strip().lower()
    if not clean_q:
        return None

    # Handle delete all commands
    if clean_q in ["all", "all tasks", "all task", "everything", "every task", "sab", "saare", "saare tasks", "clear all", "delete all"]:
        count = delete_all_tasks()
        return {"id": -1, "title": "All Tasks", "count": count}

    task = find_task_by_query(query)
    if task:
        delete_task(task["id"])
        return task
    return None

def update_task_by_query(query: str, new_title: Optional[str] = None, new_status: Optional[str] = None, new_interval_mins: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Finds a task and updates its title, status, or reminder interval."""
    task = find_task_by_query(query)
    if not task:
        return None
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    params: List[Any] = []
    if new_title:
        updates.append("title = ?")
        params.append(new_title.strip())
    if new_status:
        updates.append("status = ?")
        params.append(new_status.strip())
    if new_interval_mins is not None:
        updates.append("reminder_interval_mins = ?")
        params.append(int(new_interval_mins))
    if updates:
        params.append(task["id"])
        cursor.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return find_task_by_query(str(task["id"]))

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return settings
