# app/core/similarity.py

import numpy as np
from typing import Dict, List, Optional

from app.corpus.embedder import Embedder
from app.corpus.index import VectorIndex
from app.config import settings

# Module-level singletons — loaded once at startup via init()
_embedder: Optional[Embedder] = None
_index: Optional[VectorIndex] = None


def init(embedder: Embedder, index: Optional[VectorIndex]) -> None:
    """Call once at startup to set shared model and index."""
    global _embedder, _index
    _embedder = embedder
    _index = index


def is_ready() -> bool:
    return _embedder is not None and _index is not None


class SimilarityEngine:
    """
    Handles semantic similarity retrieval and signal extraction.
    Uses module-level singletons so the model/index load only once.
    """

    def analyze(self, idea_text: str) -> Dict:
        """
        Returns similarity-based novelty signals.
        """
        if not is_ready():
            return {
                "top_indices": [],
                "scores": [],
                "max_similarity": 0.0,
                "mean_similarity": 0.0,
                "similarity_spread": 0.0,
            }

        idea_vector = _embedder.embed_text(idea_text)
        indices, scores = _index.search(idea_vector, top_k=settings.TOP_K)

        if not scores:
            return {
                "top_indices": [],
                "scores": [],
                "max_similarity": 0.0,
                "mean_similarity": 0.0,
                "similarity_spread": 0.0,
            }

        scores_arr = np.array(scores)

        return {
            "top_indices": indices,
            "scores": scores,
            "max_similarity": float(scores_arr.max()),
            "mean_similarity": float(scores_arr.mean()),
            "similarity_spread": float(scores_arr.std()),
        }
