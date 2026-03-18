"""Sentence embedding using sentence-transformers"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def encode(texts: list[str]) -> np.ndarray:
    """Encode texts into normalized embeddings (unit vectors for cosine similarity)."""
    model = get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 50,
        batch_size=32,
    )
