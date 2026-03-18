# app/corpus/recency.py

from typing import Dict, List
from collections import Counter


def compute_recency(
    similar_papers: List[Dict],
    recent_years: int = 3,
    past_years: int = 5
) -> float:
    """
    Recency Score =
    (# papers in last recent_years) /
    (# papers in previous past_years)

    Returns:
    - >1  : growing area
    - ~1  : stable
    - <1  : declining
    """

    if not similar_papers:
        return 0.0

    years = [p["year"] for p in similar_papers]
    max_year = max(years)

    recent_start = max_year - recent_years + 1
    past_start = recent_start - past_years

    recent_count = sum(y >= recent_start for y in years)
    past_count = sum(
        past_start <= y < recent_start for y in years
    )

    if past_count == 0:
        return float(recent_count)  # avoid divide-by-zero

    return float(recent_count / past_count)
