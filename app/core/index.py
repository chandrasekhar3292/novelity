"""FAISS index management for corpus search"""

import os

import faiss
import numpy as np

from app.config import settings

_index: faiss.Index | None = None


def get_index() -> faiss.Index | None:
    return _index


def is_loaded() -> bool:
    return _index is not None and _index.ntotal > 0


def build(embeddings: np.ndarray) -> None:
    global _index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product = cosine sim on normalized vectors
    index.add(embeddings.astype(np.float32))
    _index = index


def save() -> None:
    if _index is None:
        return
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    faiss.write_index(_index, settings.FAISS_INDEX_PATH)


def load() -> bool:
    global _index
    if os.path.exists(settings.FAISS_INDEX_PATH):
        _index = faiss.read_index(settings.FAISS_INDEX_PATH)
        return True
    return False


def search(query_embedding: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (similarities, indices) for the top-k nearest neighbors."""
    if _index is None or _index.ntotal == 0:
        return np.array([]), np.array([])
    k = min(k, _index.ntotal)
    query = query_embedding.astype(np.float32).reshape(1, -1)
    similarities, indices = _index.search(query, k)
    return similarities[0], indices[0]
