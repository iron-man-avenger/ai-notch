import os
import json
import re
from typing import Dict, Any, List, Optional, Generator
import requests
from dotenv import load_dotenv

from core.db import get_setting
from core.rag_engine import rag_engine
from core.web_searcher import search_web_organic, format_search_results_for_llm

load_dotenv()

SYSTEM_RAG_PROMPT = """You are Mochi, a smart, helpful AI Personal Assistant with Hybrid RAG Document Intelligence and Live Web Search.
Answer accurately based on the provided VERIFIED CONTEXT and live web search results whenever relevant.
If information is missing or not covered in the context, clearly state what is known and what is missing.
Provide structured, concise, step-by-step answers in clean markdown.
Always end your answer with clear citations:
> Reference: [DOC_REF] (and/or verified web source links)
"""

def generate_rag_response(
    query: str,
    doc_ref: Optional[str] = None,
    model_choice: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    include_web_search: bool = True
) -> Dict[str, Any]:
    """
    Core RAG Chat synthesis:
    1. Hybrid Retrieval (Dense Vector + BM25 + RRF k=60)
    2. Live Web Search Integration
    3. Context Injection
    4. Dual LLM Generation (Groq LLaMA or Google Gemini)
    """
    # 1. Check if conversational greeting or small-talk (bypass expensive RAG/web lookups)
    q_lower = query.lower().strip()
    is_greeting = q_lower in ["hi", "hello", "hey", "hola", "namaste", "good morning", "good evening", "good afternoon", "how are you", "who are you"] or (len(q_lower) < 6 and any(q_lower.startswith(g) for g in ["hi", "hey", "sup"]))

    # 1. Retrieve top relevant chunks from RAG store (only if not greeting)
    chunks = []
    if not is_greeting:
        chunks = rag_engine.hybrid_search(query, top_k=4, doc_ref=doc_ref)

    # 2. Live Web Search ONLY if explicitly requested or relevant
    search_sources: List[Dict[str, Any]] = []
    web_context_str = ""
    is_web_query = any(w in q_lower for w in ["research", "search the web", "search web", "google", "find latest", "latest news", "today's news", "browse web"])
    
    if include_web_search and is_web_query and not is_greeting:
        try:
            q_clean = re.sub(r"(?i)\b(please|research|search|web|on|about|google|find|for|look|up|the|can you)\b", " ", query).strip()
            if not q_clean or len(q_clean) < 3:
                q_clean = query
            search_sources = search_web_organic(q_clean, max_results=4)
            if search_sources:
                web_context_str = f"\nVERIFIED WEB SEARCH RESULTS for '{q_clean}':\n" + format_search_results_for_llm(search_sources) + "\n"
        except Exception as e_s:
            print(f"[RAG Web Search Warning] {e_s}")

    # 3. Build verified context block
    rag_context_blocks = []
    citations = []
    for c in chunks:
        ref = c["doc_ref"]
        if ref not in citations:
            citations.append(ref)
        rag_context_blocks.append(f"SOURCE [{ref}] {c['title']} ({c.get('heading', '')}):\n{c['content']}")

    context_text = "\n\n---\n\n".join(rag_context_blocks)
    context_section = f"VERIFIED DOCUMENT CONTEXT:\n{context_text}\n" if context_text else ""

    # 4. Determine LLM provider (Groq vs Gemini)
    chosen_model = model_choice or "gemini-3.5-flash-lite"
    is_groq = any(name in chosen_model.lower() for name in ["groq", "llama", "qwen", "gpt-oss", "mixtral", "gemma"])

    full_prompt = f"""{SYSTEM_RAG_PROMPT}

{context_section}
{web_context_str}

User Question: {query}
"""

    reply_text = ""

    # ── Path A0: Local Ollama (if running on user's machine at port 11434) ──
    is_ollama = "ollama" in chosen_model.lower() or "local" in chosen_model.lower()
    if is_ollama:
        try:
            ollama_resp = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "llama3", "prompt": full_prompt, "stream": False},
                timeout=10.0
            )
            if ollama_resp.status_code == 200:
                reply_text = ollama_resp.json().get("response", "").strip()
        except Exception:
            # If Ollama is not running locally, smoothly fallback to Groq Cloud
            pass

    # ── Path A: Groq Cloud LLM (Ultra-fast 0.6s generation) ───
    if (is_groq or (is_ollama and not reply_text)) and not reply_text:
        groq_key = get_setting("groq_api_key") or os.getenv("GROQ_API_KEY")
        if groq_key:
            groq_model_name = chosen_model if ("/" in chosen_model or "qwen" in chosen_model) else "openai/gpt-oss-20b"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": SYSTEM_RAG_PROMPT}]
            if context_text:
                messages.append({"role": "system", "content": f"VERIFIED DOCUMENT CONTEXT:\n{context_text}"})
            if web_context_str:
                messages.append({"role": "system", "content": web_context_str})
            if history:
                messages.extend(history[-4:])
            messages.append({"role": "user", "content": query})

            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": groq_model_name,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 1024
                    },
                    timeout=8.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = data["choices"][0]["message"]["content"].strip()
            except Exception as e_g:
                print(f"[Groq LLM Warning] {e_g}")

    # ── Path B: Google Gemini LLM (Prioritizing ultra-fast 1s flash-lite & 3.5-flash) ──
    if not reply_text:
        gemini_key = get_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                
                # Priority order: Fastest verified models first
                candidate_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
                if chosen_model and not is_groq:
                    if chosen_model in candidate_models:
                        candidate_models.remove(chosen_model)
                    candidate_models.insert(0, chosen_model)

                for m in candidate_models:
                    try:
                        res = client.models.generate_content(model=m, contents=full_prompt)
                        if res and res.text:
                            reply_text = res.text.strip()
                            chosen_model = m
                            break
                    except Exception as err_m:
                        print(f"[Gemini RAG] {m} failed: {err_m}, trying next model...")
                        continue
            except Exception as e_gem:
                print(f"[Gemini RAG Warning] {e_gem}")

    if not reply_text:
        reply_text = "I processed your request, but could not connect to Groq or Gemini. Please verify your API key in Settings."

    return {
        "reply": reply_text,
        "chunks": chunks,
        "citations": citations,
        "sources": search_sources,
        "model_used": chosen_model
    }

def stream_rag_tokens(query: str, doc_ref: Optional[str] = None, model_choice: Optional[str] = None) -> Generator[str, None, None]:
    """
    Streams tokens via Server-Sent Events (SSE) data format:
    data: {"token": "..."}\n\n
    """
    res = generate_rag_response(query=query, doc_ref=doc_ref, model_choice=model_choice)
    full_text = res.get("reply", "")

    # Split text into tokens / words for smooth SSE streaming
    words = full_text.split(" ")
    for idx, w in enumerate(words):
        token = w + (" " if idx < len(words) - 1 else "")
        yield f"data: {json.dumps({'token': token})}\n\n"

    # Send final payload with citations and web sources
    yield f"data: {json.dumps({'done': True, 'citations': res.get('citations', []), 'sources': res.get('sources', [])})}\n\n"
