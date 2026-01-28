# app/core/crosslink.py

from typing import List, Dict
from itertools import combinations
from collections import defaultdict


def compute_crosslink_score(
    idea_concepts: List[str],
    corpus_papers: List[Dict]
) -> float:
    """
    Cross-Link Score measures how rare the concept combinations are.

    idea_concepts: concepts extracted from idea (OpenAI)
    corpus_papers: list of papers with 'concepts' field
    """

    if len(idea_concepts) < 2:
        return 0.0

    # Normalize concepts
    idea_concepts = [c.lower() for c in idea_concepts]

    # Build co-occurrence counts
    co_occurrence = defaultdict(int)
    concept_counts = defaultdict(int)

    for paper in corpus_papers:
        paper_concepts = set(
            c.lower() for c in paper.get("concepts", [])
        )

        for c in paper_concepts:
            concept_counts[c] += 1

        for c1, c2 in combinations(sorted(paper_concepts), 2):
            co_occurrence[(c1, c2)] += 1

    scores = []

    for c1, c2 in combinations(sorted(idea_concepts), 2):
        pair = (c1, c2)
        pair_count = co_occurrence.get(pair, 0)

        # Rare pairs → high novelty
        rarity = 1 / (1 + pair_count)
        scores.append(rarity)

    if not scores:
        return 0.0

    # Average rarity across all pairs
    return float(sum(scores) / len(scores))
