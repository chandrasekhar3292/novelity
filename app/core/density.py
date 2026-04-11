# app/core/density.py

from typing import Dict, List


def compute_density(
    similar_papers: List[Dict],
    similarity_threshold: float = 0.85,
) -> float:
    """
    Density = how tightly clustered the top-K nearest neighbors are around
    the top match.

    Concretely: count how many of the top-K papers have a similarity ≥
    `similarity_threshold` × top_similarity. A dense research area produces
    many tightly-clustered neighbors (large count); a sparse area has the
    top match standing alone (count near 1).

    Returns a value in [0, len(similar_papers)] — typically 0 to 10.

    Note: this implementation is corpus-temporal-spread independent. The
    previous formula (`papers_in_last_5_years / 5`) was degenerate on
    single-year corpora and always returned 2.0.
    """
    if not similar_papers:
        return 0.0

    sims = [p.get("similarity") for p in similar_papers if p.get("similarity") is not None]
    if not sims:
        # No per-paper scores available — fall back to neighbor count.
        return float(len(similar_papers))

    top = max(sims)
    if top <= 0:
        return 0.0

    cutoff = top * similarity_threshold
    return float(sum(1 for s in sims if s >= cutoff))
