# ==============================================================================
# 5. FASTAPI SERVER & STREAMING ENDPOINT (main.py)
# Uses Groq or Gemini for LLM, Open-Source FastEmbed for Embeddings.
# ==============================================================================

import os
import json
import sqlite3
from typing import Optional, List, Dict, Any, Generator
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag_core_portable.ai import get_embedding, get_embeddings_batch
from rag_core_portable.chunker import chunk_document
from rag_core_portable.unlimited_ocr import extract_file_content
from rag_core_portable.rag import hybrid_search_chunks

app = FastAPI(title="Portable RAG & AI Chatbot Engine")

DB_FILE = "rag_data.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Database Table
with get_db() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_ref TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding TEXT NOT NULL
    );
    """)

SYSTEM_PROMPT = """You are an expert AI Assistant.
Answer ONLY based on the provided VERIFIED CONTEXT.
If information is missing, say you do not know.
Directly answer with clear step-by-step procedures.
Always end your response with: > Reference: [DOC_REF]
"""

class IngestTextRequest(BaseModel):
    doc_ref: str
    title: str
    text: str

class ChatRequest(BaseModel):
    message: str
    llm_provider: Optional[str] = "groq"  # "groq" or "gemini"
    model_name: Optional[str] = "llama-3.3-70b-versatile"  # or "gemini-flash-latest"

@app.post("/api/rag/ingest")
def ingest_text(req: IngestTextRequest):
    """Chunks and vectorizes text using open-source FastEmbed embeddings."""
    chunks = chunk_document(req.text, title=req.title, target_chars=550)
    if not chunks:
        return {"success": False, "chunk_count": 0}

    # Generate vectors using open-source model
    prompts = [f"{req.title}: {c['content']}" for c in chunks]
    vectors = get_embeddings_batch(prompts)

    with get_db() as conn:
        conn.execute("DELETE FROM document_chunks WHERE doc_ref = ?", (req.doc_ref,))
        for idx, c in enumerate(chunks):
            conn.execute(
                "INSERT INTO document_chunks (doc_ref, title, content, embedding) VALUES (?, ?, ?, ?)",
                (req.doc_ref, req.title, c["content"], json.dumps(vectors[idx]))
            )
        conn.commit()

    return {"success": True, "doc_ref": req.doc_ref, "chunk_count": len(chunks)}

@app.post("/api/rag/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Extracts text from PDF, Images (Unlimited-OCR), Word, or Code, then vectorizes."""
    content_bytes = await file.read()
    extracted_text = extract_file_content(file.filename, content_bytes)
    doc_ref = file.filename.replace(" ", "_").lower()
    
    return ingest_text(IngestTextRequest(
        doc_ref=doc_ref,
        title=file.filename,
        text=extracted_text
    ))

def call_llm(prompt: str, provider: str = "groq", model_name: str = "llama-3.3-70b-versatile") -> str:
    """Calls Groq or Gemini LLM."""
    if provider == "groq" or "llama" in model_name:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model_name or "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2
                },
                timeout=15.0
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()

    # Gemini Fallback / Default
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        res = client.models.generate_content(
            model=model_name if "gemini" in model_name else "gemini-flash-latest",
            contents=prompt
        )
        if res and res.text:
            return res.text.strip()

    return "Error: Could not reach LLM provider. Please check GROQ_API_KEY or GEMINI_API_KEY."

def generate_chat_stream(user_query: str, provider: str, model: str) -> Generator[str, None, None]:
    """Retrieves top chunks via Hybrid RAG and streams tokens via SSE."""
    # 1. Fetch all chunks from database
    with get_db() as conn:
        rows = conn.execute("SELECT id, doc_ref, title, content, embedding FROM document_chunks").fetchall()

    chunks = []
    for r in rows:
        chunks.append({
            "id": r["id"],
            "doc_ref": r["doc_ref"],
            "title": r["title"],
            "content": r["content"],
            "embedding": json.loads(r["embedding"])
        })

    # 2. Hybrid Search (Vector + BM25 + RRF k=60)
    top_chunks = hybrid_search_chunks(chunks, user_query, top_k=4)

    # 3. Build Verified Context Block
    context_text = "\n\n---\n\n".join([
        f"SOURCE [{c['doc_ref']}] {c['title']}:\n{c['content']}" for c in top_chunks
    ])

    full_prompt = f"{SYSTEM_PROMPT}\n\nVERIFIED CONTEXT:\n{context_text}\n\nUser Question: {user_query}"

    # 4. Generate LLM Answer
    answer = call_llm(full_prompt, provider=provider, model_name=model)

    # 5. Stream as Server-Sent Events (SSE)
    words = answer.split(" ")
    for idx, w in enumerate(words):
        token = w + (" " if idx < len(words) - 1 else "")
        yield f"data: {json.dumps({'token': token})}\n\n"

    yield "data: {\"done\": true}\n\n"

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Streaming Chat Endpoint with SSE."""
    return StreamingResponse(
        generate_chat_stream(req.message, req.llm_provider or "groq", req.model_name or "llama-3.3-70b-versatile"),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
