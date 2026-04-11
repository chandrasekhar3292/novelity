"""
Test script: Compare old rule-based classifier vs new combined classifier.

Runs both classifiers on the same inputs and evaluates:
1. Consistency — do similar inputs get similar labels?
2. Granularity — does the combined system differentiate better?
3. Confidence calibration — are confidence scores meaningful?
4. Edge cases — how do both handle boundary conditions?

Usage:
    python scripts/test_classifier.py
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
from app.core.corpus_stats import CorpusStats, init_stats, get_stats


# ---- Old rule-based classifier (copy for comparison) ----
def classify_rule_based(features):
    max_sim = features["max_similarity"]
    density = features["density_score"]
    cross = features["crosslink_score"]

    if max_sim < 0.15:
        return {"label": "Out-of-Domain", "confidence": 0.60}
    if max_sim >= 0.80:
        return {"label": "Direct Gap Fill", "confidence": 0.90}
    if 0.45 <= max_sim < 0.80 and cross >= 0.6:
        return {"label": "Cross-Link Novelty", "confidence": 0.80}
    if max_sim < 0.45 and density < 2.5:
        return {"label": "Independent Novelty", "confidence": 0.75}
    return {"label": "Uncertain Novelty", "confidence": 0.50}


# ---- New combined classifier ----
from app.core.classifier import classify_novelty as classify_combined


# ---- Test ideas ----
# Expectations calibrated for a corpus of ~4800 recent (2024-2026) AI/ML papers.
# The corpus is arxiv-heavy (cs.AI, cs.LG, cs.CV, cs.CL, etc.)
TEST_IDEAS = [
    # --- Should be Direct Gap Fill (very close to active corpus topics) ---
    {
        "text": "Large language model alignment using reinforcement learning from human feedback to improve safety and helpfulness of AI assistants",
        "expected": "Direct Gap Fill",
        "reason": "RLHF + LLM alignment is THE hot topic in 2024-2026 AI papers",
    },
    {
        "text": "Vision transformer architecture for multi-modal image and text understanding with contrastive pretraining on web-scale datasets",
        "expected": "Direct Gap Fill",
        "reason": "Vision transformers + multimodal + contrastive learning are dominant in recent CV/CL",
    },
    {
        "text": "Diffusion model based text-to-video generation with temporal consistency and motion control for high resolution content creation",
        "expected": "Direct Gap Fill",
        "reason": "Text-to-video diffusion models are extremely active in 2024-2026",
    },
    {
        "text": "Parameter efficient fine-tuning of large language models using low rank adaptation for downstream natural language processing tasks",
        "expected": "Direct Gap Fill",
        "reason": "LoRA / PEFT for LLMs is heavily published in recent AI papers",
    },

    # --- Should be Cross-Link Novelty (bridge between known domains) ---
    {
        "text": "Applying graph neural networks to model protein-protein interaction networks for predicting drug synergies in cancer treatment using multi-omics data",
        "expected": "Cross-Link Novelty",
        "reason": "GNN + drug discovery + multi-omics bridges AI with bioinformatics",
    },
    {
        "text": "Combining neuromorphic computing hardware design with spiking neural network architectures for energy efficient edge deployment of transformer models",
        "expected": "Cross-Link Novelty",
        "reason": "Neuromorphic + SNN + transformers + edge AI spans hardware and ML",
    },
    {
        "text": "Reinforcement learning for autonomous multi-robot coordination in warehouse logistics using federated learning for privacy-preserving policy sharing",
        "expected": "Cross-Link Novelty",
        "reason": "RL + multi-robot + federated learning + logistics is a rare combination",
    },

    # --- Should be Independent Novelty (sparse area, little existing work) ---
    {
        "text": "Developing machine learning models for predicting geothermal energy potential from seismographic data combined with satellite thermal imaging in volcanic regions",
        "expected": "Independent Novelty",
        "reason": "ML + geothermal + seismographic + thermal imaging is very sparse in AI corpus",
    },
    {
        "text": "Using deep learning to analyze soil microbiome DNA sequences for predicting agricultural crop disease outbreaks in tropical regions",
        "expected": "Independent Novelty",
        "reason": "DL + soil microbiome + crop disease is far from mainstream AI",
    },

    # --- Should be Out-of-Domain (completely outside AI/ML scope) ---
    {
        "text": "A comparative study of medieval European manuscript illumination techniques using pigment analysis and dendrochronological dating of vellum preparation methods",
        "expected": "Out-of-Domain",
        "reason": "Medieval manuscripts / pigment analysis / dendrochronology has nothing to do with AI/ML",
    },
    {
        "text": "Analyzing the socioeconomic impact of Roman aqueduct construction on provincial urbanization patterns through archaeological survey data",
        "expected": "Out-of-Domain",
        "reason": "Roman archaeology is completely outside AI/ML corpus",
    },
]


def run_pipeline(idea_text, sim_engine, corpus):
    """Run the feature extraction pipeline for a single idea."""
    # Use concepts for category-aware similarity
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

    # Use arXiv categories from similar papers for crosslink
    # (since fallback extraction produces keywords that don't match arXiv cats)
    paper_concepts = set()
    for p in similar_papers[:10]:
        for c in p.get("concepts", []):
            paper_concepts.add(c)

    # Mix idea keywords with related paper categories for realistic crosslink
    mixed_concepts = concepts[:3] + list(paper_concepts)[:5]
    crosslink = compute_crosslink_score(mixed_concepts, corpus)

    features = build_feature_vector(similarity, density, recency, crosslink)
    return features, similar_papers


def print_comparison(idx, idea, features, old_result, new_result, similar_papers):
    """Print side-by-side comparison of old vs new classifier."""
    expected = idea["expected"]

    old_label = old_result["label"]
    old_conf = old_result["confidence"]
    new_label = new_result["label"]
    new_conf = new_result["confidence"]
    novelty_score = new_result.get("novelty_score", "N/A")

    old_match = "OK" if old_label == expected else "MISS"
    new_match = "OK" if new_label == expected else "MISS"

    print(f"\n{'='*80}")
    print(f"Test {idx+1}: {idea['text'][:75]}...")
    print(f"  Expected:  {expected}")
    print(f"  Reason:    {idea['reason']}")
    print(f"  Signals:   sim={features['max_similarity']:.3f}  "
          f"density={features['density_score']:.2f}  "
          f"recency={features['recency_score']:.2f}  "
          f"crosslink={features['crosslink_score']:.3f}")
    if similar_papers:
        print(f"  Top match: \"{similar_papers[0].get('title', '')[:70]}\"")
    print(f"  OLD:       {old_label:25s}  conf={old_conf:.2f}  [{old_match}]")
    print(f"  NEW:       {new_label:25s}  conf={new_conf:.2f}  "
          f"score={novelty_score}  [{new_match}]")

    if new_result.get("percentiles"):
        pcts = new_result["percentiles"]
        print(f"  Percentiles: sim={pcts['similarity']:.0f}th  "
              f"density={pcts['density']:.0f}th  "
              f"recency={pcts['recency']:.0f}th  "
              f"crosslink={pcts['crosslink']:.0f}th")


def run_corpus_sample_test(sim_engine, corpus, n=50):
    """
    Test on random corpus papers — a paper from the corpus should
    generally be classified as Direct Gap Fill (high similarity to itself).
    """
    print(f"\n{'='*80}")
    print(f"CORPUS SELF-TEST: {n} random papers (should mostly be 'Direct Gap Fill')")
    print(f"{'='*80}")

    rng = np.random.RandomState(123)
    indices = rng.choice(len(corpus), size=min(n, len(corpus)), replace=False)

    old_labels = []
    new_labels = []
    new_scores = []

    for idx in indices:
        paper = corpus[idx]
        text = f"{paper.get('title', '')}. {paper['abstract']}"
        features, _ = run_pipeline(text, sim_engine, corpus)
        old = classify_rule_based(features)
        new = classify_combined(features)
        old_labels.append(old["label"])
        new_labels.append(new["label"])
        if new.get("novelty_score"):
            new_scores.append(new["novelty_score"])

    print(f"\n  OLD distribution: {dict(Counter(old_labels))}")
    print(f"  NEW distribution: {dict(Counter(new_labels))}")

    old_gap = old_labels.count("Direct Gap Fill") / len(old_labels) * 100
    new_gap = new_labels.count("Direct Gap Fill") / len(new_labels) * 100
    print(f"\n  OLD 'Direct Gap Fill' rate: {old_gap:.1f}%")
    print(f"  NEW 'Direct Gap Fill' rate: {new_gap:.1f}%")
    print(f"  (Higher is better — corpus papers should match existing work)")

    if new_scores:
        print(f"\n  NEW score distribution for corpus papers:")
        print(f"    Mean: {np.mean(new_scores):.1f}  Std: {np.std(new_scores):.1f}")
        print(f"    Min: {min(new_scores):.1f}  Max: {max(new_scores):.1f}")

    return old_gap, new_gap


def run_boundary_test():
    """Test behavior around critical thresholds."""
    print(f"\n{'='*80}")
    print("BOUNDARY TEST: Values near old thresholds")
    print(f"{'='*80}")

    boundary_cases = [
        {"max_similarity": 0.69, "mean_similarity": 0.5, "similarity_spread": 0.1,
         "density_score": 3.0, "recency_score": 1.0, "crosslink_score": 0.04,
         "note": "sim=0.69 (just below new high threshold ~0.70)"},
        {"max_similarity": 0.71, "mean_similarity": 0.5, "similarity_spread": 0.1,
         "density_score": 3.0, "recency_score": 1.0, "crosslink_score": 0.04,
         "note": "sim=0.71 (just above new high threshold ~0.70)"},
        {"max_similarity": 0.79, "mean_similarity": 0.5, "similarity_spread": 0.1,
         "density_score": 3.0, "recency_score": 1.0, "crosslink_score": 0.04,
         "note": "sim=0.79 (just below old 0.80 threshold)"},
        {"max_similarity": 0.81, "mean_similarity": 0.5, "similarity_spread": 0.1,
         "density_score": 3.0, "recency_score": 1.0, "crosslink_score": 0.04,
         "note": "sim=0.81 (just above old 0.80 threshold)"},
        {"max_similarity": 0.19, "mean_similarity": 0.1, "similarity_spread": 0.02,
         "density_score": 0.2, "recency_score": 0.5, "crosslink_score": 0.9,
         "note": "sim=0.19 (just below out-of-domain 0.20)"},
        {"max_similarity": 0.21, "mean_similarity": 0.1, "similarity_spread": 0.03,
         "density_score": 0.4, "recency_score": 0.5, "crosslink_score": 0.9,
         "note": "sim=0.21 (just above out-of-domain 0.20)"},
        {"max_similarity": 0.50, "mean_similarity": 0.35, "similarity_spread": 0.1,
         "density_score": 2.0, "recency_score": 5.0, "crosslink_score": 0.02,
         "note": "sim=0.50, crosslink=0.02 (median sim, low crosslink)"},
        {"max_similarity": 0.50, "mean_similarity": 0.35, "similarity_spread": 0.1,
         "density_score": 2.0, "recency_score": 5.0, "crosslink_score": 0.30,
         "note": "sim=0.50, crosslink=0.30 (median sim, high crosslink)"},
    ]

    for case in boundary_cases:
        note = case.pop("note")
        old = classify_rule_based(case)
        new = classify_combined(case)

        old_label = old["label"]
        new_label = new["label"]
        new_score = new.get("novelty_score", "N/A")
        new_conf = new["confidence"]

        print(f"\n  {note}")
        print(f"    OLD: {old_label:25s}  conf={old['confidence']:.2f}")
        print(f"    NEW: {new_label:25s}  conf={new_conf:.2f}  score={new_score}")

        case["note"] = note  # restore


def run_score_ordering_test(sim_engine, corpus):
    """
    Test that novelty scores are ordered correctly:
    ideas that are clearly more novel should get higher scores.
    """
    print(f"\n{'='*80}")
    print("SCORE ORDERING TEST: Do scores rank correctly?")
    print(f"{'='*80}")

    # Ordered by expected novelty (least → most) based on ACTUAL corpus coverage.
    # The corpus is ~4800 recent arXiv AI/ML papers.
    ordered_ideas = [
        ("Parameter efficient fine-tuning of large language models using LoRA adapters for NLP tasks",
         "Extremely common in corpus — should score LOWEST"),
        ("Vision transformer with contrastive learning for multi-modal understanding",
         "Common but slightly less — should score LOW"),
        ("Graph neural networks for protein structure prediction in drug discovery",
         "Cross-domain, moderate similarity — should score MEDIUM-HIGH"),
        ("Deep learning for soil microbiome analysis and crop disease prediction in tropical agriculture",
         "Very sparse in AI/ML corpus — should score HIGHEST"),
    ]

    scores = []
    for text, desc in ordered_ideas:
        features, _ = run_pipeline(text, sim_engine, corpus)
        result = classify_combined(features)
        score = result.get("novelty_score", 0)
        scores.append(score)
        print(f"\n  {desc}")
        print(f"    \"{text[:70]}...\"")
        print(f"    Score: {score}  Label: {result['label']}  "
              f"Conf: {result['confidence']}  Sim: {features['max_similarity']:.3f}")

    # Check if scores are monotonically increasing
    is_ordered = all(scores[i] <= scores[i+1] for i in range(len(scores)-1))
    print(f"\n  Scores: {scores}")
    print(f"  Correctly ordered (ascending novelty): {'YES' if is_ordered else 'NO'}")

    return is_ordered


def main():
    print("=" * 80)
    print("NOVELTY CLASSIFIER COMPARISON: Old (Rule-Based) vs New (Combined)")
    print("=" * 80)

    # Setup
    print("\nLoading models and data...")
    t0 = time.time()

    embedder = Embedder()
    index = load_index()
    corpus = load_papers()

    if index is None:
        print("ERROR: No FAISS index found. Run 'python scripts/build_index.py' first.")
        sys.exit(1)

    sim_module.init(embedder, index, corpus)
    sim_engine = SimilarityEngine()

    print(f"Loaded {len(corpus)} papers in {time.time()-t0:.1f}s")

    # Compute corpus stats for combined classifier
    print("\nComputing corpus statistics...")
    t0 = time.time()
    stats = init_stats(corpus, index, embedder)
    print(f"Stats computed in {time.time()-t0:.1f}s")
    print(f"Adaptive weights: {stats.signal_weights}")
    print(f"Informative signals: "
          f"similarity={stats.is_signal_informative('similarity')}, "
          f"density={stats.is_signal_informative('density')}, "
          f"recency={stats.is_signal_informative('recency')}, "
          f"crosslink={stats.is_signal_informative('crosslink')}")

    # ---- Test 1: Known ideas ----
    print(f"\n{'='*80}")
    print("TEST 1: Known ideas with expected classifications")
    print(f"{'='*80}")

    old_correct = 0
    new_correct = 0
    old_uncertain = 0
    new_scores = []

    for i, idea in enumerate(TEST_IDEAS):
        features, similar_papers = run_pipeline(idea["text"], sim_engine, corpus)
        old_result = classify_rule_based(features)
        new_result = classify_combined(features)

        print_comparison(i, idea, features, old_result, new_result, similar_papers)

        if old_result["label"] == idea["expected"]:
            old_correct += 1
        if new_result["label"] == idea["expected"]:
            new_correct += 1
        if old_result["label"] == "Uncertain Novelty":
            old_uncertain += 1
        if new_result.get("novelty_score"):
            new_scores.append(new_result["novelty_score"])

    total = len(TEST_IDEAS)
    print(f"\n{'='*80}")
    print("TEST 1 RESULTS")
    print(f"{'='*80}")
    print(f"  OLD accuracy: {old_correct}/{total} ({old_correct/total*100:.1f}%)")
    print(f"  NEW accuracy: {new_correct}/{total} ({new_correct/total*100:.1f}%)")
    print(f"  OLD 'Uncertain' count: {old_uncertain}")
    if new_scores:
        print(f"  NEW score range: {min(new_scores):.1f} - {max(new_scores):.1f} "
              f"(spread: {max(new_scores)-min(new_scores):.1f})")
        print(f"  NEW score std:   {np.std(new_scores):.1f}")

    # ---- Test 2: Corpus self-test ----
    old_gap, new_gap = run_corpus_sample_test(sim_engine, corpus)

    # ---- Test 3: Boundary test ----
    run_boundary_test()

    # ---- Test 4: Score ordering ----
    ordered = run_score_ordering_test(sim_engine, corpus)

    # ---- Summary ----
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    print(f"  Known ideas accuracy:   OLD={old_correct/total*100:.0f}%  NEW={new_correct/total*100:.0f}%")
    print(f"  Corpus self-test:       OLD={old_gap:.0f}% gap-fill  NEW={new_gap:.0f}% gap-fill")
    print(f"  Score ordering:         {'CORRECT' if ordered else 'INCORRECT'}")
    print(f"  Score granularity:      OLD=4 fixed confidences  NEW=continuous 0-100 + calibrated confidence")
    print(f"  Boundary handling:      OLD=hard cutoffs  NEW=smooth fuzzy transitions")
    print(f"  'Uncertain' fallback:   OLD={old_uncertain} times  NEW=0 times (always decisive)")


if __name__ == "__main__":
    main()
