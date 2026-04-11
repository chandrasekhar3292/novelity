# app/core/similarity.py

import numpy as np
from typing import Dict, List, Optional

from app.corpus.embedder import Embedder
from app.corpus.index import VectorIndex
from app.config import settings

# Module-level singletons — loaded once at startup via init()
_embedder: Optional[Embedder] = None
_index: Optional[VectorIndex] = None
_papers: Optional[List[dict]] = None


def init(embedder: Embedder, index: Optional[VectorIndex], papers: Optional[List[dict]] = None) -> None:
    """Call once at startup to set shared model and index."""
    global _embedder, _index, _papers
    _embedder = embedder
    _index = index
    _papers = papers


def is_ready() -> bool:
    return _embedder is not None and _index is not None


def _build_category_map(papers: List[dict]) -> Dict[str, set]:
    """Build a reverse index: category -> set of paper indices."""
    cat_map: Dict[str, set] = {}
    for i, p in enumerate(papers):
        for cat in (p.get("concepts") or []):
            cat_key = cat.lower().strip()
            if cat_key:
                cat_map.setdefault(cat_key, set()).add(i)
    return cat_map


def _match_categories(idea_concepts: List[str], cat_map: Dict[str, set]) -> set:
    """Find paper indices that share at least one category with the idea."""
    matched = set()
    for concept in idea_concepts:
        key = concept.lower().strip()
        # Direct match
        if key in cat_map:
            matched |= cat_map[key]
        # Partial match (e.g. "machine learning" matches "cs.lg" via substring)
        for cat, indices in cat_map.items():
            if key in cat or cat in key:
                matched |= indices
    return matched


class SimilarityEngine:
    """
    Handles semantic similarity retrieval and signal extraction.
    Uses module-level singletons so the model/index load only once.

    Category-aware: when idea concepts are provided, results are
    re-ranked to prioritize papers from matching categories while
    still including cross-domain matches.
    """

    _EMPTY = {
        "top_indices": [],
        "scores": [],
        "max_similarity": 0.0,
        "mean_similarity": 0.0,
        "similarity_spread": 0.0,
    }

    def analyze(
        self,
        idea_text: str,
        idea_concepts: Optional[List[str]] = None,
    ) -> Dict:
        """
        Returns similarity-based novelty signals.

        If idea_concepts are provided and papers are loaded, results
        are re-ranked: category-matched papers are boosted, but
        cross-domain matches are still included.
        """
        if not is_ready():
            return dict(self._EMPTY)

        idea_vector = _embedder.embed_text(idea_text)

        # Retrieve more candidates than needed so we can filter + re-rank
        fetch_k = settings.TOP_K * 3 if idea_concepts and _papers else settings.TOP_K
        indices, scores = _index.search(idea_vector, top_k=fetch_k)

        if not scores:
            return dict(self._EMPTY)

        # Category-aware re-ranking
        if idea_concepts and _papers:
            cat_map = _build_category_map(_papers)
            matched_indices = _match_categories(idea_concepts, cat_map)

            # Split into category-matched and cross-domain
            in_domain = []
            cross_domain = []
            for idx, score in zip(indices, scores):
                if idx < 0:
                    continue
                if idx in matched_indices:
                    in_domain.append((idx, score))
                else:
                    cross_domain.append((idx, score))

            # Re-rank: take category matches first (by score), then fill
            # remaining slots with cross-domain (keeps diversity)
            top_k = settings.TOP_K
            domain_slots = min(len(in_domain), int(top_k * 0.7))  # up to 70% from domain
            cross_slots = top_k - domain_slots

            ranked = in_domain[:domain_slots] + cross_domain[:cross_slots]
            # Re-sort by score so the output is score-ordered
            ranked.sort(key=lambda x: x[1], reverse=True)

            indices = [r[0] for r in ranked]
            scores = [r[1] for r in ranked]

        else:
            # No concepts — use raw FAISS results
            indices = [i for i in indices if i >= 0][:settings.TOP_K]
            scores = scores[:len(indices)]

        scores_arr = np.array(scores)

        return {
            "top_indices": indices,
            "scores": scores,
            "max_similarity": float(scores_arr.max()),
            "mean_similarity": float(scores_arr.mean()),
            "similarity_spread": float(scores_arr.std()),
        }
