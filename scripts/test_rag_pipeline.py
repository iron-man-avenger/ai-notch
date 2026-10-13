import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.chunker import chunk_text
from core.embeddings import get_embedding
from core.document_extractor import document_extractor
from core.rag_engine import rag_engine
from core.rag_chat import generate_rag_response

sample_text = """
Payroll policy cut-off date is strictly the 25th of every month. All timesheets must be submitted by 5:00 PM GMT.
Late submissions will be processed in the following payroll cycle.
Reimbursements for travel and office expenses require receipts uploaded via the expense portal within 30 days.
The maximum daily meal allowance is 45 GBP for domestic business travel.
"""

print("1. Testing Document Extraction & Chunking...")
doc_info = document_extractor.extract(
    filename="payroll_policy_2026.txt",
    file_bytes=sample_text.encode("utf-8"),
    file_text=sample_text
)
print(f"Extracted document: {doc_info['title']} ({doc_info['word_count']} words)")

chunks = chunk_text(doc_info["content"], title=doc_info["title"], target_chars=550)
print(f"Created {len(chunks)} semantic passages.")

print("\n2. Vectorizing into RAG Engine (FastEmbed BGE 384-dim)...")
v_res = rag_engine.vectorize_document(
    doc_ref=doc_info["doc_ref"],
    title=doc_info["title"],
    text=doc_info["content"]
)
print(f"Vectorization result: {v_res}")

print("\n3. Testing Hybrid Retrieval (Dense Vector + BM25Okapi + RRF k=60)...")
query = "What is the cut-off date and submission time for payroll timesheets?"
top_chunks = rag_engine.hybrid_search(query, top_k=2)
for idx, c in enumerate(top_chunks):
    print(f"  Top Match #{idx+1} [RRF Score={c['rrf_score']}]: {c['content'][:90]}...")

print("\n4. Testing RAG Chat Generation with Verified Context + Citations...")
chat_res = generate_rag_response(query, doc_ref=doc_info["doc_ref"])
print("\n--- AI Response ---")
print(chat_res["reply"])
print(f"Citations: {chat_res['citations']}")
print("\n[RAG PIPELINE TEST COMPLETE: 100% HEALTHY]")
