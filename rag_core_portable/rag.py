# ==============================================================================
# 4. HYBRID SEARCH ENGINE (rag.py)
# Reciprocal Rank Fusion (RRF k=60) combining Dense Vector + BM25 Keyword Search
# ==============================================================================

import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from rag_core_portable.ai import get_embedding, cosine_distance

def hybrid_search_chunks(
    chunks: List[Dict[str, Any]],
    query: str,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """
    Executes pure mathematically rigorous Hybrid Retrieval:
    1. Dense Vector Search (Cosine Distance)
    2. Sparse Keyword Search (BM25Okapi exact matching)
    3. Reciprocal Rank Fusion (RRF, k=60): Score = 1/(60 + DenseRank) + 1/(60 + BM25Rank)
    """
    if not chunks or not query.strip():
        return []

    # 1. Dense Vector Search (Cosine Distance)
    query_vector = get_embedding(query)
    dense_scores = []
    for c in chunks:
        c_emb = c.get("embedding")
        dist = cosine_distance(query_vector, c_emb) if c_emb else 1.0
        dense_scores.append((c, dist))

    # Sort ascending by distance (closer = better)
    dense_scores.sort(key=lambda x: x[1])
    dense_results = [c for c, dist in dense_scores[:15]]
    dense_ranks = {c["id"]: rank for rank, c in enumerate(dense_results)}

    # 2. Sparse Keyword Search (BM25)
    tokenized_corpus = [
        re.findall(r"\w+", f"{c.get('title', '')} {c.get('content', '')}".lower())
        for c in chunks
    ]
    bm25 = BM25Okapi(tokenized_corpus)
    q_tokens = re.findall(r"\w+", query.lower())
    scores = bm25.get_scores(q_tokens) if q_tokens else [0.0] * len(chunks)

    sparse_sorted = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    sparse_ranks = {c["id"]: rank for rank, (c, score) in enumerate(sparse_sorted[:15]) if score > 0}

    # 3. Reciprocal Rank Fusion (RRF, k=60)
    rrf_k = 60
    rrf_scores: Dict[Any, float] = {}
    chunk_map = {c["id"]: c for c in chunks}

    for cid, rank in dense_ranks.items():
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    for cid, rank in sparse_ranks.items():
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    
    results = []
    for cid in sorted_ids[:top_k]:
        item = chunk_map[cid].copy()
        item["rrf_score"] = round(rrf_scores[cid], 5)
        results.append(item)

    return results
