# app/core/similarity.py

import numpy as np
from typing import Dict, List

from app.corpus.embedder import Embedder
from app.corpus.index import VectorIndex
from app.config import settings


class SimilarityEngine:
    """
    Handles semantic similarity retrieval and signal extraction.
    """

    def __init__(self):
        self.embedder = Embedder()
        self.index = VectorIndex.load(settings.FAISS_INDEX_PATH)

    def analyze(self, idea_text: str) -> Dict:
        """
        Returns similarity-based novelty signals.
        """

        idea_vector = self.embedder.embed_text(idea_text)

        indices, scores = self.index.search(
            idea_vector,
            top_k=settings.TOP_K
        )

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
