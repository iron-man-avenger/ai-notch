# Portable Hybrid RAG & AI Chatbot Engine

Pure, portable backend & RAG engine combining:
* **Open-Source Embeddings:** `fastembed` (`BAAI/bge-small-en-v1.5`, 384 dimensions, local ONNX CPU runtime, $0 cost).
* **Document Extraction & OCR:** Baidu Unlimited-OCR (`https://github.com/baidu/Unlimited-OCR`) for long-context multi-page PDFs, images, and tables, with fallback vision support.
* **Semantic Chunker:** 500-600 character passages on sentence boundaries.
* **Hybrid Retrieval:** Dense Vector (Cosine Distance) + Sparse Keyword (`rank-bm25` / `BM25Okapi`) + Reciprocal Rank Fusion (**RRF $k=60$**).
* **LLM Engine:** Groq (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) or Google Gemini (`gemini-flash-latest`, `gemini-3-flash-preview`).
* **FastAPI Streaming:** Real-time Server-Sent Events (SSE) token streaming.

---

## 🛠️ Quick Installation

```bash
pip install fastapi uvicorn fastembed rank-bm25 pypdf requests pydantic
```

*(Optional: For PostgreSQL with pgvector, install `sqlalchemy psycopg2-binary pgvector`)*

---

## 🚀 Running the Standalone API Server

Set your API keys:
```bash
set GROQ_API_KEY=your_groq_api_key
# and/or
set GEMINI_API_KEY=your_gemini_api_key
```

Start the FastAPI server:
```bash
python -m uvicorn rag_core_portable.main:app --port 8000 --reload
```

---

## 📋 Endpoints

### 1. Ingest Raw Text into Vector Store
`POST /api/rag/ingest`
```json
{
  "doc_ref": "hr_policy_2026",
  "title": "Company Leave & Attendance Policy",
  "text": "Annual leave allocation is 25 days per calendar year. Requests must be submitted 2 weeks in advance."
}
```

### 2. Upload Document or Image (PDF / DOCX / Image OCR)
`POST /api/rag/upload-file` (Multipart file upload)
* Automatically extracts text with Baidu Unlimited-OCR / `pypdf`, chunks into 500-600 char passages, and indexes vectors.

### 3. Ask Question with Streaming Response (SSE)
`POST /api/chat`
```json
{
  "message": "What is the annual leave allocation and advance notice required?",
  "llm_provider": "groq",
  "model_name": "llama-3.3-70b-versatile"
}
```

Returns streaming Server-Sent Events (SSE) tokens:
```
data: {"token": "Based "}

data: {"token": "on "}

data: {"token": "the "}

...

data: {"done": true}
```
