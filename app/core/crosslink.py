# app/core/crosslink.py

import math
from typing import List, Dict, Optional, Sequence
from itertools import combinations
from collections import defaultdict


def compute_crosslink_score(
    idea_concepts: List[str],
    corpus_papers: List[Dict],
    similar_papers: Optional[Sequence[Dict]] = None,
) -> float:
    """
    Cross-link rarity: how unusual is it for the topics this idea touches
    to appear together in the same paper?

    The corpus stores concepts as arXiv categories ("cs.CV", "cs.AI", ...).
    LLM-extracted idea_concepts are English phrases ("Diffusion-based
    Inpainting", "Object Removal") and never match arXiv codes directly,
    so a naive set-intersection always reports zero co-occurrence and the
    score collapses to 1.0 for every input.

    Workaround: when `similar_papers` is provided, use the union of arXiv
    categories from the top-K nearest neighbors as the "topics" the idea
    touches. Then compute, for every pair of those categories, the inverse
    co-occurrence frequency in the full corpus. Cross-domain ideas — where
    the neighbors span unrelated categories that rarely co-occur — score
    high. Within-domain ideas — where neighbors all share cs.LG/cs.CL —
    score low.

    Falls back to the legacy idea_concepts path when similar_papers is
    not supplied (preserves existing call sites in the eval scripts).
    """

    # Build co-occurrence + individual counts for the corpus once.
    co_occurrence: Dict[tuple, int] = defaultdict(int)
    cat_counts: Dict[str, int] = defaultdict(int)
    for paper in corpus_papers:
        cats = set(c.lower() for c in paper.get("concepts", []))
        for c in cats:
            cat_counts[c] += 1
        for c1, c2 in combinations(sorted(cats), 2):
            co_occurrence[(c1, c2)] += 1

    # --- Preferred path: derive topics from nearest-neighbor categories ---
    if similar_papers:
        neighbor_cats: Dict[str, int] = defaultdict(int)
        for p in similar_papers[:10]:
            for c in p.get("concepts", []):
                neighbor_cats[c.lower()] += 1

        # Filter out singletons that appear in only 1 of the 10 neighbors —
        # they're noise from a single off-topic match.
        active_cats = sorted(c for c, n in neighbor_cats.items() if n >= 2)

        # If too few categories survive the filter, broaden to all neighbors.
        if len(active_cats) < 2:
            active_cats = sorted(neighbor_cats.keys())

        if len(active_cats) >= 2:
            # PMI-based rarity. For each pair of neighbor categories, compute
            # how much more (or less) often they co-occur than independent
            # chance would predict, then sigmoid-flip so common pairs map
            # near 0 and rare pairs map near 1.
            #
            # PMI = log( P(c1, c2) / (P(c1) * P(c2)) )
            #     positive → categories co-occur more than chance (related)
            #     negative → categories co-occur less than chance (rare)
            #
            # rarity = 1 - sigmoid(PMI)
            #     PMI ≫ 0  →  rarity ≈ 0   (very common pair)
            #     PMI = 0  →  rarity = 0.5 (independent)
            #     PMI ≪ 0  →  rarity ≈ 1   (very rare pair)
            N = max(len(corpus_papers), 1)
            rarities = []
            for c1, c2 in combinations(active_cats, 2):
                pair_count = co_occurrence.get((c1, c2), 0)
                c1_count = cat_counts.get(c1, 0)
                c2_count = cat_counts.get(c2, 0)
                if c1_count == 0 or c2_count == 0:
                    continue
                p_co = pair_count / N
                p_1 = c1_count / N
                p_2 = c2_count / N
                expected = p_1 * p_2
                if p_co <= 0:
                    # Never co-occur → maximally rare combination.
                    rarities.append(1.0)
                    continue
                pmi = math.log(p_co / expected)
                # Sigmoid: 1 / (1 + e^pmi) — high pmi → near 0, low pmi → near 1.
                rarity = 1.0 / (1.0 + math.exp(pmi))
                rarities.append(rarity)
            if rarities:
                return float(sum(rarities) / len(rarities))

    # --- Legacy fallback path (original behavior) ---
    if len(idea_concepts) < 2:
        return 0.0

    idea_norm = [c.lower() for c in idea_concepts]
    scores = []
    for c1, c2 in combinations(sorted(idea_norm), 2):
        pair_count = co_occurrence.get((c1, c2), 0)
        scores.append(1 / (1 + pair_count))

    if not scores:
        return 0.0
    return float(sum(scores) / len(scores))
