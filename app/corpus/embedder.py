# app/corpus/embedder.py

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class Embedder:
    """
    SBERT wrapper.
    Ensures consistent embeddings for corpus and ideas.
    """

    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed_text(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            raise ValueError("Text for embedding is empty")

        vec = self.model.encode(
            text,
            normalize_embeddings=True
        )
        return np.array(vec, dtype="float32")

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        if not texts:
            raise ValueError("Empty text batch")

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True
        )
        return np.array(vectors, dtype="float32")
