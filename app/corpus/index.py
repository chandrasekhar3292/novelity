# app/corpus/index.py

import os
import faiss
import numpy as np
from typing import List, Tuple

from app.config import settings


class VectorIndex:
    """
    FAISS cosine similarity index (via normalized vectors).
    """

    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)

    def add(self, vectors: np.ndarray):
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError("Vector dimension mismatch")

        self.index.add(vectors)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = None
    ) -> Tuple[List[int], List[float]]:

        if top_k is None:
            top_k = settings.TOP_K

        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        scores, indices = self.index.search(query_vector, top_k)

        return indices[0].tolist(), scores[0].tolist()

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        faiss.write_index(self.index, path)

    @staticmethod
    def load(path: str) -> "VectorIndex":
        if not os.path.exists(path):
            raise FileNotFoundError(f"FAISS index not found at {path}")

        index = faiss.read_index(path)
        vi = VectorIndex(index.d)
        vi.index = index
        return vi
