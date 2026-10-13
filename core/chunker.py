import re
from typing import List, Dict, Any

def chunk_text(text: str, title: str = "", target_chars: int = 550) -> List[Dict[str, Any]]:
    """
    Splits text into semantic passages of ~500-600 characters based on sentence boundaries,
    preserving title context for high-precision hybrid retrieval.
    """
    if not text or not text.strip():
        return []

    # 1. Clean and split text into sentence boundaries
    # Split on sentence end punctuation followed by whitespace
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    
    # Fallback if no sentence boundaries found (e.g. code or lists)
    if not sentences:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        sentences = lines if lines else [text.strip()]

    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    chunk_index = 0

    for s in sentences:
        # Group sentences into ~500-600 characters per chunk
        if len(current_chunk) + len(s) > target_chars and current_chunk:
            chunks.append({
                "chunk_index": chunk_index,
                "title": title,
                "content": current_chunk.strip(),
                "char_count": len(current_chunk.strip())
            })
            current_chunk = s
            chunk_index += 1
        else:
            current_chunk += (" " if current_chunk else "") + s

    if current_chunk and current_chunk.strip():
        chunks.append({
            "chunk_index": chunk_index,
            "title": title,
            "content": current_chunk.strip(),
            "char_count": len(current_chunk.strip())
        })

    return chunks
