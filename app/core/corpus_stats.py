# app/core/corpus_stats.py
"""
Compute corpus-level statistics at startup.
These replace hard-coded magic numbers with data-driven percentiles.
"""

import numpy as np
from typing import Dict, List, Optional


class CorpusStats:
    """
    Holds precomputed distributions from the corpus so that
    thresholds, fuzzy boundaries, and Bayesian priors are all
    derived from actual data — not guesses.
    """

    def __init__(self):
        self.similarity_percentiles: Dict[int, float] = {}
        self.density_percentiles: Dict[int, float] = {}
        self.recency_percentiles: Dict[int, float] = {}
        self.crosslink_percentiles: Dict[int, float] = {}

        # Raw distribution params for Bayesian priors
        self.similarity_mean: float = 0.0
        self.similarity_std: float = 1.0
        self.density_mean: float = 0.0
        self.density_std: float = 1.0
        self.recency_mean: float = 0.0
        self.recency_std: float = 1.0
        self.crosslink_mean: float = 0.0
        self.crosslink_std: float = 1.0

        # Adaptive weights — signals with low variance get downweighted
        self.signal_weights: Dict[str, float] = {}

        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def compute(
        self,
        papers: List[dict],
        index,
        embedder,
    ) -> None:
        """
        Sample the corpus to build distributions for each signal.
        Uses a random sample of papers to compute what "typical"
        similarity/density/recency/crosslink looks like.
        """
        from app.core.density import compute_density
        from app.corpus.recency import compute_recency
        from app.core.crosslink import compute_crosslink_score

        if not papers or index is None:
            self._ready = False
            return

        n = len(papers)
        sample_size = min(200, n)
        rng = np.random.RandomState(42)
        sample_indices = rng.choice(n, size=sample_size, replace=False)

        sim_scores = []
        density_scores = []
        recency_scores = []
        crosslink_scores = []

        for idx in sample_indices:
            paper = papers[idx]
            text = f"{paper.get('title', '')}. {paper['abstract']}".strip()

            # Similarity: embed this paper, search corpus
            vec = embedder.embed_text(text)
            raw_indices, raw_scores = index.search(vec, top_k=20)

            # Skip self-match (first result is usually the paper itself)
            scores_filtered = [
                s for i, s in zip(raw_indices, raw_scores)
                if i >= 0 and i != idx
            ]
            if scores_filtered:
                sim_scores.append(max(scores_filtered))

            # Density / recency: use top similar papers, attaching the per-
            # paper similarity scores so the new clustering-based density
            # can compute distances. Without this attachment, every sampled
            # paper produces density=len(neighbors) and the std collapses
            # to zero, marking the signal as not-informative even though it
            # varies meaningfully on real inputs.
            similar_with_scores = []
            for i, s in zip(raw_indices, raw_scores):
                if 0 <= i < n and i != idx and papers[i].get("year"):
                    similar_with_scores.append({
                        **papers[i],
                        "similarity": float(s),
                    })
            if similar_with_scores:
                density_scores.append(compute_density(similar_with_scores))
                recency_scores.append(compute_recency(similar_with_scores))

            # Crosslink: use this paper's concepts
            concepts = paper.get("concepts", [])
            if len(concepts) >= 2:
                crosslink_scores.append(
                    compute_crosslink_score(concepts, papers)
                )

        # Compute percentiles
        percentile_points = [5, 10, 25, 50, 75, 90, 95]

        def _percentiles(values):
            if not values:
                return {p: 0.0 for p in percentile_points}
            arr = np.array(values)
            return {p: float(np.percentile(arr, p)) for p in percentile_points}

        def _stats(values):
            if not values:
                return 0.0, 1.0
            arr = np.array(values)
            return float(arr.mean()), float(max(arr.std(), 1e-6))

        self.similarity_percentiles = _percentiles(sim_scores)
        self.density_percentiles = _percentiles(density_scores)
        self.recency_percentiles = _percentiles(recency_scores)
        self.crosslink_percentiles = _percentiles(crosslink_scores)

        self.similarity_mean, self.similarity_std = _stats(sim_scores)
        self.density_mean, self.density_std = _stats(density_scores)
        self.recency_mean, self.recency_std = _stats(recency_scores)
        self.crosslink_mean, self.crosslink_std = _stats(crosslink_scores)

        # Compute adaptive weights based on coefficient of variation
        # Signals with very low variance are less useful for differentiation
        self._compute_adaptive_weights()

        self._ready = True
        print(f"  Corpus stats computed from {sample_size} samples")
        print(f"    Similarity: mean={self.similarity_mean:.3f}, std={self.similarity_std:.3f}")
        print(f"    Density:    mean={self.density_mean:.3f}, std={self.density_std:.3f}")
        print(f"    Recency:    mean={self.recency_mean:.3f}, std={self.recency_std:.3f}")
        print(f"    Crosslink:  mean={self.crosslink_mean:.3f}, std={self.crosslink_std:.3f}")
        print(f"    Adaptive weights: {self.signal_weights}")

    def _compute_adaptive_weights(self):
        """
        Compute signal weights proportional to their discriminative power.
        Signals with near-zero variance get minimal weight.
        """
        # Coefficient of variation (CV) for each signal
        def _cv(mean, std):
            if abs(mean) < 1e-6:
                return std  # if mean is ~0, use raw std
            return std / abs(mean)

        raw = {
            "similarity": _cv(self.similarity_mean, self.similarity_std),
            "density": _cv(self.density_mean, self.density_std),
            "recency": _cv(self.recency_mean, self.recency_std),
            "crosslink": _cv(self.crosslink_mean, self.crosslink_std),
            "spread": 0.05,  # small baseline weight
        }

        # Base weights (domain knowledge)
        base = {
            "similarity": 0.35,
            "density": 0.20,
            "recency": 0.10,
            "crosslink": 0.25,
            "spread": 0.10,
        }

        # Scale base weights by discriminative power
        # cv_factor: 1.0 if cv >= 0.1 (good variance), down to 0.1 if cv ~ 0
        adjusted = {}
        for signal in base:
            cv = raw.get(signal, 0.05)
            cv_factor = min(1.0, max(0.1, cv / 0.1))
            adjusted[signal] = base[signal] * cv_factor

        # Normalize to sum to 1.0
        total = sum(adjusted.values())
        self.signal_weights = {
            k: round(v / total, 3) for k, v in adjusted.items()
        }

    def get_percentile_rank(self, signal: str, value: float) -> float:
        """
        Returns approximate percentile rank (0-100) of a value
        within the corpus distribution for that signal.
        """
        percentiles = getattr(self, f"{signal}_percentiles", {})
        if not percentiles:
            return 50.0

        points = sorted(percentiles.items())
        # Below minimum
        if value <= points[0][1]:
            return float(points[0][0]) * (value / max(points[0][1], 1e-6))
        # Above maximum
        if value >= points[-1][1]:
            return min(99.0, float(points[-1][0]) + (100 - points[-1][0]) * 0.5)

        # Interpolate between known percentile points
        for i in range(len(points) - 1):
            p1, v1 = points[i]
            p2, v2 = points[i + 1]
            if v1 <= value <= v2:
                if v2 == v1:
                    return float(p1)
                frac = (value - v1) / (v2 - v1)
                return float(p1 + frac * (p2 - p1))

        return 50.0

    def is_signal_informative(self, signal: str, min_cv: float = 0.02) -> bool:
        """Check if a signal has enough variance to be useful."""
        mean = getattr(self, f"{signal}_mean", 0.0)
        std = getattr(self, f"{signal}_std", 0.0)
        if abs(mean) < 1e-6:
            return std > min_cv
        return (std / abs(mean)) > min_cv

    def to_dict(self) -> Dict:
        """Serialize for debugging / API exposure."""
        return {
            "similarity": {
                "percentiles": self.similarity_percentiles,
                "mean": self.similarity_mean,
                "std": self.similarity_std,
                "informative": self.is_signal_informative("similarity"),
            },
            "density": {
                "percentiles": self.density_percentiles,
                "mean": self.density_mean,
                "std": self.density_std,
                "informative": self.is_signal_informative("density"),
            },
            "recency": {
                "percentiles": self.recency_percentiles,
                "mean": self.recency_mean,
                "std": self.recency_std,
                "informative": self.is_signal_informative("recency"),
            },
            "crosslink": {
                "percentiles": self.crosslink_percentiles,
                "mean": self.crosslink_mean,
                "std": self.crosslink_std,
                "informative": self.is_signal_informative("crosslink"),
            },
            "adaptive_weights": self.signal_weights,
        }


# Module-level singleton
_stats: Optional[CorpusStats] = None


def init_stats(papers, index, embedder) -> CorpusStats:
    global _stats
    _stats = CorpusStats()
    _stats.compute(papers, index, embedder)
    return _stats


def get_stats() -> Optional[CorpusStats]:
    return _stats
