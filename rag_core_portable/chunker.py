# ==============================================================================
# 3. CHUNKING & INGESTION ENGINE (chunker.py)
# Splits text into 500-600 character semantic passages on sentence boundaries.
# ==============================================================================

import re
from typing import List, Dict, Any

def chunk_document(text: str, title: str = "", target_chars: int = 550) -> List[Dict[str, Any]]:
    """Splits raw text into ~500-600 char semantic passages."""
    if not text or not text.strip():
        return []

    # Clean and split text on sentence boundaries
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        sentences = lines if lines else [text.strip()]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for s in sentences:
        if len(current_chunk) + len(s) > target_chars and current_chunk:
            chunks.append({
                "chunk_index": chunk_index,
                "title": title,
                "content": current_chunk.strip()
            })
            current_chunk = s
            chunk_index += 1
        else:
            current_chunk += (" " if current_chunk else "") + s

    if current_chunk and current_chunk.strip():
        chunks.append({
            "chunk_index": chunk_index,
            "title": title,
            "content": current_chunk.strip()
        })

    return chunks
