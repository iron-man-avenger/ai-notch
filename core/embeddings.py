import os
import re
from typing import List, Optional
import numpy as np

_model_instance = None

def get_embedding_model():
    """Lazy loader for open-source FastEmbed embedding model (BAAI/bge-small-en-v1.5)."""
    global _model_instance
    if _model_instance is None:
        try:
            from fastembed import TextEmbedding
            # Uses BAAI/bge-small-en-v1.5 by default: 384 dimensions, super-fast ONNX runtime
            _model_instance = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            print("[Embeddings] FastEmbed open-source model 'BAAI/bge-small-en-v1.5' initialized.")
        except Exception as e:
            print(f"[Embeddings] FastEmbed initialization error: {e}")
            _model_instance = False
    return _model_instance

def get_embedding(text: str) -> List[float]:
    """
    Converts raw text into a dense semantic vector using the open-source model.
    Returns a normalized float array.
    """
    clean_text = text.replace("\n", " ").strip()
    if not clean_text:
        return [0.0] * 384

    model = get_embedding_model()
    if model:
        try:
            generator = model.embed([clean_text])
            vector = list(generator)[0]
            # Convert numpy array to standard python float list
            return [float(x) for x in vector]
        except Exception as err:
            print(f"[Embeddings Error] {err}")

    # Fallback deterministic pseudo-embedding (384 dimensions) if model fails
    h = hash(clean_text)
    np.random.seed(abs(h) % (2**31))
    vec = np.random.randn(384).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return [float(x) for x in vec]

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Converts a batch of texts into semantic vectors in a single pass."""
    if not texts:
        return []
    clean_texts = [t.replace("\n", " ").strip() or " " for t in texts]
    model = get_embedding_model()
    if model:
        try:
            results = list(model.embed(clean_texts))
            return [[float(x) for x in v] for v in results]
        except Exception as err:
            print(f"[Batch Embeddings Error] {err}")
    return [get_embedding(t) for t in clean_texts]

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
