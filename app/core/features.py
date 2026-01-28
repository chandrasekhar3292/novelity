# app/core/features.py

from typing import Dict


def build_feature_vector(
    similarity: Dict,
    density_score: float,
    recency_score: float,
    crosslink_score: float
) -> Dict:
    """
    Combines all novelty signals into a single feature representation.
    """

    return {
        "max_similarity": similarity.get("max_similarity", 0.0),
        "mean_similarity": similarity.get("mean_similarity", 0.0),
        "similarity_spread": similarity.get("similarity_spread", 0.0),
        "density_score": density_score,
        "recency_score": recency_score,
        "crosslink_score": crosslink_score,
    }
