import os
import re
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

from core.db import get_db, init_db
from core.chunker import chunk_text
from core.embeddings import get_embedding, get_embeddings_batch, cosine_similarity

class RAGEngine:
    """
    Production-grade Hybrid RAG Engine combining:
    1. Dense Vector Search (Cosine distance over open-source BGE embeddings)
    2. Sparse Keyword Search (BM25Okapi exact matching)
    3. Reciprocal Rank Fusion (RRF k=60)
    """
    def __init__(self):
        init_db()

    def vectorize_document(self, doc_ref: str, title: str, text: str, heading: str = "") -> Dict[str, Any]:
        """
        Takes raw document text, splits into 500-600 char semantic passages,
        generates open-source embeddings, and saves into vector store.
        """
        if not text or not text.strip():
            return {"doc_ref": doc_ref, "title": title, "chunk_count": 0}

        # 1. Clean and chunk text into semantic passages
        chunks = chunk_text(text, title=title, target_chars=550)
        if not chunks:
            return {"doc_ref": doc_ref, "title": title, "chunk_count": 0}

        # 2. Batch generate vectors using open-source model
        batch_prompts = [f"{title}: {c['content']}" for c in chunks]
        embeddings = get_embeddings_batch(batch_prompts)

        # 3. Store in database
        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.now().isoformat()

        # Remove existing chunks for this doc_ref if re-indexing
        cursor.execute("DELETE FROM document_chunks WHERE doc_ref = ?", (doc_ref,))

        for idx, c in enumerate(chunks):
            emb_json = json.dumps(embeddings[idx]) if idx < len(embeddings) else json.dumps([])
            cursor.execute("""
            INSERT INTO document_chunks (doc_ref, title, heading, content, embedding, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_ref,
                title,
                heading or f"Section {idx + 1}",
                c["content"],
                emb_json,
                now_iso
            ))

        conn.commit()
        conn.close()

        print(f"[RAG Engine] Indexed '{title}' (doc_ref: {doc_ref}) with {len(chunks)} semantic chunks.")
        return {
            "doc_ref": doc_ref,
            "title": title,
            "chunk_count": len(chunks)
        }

    def hybrid_search(self, query: str, top_k: int = 4, doc_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes Hybrid Retrieval:
        1. Dense Vector Search (Cosine Distance) -> top 15
        2. Sparse Keyword Search (BM25) -> top 15
        3. Reciprocal Rank Fusion (RRF k=60) -> top_k
        """
        if not query or not query.strip():
            return []

        conn = get_db()
        cursor = conn.cursor()

        if doc_ref:
            cursor.execute("SELECT id, doc_ref, title, heading, content, embedding FROM document_chunks WHERE doc_ref = ?", (doc_ref,))
        else:
            cursor.execute("SELECT id, doc_ref, title, heading, content, embedding FROM document_chunks")

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        all_chunks: List[Dict[str, Any]] = []
        for r in rows:
            emb_list = []
            if r["embedding"]:
                try:
                    emb_list = json.loads(r["embedding"])
                except Exception:
                    emb_list = []
            all_chunks.append({
                "id": r["id"],
                "doc_ref": r["doc_ref"],
                "title": r["title"],
                "heading": r["heading"] or "",
                "content": r["content"],
                "embedding": emb_list
            })

        # ── 1. Dense Vector Search (Cosine Similarity) ───────────
        query_vector = get_embedding(query)
        dense_candidates = []
        for c in all_chunks:
            if c["embedding"]:
                sim = cosine_similarity(query_vector, c["embedding"])
                dense_candidates.append((c, sim))

        dense_candidates.sort(key=lambda x: x[1], reverse=True)
        dense_results = [c for c, sim in dense_candidates[:15]]
        dense_ranks = {c["id"]: rank for rank, c in enumerate(dense_results)}

        # ── 2. Sparse Keyword Search (BM25) ──────────────────────
        tokenized_corpus = [
            re.findall(r"\w+", f"{c['title']} {c['heading']} {c['content']}".lower()) 
            for c in all_chunks
        ]
        q_tokens = re.findall(r"\w+", query.lower())

        try:
            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(q_tokens) if q_tokens else [0.0] * len(all_chunks)
        except Exception:
            bm25_scores = [0.0] * len(all_chunks)

        sparse_candidates = list(zip(all_chunks, bm25_scores))
        sparse_candidates.sort(key=lambda x: x[1], reverse=True)
        sparse_results = [c for c, score in sparse_candidates[:15] if score > 0]
        sparse_ranks = {c["id"]: rank for rank, c in enumerate(sparse_results)}

        # ── 3. Reciprocal Rank Fusion (RRF, k=60) ────────────────
        rrf_k = 60
        rrf_scores: Dict[int, float] = {}
        chunk_map = {c["id"]: c for c in all_chunks}

        for cid, rank in dense_ranks.items():
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        for cid, rank in sparse_ranks.items():
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # Sort IDs by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        final_chunks = []
        for cid in sorted_ids[:top_k]:
            item = chunk_map[cid].copy()
            item["rrf_score"] = round(rrf_scores[cid], 5)
            # Remove raw vector from returned chunk dict for lightweight serialization
            item.pop("embedding", None)
            final_chunks.append(item)

        return final_chunks

    def list_documents(self) -> List[Dict[str, Any]]:
        """Lists all indexed documents and chunk statistics."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT doc_ref, title, COUNT(id) as chunk_count, MIN(created_at) as created_at
        FROM document_chunks
        GROUP BY doc_ref, title
        ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "doc_ref": r["doc_ref"],
                "title": r["title"],
                "chunk_count": r["chunk_count"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    def delete_document(self, doc_ref: str) -> bool:
        """Removes all indexed chunks for a document."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_chunks WHERE doc_ref = ?", (doc_ref,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def clear_all(self):
        """Clears all indexed chunks."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_chunks")
        conn.commit()
        conn.close()

rag_engine = RAGEngine()
