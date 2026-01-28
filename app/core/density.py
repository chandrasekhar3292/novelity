# app/core/density.py

from typing import Dict, List
from collections import Counter


def compute_density(
    similar_papers: List[Dict],
    window_years: int = 5
) -> float:
    """
    Density Score = (# papers in recent window) / (window_years)

    similar_papers schema:
    {
        "year": int,
        ...
    }
    """

    if not similar_papers:
        return 0.0

    years = [p["year"] for p in similar_papers]

    max_year = max(years)
    min_allowed_year = max_year - window_years + 1

    recent_count = sum(
        1 for y in years if y >= min_allowed_year
    )

    density_score = recent_count / window_years
    return float(density_score)
