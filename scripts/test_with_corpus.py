"""
Test the combined classifier using REAL corpus papers.

Tests:
1. Feed corpus papers back — they should get "Direct Gap Fill" + low novelty score
2. Feed slightly modified corpus papers — should still be "Direct Gap Fill"
3. Feed mashups of 2 distant papers — should get "Cross-Link Novelty"
4. Feed completely fabricated non-AI text — should get "Out-of-Domain"
5. Check score distribution makes sense across the board

Usage:
    python scripts/test_with_corpus.py
"""

import sys
import os
import json
import time
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.corpus.embedder import Embedder
from app.corpus.builder import load_index
from app.corpus.loader import load_papers
from app.core import similarity as sim_module
from app.core.similarity import SimilarityEngine
from app.core.density import compute_density
from app.corpus.recency import compute_recency
from app.core.crosslink import compute_crosslink_score
from app.core.features import build_feature_vector
from app.core.corpus_stats import init_stats, get_stats
from app.core.classifier import classify_novelty
from app.core.explanation import generate_rule_based_explanation


def run_pipeline(idea_text, sim_engine, corpus, concepts=None):
    """Full pipeline for a single idea."""
    if concepts is None:
        from app.core.idea import _fallback_extraction
        tags = _fallback_extraction(idea_text)
        concepts = tags.get("concepts", []) + tags.get("domains", [])

    similarity = sim_engine.analyze(idea_text, idea_concepts=concepts)

    similar_papers = [
        corpus[i] for i in similarity["top_indices"]
        if 0 <= i < len(corpus)
    ]

    density = compute_density(similar_papers)
    recency = compute_recency(similar_papers)

    # Use paper categories from results for realistic crosslink
    paper_concepts = set()
    for p in similar_papers[:10]:
        for c in p.get("concepts", []):
            paper_concepts.add(c)
    mixed_concepts = concepts[:3] + list(paper_concepts)[:5]
    crosslink = compute_crosslink_score(mixed_concepts, corpus)

    features = build_feature_vector(similarity, density, recency, crosslink)
    classification = classify_novelty(features)
    explanation = generate_rule_based_explanation([], features, classification)

    return features, classification, explanation, similar_papers


def test_exact_corpus_papers(sim_engine, corpus, n=30):
    """
    TEST 1: Feed exact corpus papers back through the pipeline.
    Expected: Direct Gap Fill, low novelty score (they ARE existing work).
    """
    print(f"\n{'='*80}")
    print(f"TEST 1: Exact corpus papers (n={n})")
    print(f"Expected: 'Direct Gap Fill', low novelty score")
    print(f"{'='*80}")

    rng = np.random.RandomState(42)
    indices = rng.choice(len(corpus), size=min(n, len(corpus)), replace=False)

    labels = []
    scores = []
    details = []

    for idx in indices:
        paper = corpus[idx]
        text = f"{paper.get('title', '')}. {paper['abstract']}"
        concepts = paper.get("concepts", [])

        features, classification, _, similar = run_pipeline(
            text, sim_engine, corpus, concepts=concepts
        )

        label = classification["label"]
        score = classification.get("novelty_score", -1)
        labels.append(label)
        scores.append(score)
        details.append({
            "title": paper.get("title", "")[:60],
            "sim": features["max_similarity"],
            "label": label,
            "score": score,
            "conf": classification["confidence"],
        })

    # Print sample results
    print(f"\n  Sample results:")
    for d in details[:10]:
        print(f"    [{d['label']:25s}] score={d['score']:5.1f}  sim={d['sim']:.3f}  "
              f"\"{d['title']}...\"")

    # Stats
    dist = dict(Counter(labels))
    gap_fill_rate = labels.count("Direct Gap Fill") / len(labels) * 100
    scores_arr = np.array(scores)

    print(f"\n  Label distribution: {dist}")
    print(f"  'Direct Gap Fill' rate: {gap_fill_rate:.1f}%")
    print(f"  Novelty scores: mean={scores_arr.mean():.1f}, "
          f"std={scores_arr.std():.1f}, "
          f"min={scores_arr.min():.1f}, max={scores_arr.max():.1f}")
    print(f"  Scores < 50 (low novelty, correct): {sum(1 for s in scores if s < 50)}/{n} "
          f"({sum(1 for s in scores if s < 50)/n*100:.0f}%)")

    return gap_fill_rate, scores_arr.mean()


def test_modified_corpus_papers(sim_engine, corpus, n=15):
    """
    TEST 2: Slightly rephrase corpus paper titles+abstracts.
    Expected: Still Direct Gap Fill / low novelty (minor rewording shouldn't change classification).
    """
    print(f"\n{'='*80}")
    print(f"TEST 2: Modified corpus papers (n={n})")
    print(f"Expected: Still 'Direct Gap Fill' or similar, moderate-low novelty")
    print(f"{'='*80}")

    rng = np.random.RandomState(99)
    indices = rng.choice(len(corpus), size=min(n, len(corpus)), replace=False)

    labels = []
    scores = []

    for idx in indices:
        paper = corpus[idx]
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        # Simple modification: swap some words, add prefix
        modified = f"An improved approach to {title.lower()}. We extend prior work by {abstract[:200]}"
        concepts = paper.get("concepts", [])

        features, classification, _, _ = run_pipeline(
            modified, sim_engine, corpus, concepts=concepts
        )

        label = classification["label"]
        score = classification.get("novelty_score", -1)
        labels.append(label)
        scores.append(score)

    scores_arr = np.array(scores)
    dist = dict(Counter(labels))
    gap_fill_rate = labels.count("Direct Gap Fill") / len(labels) * 100

    print(f"\n  Label distribution: {dist}")
    print(f"  'Direct Gap Fill' rate: {gap_fill_rate:.1f}%")
    print(f"  Novelty scores: mean={scores_arr.mean():.1f}, std={scores_arr.std():.1f}")
    print(f"  Scores < 50 (low novelty): {sum(1 for s in scores if s < 50)}/{n}")

    return gap_fill_rate, scores_arr.mean()


def test_paper_mashups(sim_engine, corpus):
    """
    TEST 3: Combine titles/abstracts from papers in DIFFERENT categories.
    Expected: Cross-Link Novelty (bridging two fields).
    """
    print(f"\n{'='*80}")
    print("TEST 3: Paper mashups (combine distant papers)")
    print("Expected: 'Cross-Link Novelty' or 'Independent Novelty'")
    print(f"{'='*80}")

    # Find papers from different categories
    by_cat = {}
    for i, p in enumerate(corpus):
        for c in p.get("concepts", []):
            by_cat.setdefault(c, []).append(i)

    categories = list(by_cat.keys())
    mashups = []

    # Create mashups from different category pairs
    pairs = [
        ("cs.CV", "cs.CL"),
        ("cs.AI", "stat.ML"),
        ("cs.LG", "cs.RO"),
        ("cs.NE", "cs.IR"),
    ]

    for cat1, cat2 in pairs:
        if cat1 in by_cat and cat2 in by_cat:
            p1 = corpus[by_cat[cat1][0]]
            p2 = corpus[by_cat[cat2][-1]]
            mashup_text = (
                f"{p1.get('title', '')}. Combined with concepts from: "
                f"{p2.get('title', '')}. {p1['abstract'][:150]} "
                f"Furthermore, {p2['abstract'][:150]}"
            )
            mashup_concepts = list(set(p1.get("concepts", []) + p2.get("concepts", [])))
            mashups.append((mashup_text, mashup_concepts, cat1, cat2))

    labels = []
    scores = []

    for text, concepts, c1, c2 in mashups:
        features, classification, _, _ = run_pipeline(
            text, sim_engine, corpus, concepts=concepts
        )
        label = classification["label"]
        score = classification.get("novelty_score", -1)
        labels.append(label)
        scores.append(score)

        print(f"\n  [{c1} + {c2}] -> {label:25s} score={score:.1f}  sim={features['max_similarity']:.3f}")

    dist = dict(Counter(labels))
    crosslink_rate = labels.count("Cross-Link Novelty") / max(len(labels), 1) * 100

    print(f"\n  Label distribution: {dist}")
    print(f"  'Cross-Link Novelty' rate: {crosslink_rate:.1f}%")
    if scores:
        print(f"  Novelty scores: mean={np.mean(scores):.1f}")

    return crosslink_rate


def test_out_of_domain(sim_engine, corpus):
    """
    TEST 4: Completely non-AI/ML ideas.
    Expected: Out-of-Domain or very high novelty score.
    """
    print(f"\n{'='*80}")
    print("TEST 4: Out-of-domain ideas (non-AI/ML)")
    print("Expected: 'Out-of-Domain' or 'Independent Novelty' with high score")
    print(f"{'='*80}")

    ood_ideas = [
        "The impact of soil pH levels on earthworm population density in temperate deciduous forests of Northern Europe during seasonal transitions",
        "Comparative analysis of Gothic cathedral buttress engineering techniques in 13th century France versus 14th century England",
        "The role of tidal patterns in shaping salt marsh sediment deposition along the Eastern Atlantic coastline",
        "Effects of fermentation temperature on flavor compound development in traditional Korean kimchi preparation methods",
        "Archaeological evidence of Bronze Age trade routes through analysis of tin isotope ratios in Mediterranean copper alloys",
        "Evaluating the acoustic properties of different hardwood species for violin construction based on density and grain patterns",
    ]

    labels = []
    scores = []

    for idea in ood_ideas:
        features, classification, _, _ = run_pipeline(idea, sim_engine, corpus)
        label = classification["label"]
        score = classification.get("novelty_score", -1)
        labels.append(label)
        scores.append(score)

        print(f"\n  [{label:25s}] score={score:.1f}  sim={features['max_similarity']:.3f}")
        print(f"    \"{idea[:80]}...\"")

    dist = dict(Counter(labels))
    ood_rate = labels.count("Out-of-Domain") / len(labels) * 100
    high_novelty = sum(1 for s in scores if s > 80) / len(scores) * 100

    print(f"\n  Label distribution: {dist}")
    print(f"  'Out-of-Domain' rate: {ood_rate:.1f}%")
    print(f"  Score > 80 (high novelty): {high_novelty:.0f}%")
    if scores:
        print(f"  Novelty scores: mean={np.mean(scores):.1f}")

    return ood_rate


def test_score_consistency(sim_engine, corpus, n=50):
    """
    TEST 5: Check that novelty scores are consistent and well-distributed.
    """
    print(f"\n{'='*80}")
    print(f"TEST 5: Score distribution across {n} random corpus papers")
    print(f"{'='*80}")

    rng = np.random.RandomState(77)
    indices = rng.choice(len(corpus), size=min(n, len(corpus)), replace=False)

    scores = []
    sims = []

    for idx in indices:
        paper = corpus[idx]
        text = f"{paper.get('title', '')}. {paper['abstract']}"
        concepts = paper.get("concepts", [])
        features, classification, _, _ = run_pipeline(
            text, sim_engine, corpus, concepts=concepts
        )
        scores.append(classification.get("novelty_score", 0))
        sims.append(features["max_similarity"])

    scores_arr = np.array(scores)
    sims_arr = np.array(sims)

    # Correlation between similarity and novelty score (should be negative)
    correlation = np.corrcoef(sims_arr, scores_arr)[0, 1]

    print(f"\n  Score distribution:")
    print(f"    Mean: {scores_arr.mean():.1f}  Std: {scores_arr.std():.1f}")
    print(f"    Min: {scores_arr.min():.1f}  Max: {scores_arr.max():.1f}")
    print(f"    Quartiles: 25th={np.percentile(scores_arr, 25):.1f}  "
          f"50th={np.percentile(scores_arr, 50):.1f}  "
          f"75th={np.percentile(scores_arr, 75):.1f}")

    print(f"\n  Similarity distribution:")
    print(f"    Mean: {sims_arr.mean():.3f}  Std: {sims_arr.std():.3f}")

    print(f"\n  Similarity-Score correlation: {correlation:.3f}")
    print(f"    (Should be negative: higher sim -> lower novelty score)")
    print(f"    {'CORRECT' if correlation < -0.3 else 'WEAK' if correlation < 0 else 'WRONG'} "
          f"({'strong' if abs(correlation) > 0.5 else 'moderate' if abs(correlation) > 0.3 else 'weak'})")

    return correlation


def main():
    print("=" * 80)
    print("CORPUS VALIDATION: Testing Combined Classifier on Real Data")
    print("=" * 80)

    # Setup
    print("\nLoading...")
    t0 = time.time()
    embedder = Embedder()
    index = load_index()
    corpus = load_papers()

    if index is None:
        print("ERROR: No FAISS index. Run 'python scripts/build_index.py' first.")
        sys.exit(1)

    sim_module.init(embedder, index, corpus)
    sim_engine = SimilarityEngine()

    print(f"Loaded {len(corpus)} papers in {time.time()-t0:.1f}s")

    print("\nComputing corpus statistics...")
    t0 = time.time()
    init_stats(corpus, index, embedder)
    print(f"Done in {time.time()-t0:.1f}s")

    # Run all tests
    gap_rate_exact, mean_score_exact = test_exact_corpus_papers(sim_engine, corpus)
    gap_rate_mod, mean_score_mod = test_modified_corpus_papers(sim_engine, corpus)
    crosslink_rate = test_paper_mashups(sim_engine, corpus)
    ood_rate = test_out_of_domain(sim_engine, corpus)
    correlation = test_score_consistency(sim_engine, corpus)

    # Final report
    print(f"\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}")

    results = [
        ("Exact corpus -> Direct Gap Fill", gap_rate_exact, "> 50%", gap_rate_exact > 50),
        ("Exact corpus -> mean score < 50", mean_score_exact, "< 50", mean_score_exact < 50),
        ("Modified corpus -> Direct Gap Fill", gap_rate_mod, "> 30%", gap_rate_mod > 30),
        ("Mashups -> Cross-Link Novelty", crosslink_rate, "> 30%", crosslink_rate > 30),
        ("Out-of-domain -> Out-of-Domain label", ood_rate, "> 30%", ood_rate > 30),
        ("Sim-Score correlation negative", correlation, "< -0.3", correlation < -0.3),
    ]

    passed = 0
    for name, value, target, ok in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        if isinstance(value, float):
            print(f"  [{status}] {name}: {value:.1f} (target: {target})")
        else:
            print(f"  [{status}] {name}: {value} (target: {target})")

    print(f"\n  Result: {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
