# app/core/fuzzy.py
"""
Fuzzy membership functions for novelty signals.
Replaces hard cutoffs (0.79 vs 0.81) with smooth transitions.
Membership curves are shaped by corpus percentiles — no magic numbers.
"""

import math
from typing import Dict

from app.core.corpus_stats import CorpusStats


def _sigmoid(x: float, center: float, steepness: float = 10.0) -> float:
    """Smooth S-curve: 0→1 transition centered at `center`."""
    z = steepness * (x - center)
    z = max(-20.0, min(20.0, z))  # clamp to avoid overflow
    return 1.0 / (1.0 + math.exp(-z))


def _inverse_sigmoid(x: float, center: float, steepness: float = 10.0) -> float:
    """Smooth 1→0 transition (high value = low membership)."""
    return 1.0 - _sigmoid(x, center, steepness)


def _bell(x: float, center: float, width: float) -> float:
    """Gaussian bell curve membership: peaks at center."""
    if width <= 0:
        return 1.0 if abs(x - center) < 1e-6 else 0.0
    return math.exp(-0.5 * ((x - center) / width) ** 2)


class FuzzyMembership:
    """
    Compute fuzzy membership degrees for each novelty signal.
    Each signal produces memberships in {low, medium, high}.

    Boundaries come from corpus percentiles:
    - low/medium boundary  = 25th percentile
    - medium/high boundary = 75th percentile
    """

    def __init__(self, stats: CorpusStats):
        self.stats = stats

    def _get_boundaries(self, signal: str):
        percentiles = getattr(self.stats, f"{signal}_percentiles", {})
        low_mid = percentiles.get(25, 0.3)
        mid_high = percentiles.get(75, 0.7)
        # Ensure separation
        if mid_high <= low_mid:
            mid_high = low_mid + 0.1
        return low_mid, mid_high

    def similarity_membership(self, value: float) -> Dict[str, float]:
        """
        For similarity: HIGH similarity = NOT novel (inverse relationship).
        """
        low_mid, mid_high = self._get_boundaries("similarity")
        steepness = 12.0 / max(mid_high - low_mid, 0.01)

        return {
            "low": _inverse_sigmoid(value, low_mid, steepness),
            "medium": _bell(value, (low_mid + mid_high) / 2, (mid_high - low_mid) / 2),
            "high": _sigmoid(value, mid_high, steepness),
        }

    def density_membership(self, value: float) -> Dict[str, float]:
        low_mid, mid_high = self._get_boundaries("density")
        steepness = 12.0 / max(mid_high - low_mid, 0.01)

        return {
            "low": _inverse_sigmoid(value, low_mid, steepness),
            "medium": _bell(value, (low_mid + mid_high) / 2, (mid_high - low_mid) / 2),
            "high": _sigmoid(value, mid_high, steepness),
        }

    def recency_membership(self, value: float) -> Dict[str, float]:
        low_mid, mid_high = self._get_boundaries("recency")
        steepness = 12.0 / max(mid_high - low_mid, 0.01)

        return {
            "low": _inverse_sigmoid(value, low_mid, steepness),
            "medium": _bell(value, (low_mid + mid_high) / 2, (mid_high - low_mid) / 2),
            "high": _sigmoid(value, mid_high, steepness),
        }

    def crosslink_membership(self, value: float) -> Dict[str, float]:
        """
        For crosslink: HIGH crosslink = novel concept combinations.
        """
        low_mid, mid_high = self._get_boundaries("crosslink")
        steepness = 12.0 / max(mid_high - low_mid, 0.01)

        return {
            "low": _inverse_sigmoid(value, low_mid, steepness),
            "medium": _bell(value, (low_mid + mid_high) / 2, (mid_high - low_mid) / 2),
            "high": _sigmoid(value, mid_high, steepness),
        }

    def compute_all(self, features: Dict) -> Dict[str, Dict[str, float]]:
        """Compute fuzzy memberships for all signals at once."""
        return {
            "similarity": self.similarity_membership(features["max_similarity"]),
            "density": self.density_membership(features["density_score"]),
            "recency": self.recency_membership(features["recency_score"]),
            "crosslink": self.crosslink_membership(features["crosslink_score"]),
        }
