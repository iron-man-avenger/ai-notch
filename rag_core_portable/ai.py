# ==============================================================================
# 2. OPEN-SOURCE EMBEDDING GENERATOR (ai.py)
# Uses FastEmbed (BAAI/bge-small-en-v1.5) - 100% open-source, runs on CPU via ONNX.
# ==============================================================================

from typing import List
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        # High-accuracy open-source embedding model (384 dimensions)
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model

def get_embedding(text: str) -> List[float]:
    """Converts raw text into a 384-dimensional dense semantic vector."""
    clean_text = text.replace("\n", " ").strip()
    if not clean_text:
        return [0.0] * 384
    model = get_model()
    embeddings = list(model.embed([clean_text]))
    return [float(x) for x in embeddings[0]]

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Converts a batch of texts into vectors in a single efficient forward pass."""
    clean_texts = [t.replace("\n", " ").strip() or " " for t in texts]
    model = get_model()
    embeddings = list(model.embed(clean_texts))
    return [[float(x) for x in emb] for emb in embeddings]

def cosine_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine distance (1 - cosine_similarity). Lower means closer."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 1.0
    return float(1.0 - (dot / norm))
