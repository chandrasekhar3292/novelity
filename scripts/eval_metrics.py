"""
Evaluation harness: precision / recall / F1 / accuracy for the novelty classifier.

Test set is built programmatically:
  - Direct Gap Fill   : random corpus papers, abstracts submitted verbatim
                        (self-retrieval should produce a top-1 hit)
  - Out-of-Domain     : hand-crafted non-AI/ML topics
  - Cross-Link Novelty: hand-crafted ideas bridging two corpus topics
  - Independent Novelty: hand-crafted sparse-domain ML ideas

Runs the full pipeline directly via imports (no HTTP), then computes metrics
with sklearn. Prints per-class precision/recall/F1, macro F1, accuracy, and
the confusion matrix.

Usage:
    python scripts/eval_metrics.py [--n-known 50]
"""

import os
import sys
import argparse
from collections import Counter

import numpy as np
from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    confusion_matrix,
    classification_report,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Avoid hanging on huggingface.co HEAD checks
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.corpus.embedder import Embedder
from app.corpus.builder import load_index
from app.corpus.loader import load_papers
from app.core import similarity as sim_module
from app.core.similarity import SimilarityEngine
from app.core.density import compute_density
from app.corpus.recency import compute_recency
from app.core.crosslink import compute_crosslink_score
from app.core.features import build_feature_vector
from app.core.classifier import classify_novelty
from app.core.corpus_stats import init_stats
from app.core.idea import _fallback_extraction


LABELS = ["Direct Gap Fill", "Cross-Link Novelty", "Independent Novelty", "Out-of-Domain"]


# ---------- Hand-crafted test ideas ----------

OUT_OF_DOMAIN = [
    "A comparative study of medieval European manuscript illumination techniques using pigment analysis and dendrochronological dating of vellum preparation",
    "Analyzing the socioeconomic impact of Roman aqueduct construction on provincial urbanization patterns through archaeological survey data",
    "Phylogenetic analysis of bronze-age pottery decoration motifs across Anatolian trade networks using stratigraphic context",
    "Liturgical music notation reform in 12th century Cistercian monasteries and its influence on Gregorian chant evolution",
    "Stratigraphic interpretation of Pleistocene mammoth bone deposits in Siberian permafrost",
    "Numismatic evidence for currency devaluation in late Republican Rome during the Punic Wars",
    "Iconographic analysis of Mughal miniature painting traditions in 17th century Rajasthan court workshops",
    "Sedimentological study of estuarine tidal flats in the Bay of Fundy under spring-neap cycles",
    "Crispr knock-in protocol for cardiac myocyte regeneration in zebrafish embryos using fluorescent reporters",
    "Petrographic analysis of granite intrusions in the Sierra Nevada batholith and their cooling history",
    "Folklore motifs in 19th century Norwegian peasant tales collected by Asbjornsen and Moe",
    "Game-theoretic analysis of bidding strategies in 18th-century Dutch tulip markets",
    "Hydrothermal alteration mineralogy of porphyry copper deposits in the Andes",
    "Comparative grammar of Proto-Indo-European laryngeal consonants in Hittite and Sanskrit",
    "Ethnographic study of reindeer herding kinship networks among the Sami of northern Scandinavia",
    "Chemical synthesis of novel organocatalysts for asymmetric Diels-Alder reactions in flow chemistry",
    "Fluid inclusion thermometry in epithermal gold-silver vein systems",
    "Renaissance perspective drawing techniques in the workshop of Filippo Brunelleschi",
    "Pollen-based reconstruction of Holocene vegetation in Mediterranean basins",
    "Neolithic megalith construction logistics on the Salisbury plain",
]

CROSS_LINK = [
    "A spiking neural network backbone for an autonomous LLM agent's long-term episodic memory store with biologically inspired forgetting",
    "Apply Hebbian-oscillatory co-learning principles to fine-tune large language models on continuous user feedback streams",
    "Conformal prediction guarantees for LLM-based regulatory rule extraction in compliance-critical domains",
    "Use neuromorphic accelerators to run on-device generative video diffusion models for edge deployment",
    "Combine graph neural networks with retrieval-augmented generation for protein-protein interaction question answering",
    "Apply diffusion models to crystal structure prediction guided by physics-informed neural network priors",
    "Federated reinforcement learning for multi-robot warehouse coordination with privacy-preserving policy distillation",
    "Use vision transformer features as the perception module of a robotic manipulation policy trained with offline RL",
    "Causal inference with Gaussian processes for evaluating LLM-generated treatment recommendations under selection bias",
    "Adapt speculative decoding techniques to accelerate diffusion model sampling for real-time text-to-image generation",
    "Equivariant transformer architectures for molecular dynamics simulation of drug-target binding kinetics",
    "Apply curriculum learning from cognitive science to scaling-law analysis of foundation model pretraining",
    "Combine differential privacy with multi-modal contrastive learning for medical imaging foundation models",
    "Use Bayesian optimization to search the hyperparameter space of neuromorphic hardware architectures for SNN inference",
    "Adapt program synthesis techniques to automatically generate prompts for LLM-driven scientific hypothesis generation",
]

INDEPENDENT_NOVELTY = [
    "Machine learning models for predicting geothermal energy potential from seismographic data combined with satellite thermal imaging in volcanic regions",
    "Deep learning for soil microbiome DNA sequences to predict crop disease outbreaks in tropical agriculture",
    "Neural network surrogates for tidal turbine wake modeling in marine renewable energy farms",
    "Computer vision pipeline for monitoring coral bleaching events from autonomous underwater drones in remote reef ecosystems",
    "Reinforcement learning for adaptive precision agriculture irrigation scheduling under climate variability",
    "Transformer models for predicting volcanic eruption precursors from infrasound and gas emission sensor arrays",
    "Self-supervised learning of glacier flow dynamics from satellite radar interferometry time series",
    "Graph neural networks for forecasting wildlife migration corridor disruption from infrastructure development",
    "Diffusion models for synthesizing realistic atmospheric soundings to augment numerical weather prediction training data",
    "Federated learning across rural community health clinics for early detection of arboviral disease outbreaks",
    "Variational autoencoders for de-noising single-photon LIDAR returns in dense forest canopy mapping",
    "Active learning for rare-mineral identification in hyperspectral imagery from asteroid prospecting missions",
    "Neural ODEs for modeling permafrost thaw dynamics under coupled hydrological-thermal forcing",
    "Self-supervised representation learning of seismic facies for sub-salt reservoir characterization",
    "Reinforcement learning policies for autonomous high-altitude balloon station-keeping in stratospheric winds",
]


def get_corpus_examples(corpus, n, seed=42):
    """Sample n papers from corpus and use their abstracts as 'known' ideas."""
    rng = np.random.RandomState(seed)
    indices = rng.choice(len(corpus), size=min(n, len(corpus)), replace=False)
    examples = []
    for i in indices:
        p = corpus[i]
        text = f"{p.get('title', '')}. {p.get('abstract', '')}".strip()
        if len(text) > 50:
            examples.append(text)
    return examples


def run_pipeline(idea_text, sim_engine, corpus):
    """Single-idea pipeline: features -> classification."""
    tags = _fallback_extraction(idea_text)
    concepts = tags.get("concepts", []) + tags.get("domains", [])

    similarity = sim_engine.analyze(idea_text, idea_concepts=concepts)
    similar_papers = [
        corpus[i] for i in similarity["top_indices"]
        if 0 <= i < len(corpus)
    ]

    density = compute_density(similar_papers)
    recency = compute_recency(similar_papers)

    crosslink = compute_crosslink_score(
        concepts, corpus, similar_papers=similar_papers,
    )

    features = build_feature_vector(similarity, density, recency, crosslink)
    classification = classify_novelty(features)
    return classification, features


def evaluate(n_known=50):
    print("Loading models, index, papers...")
    embedder = Embedder()
    index = load_index()
    corpus = load_papers()
    if index is None:
        print("ERROR: no FAISS index. Run scripts/build_index.py first.")
        sys.exit(1)

    sim_module.init(embedder, index, corpus)
    sim_engine = SimilarityEngine()

    print(f"  {len(corpus)} papers, {index.index.ntotal} index vectors")

    print("Computing corpus stats...")
    init_stats(corpus, index, embedder)

    # Build the test set
    print("Building test set...")
    known = get_corpus_examples(corpus, n=n_known)
    test_set = []
    for t in known:
        test_set.append((t, "Direct Gap Fill"))
    for t in CROSS_LINK:
        test_set.append((t, "Cross-Link Novelty"))
    for t in INDEPENDENT_NOVELTY:
        test_set.append((t, "Independent Novelty"))
    for t in OUT_OF_DOMAIN:
        test_set.append((t, "Out-of-Domain"))

    print(f"  Total: {len(test_set)} examples")
    print(f"    known         : {len(known)}")
    print(f"    cross-link    : {len(CROSS_LINK)}")
    print(f"    independent   : {len(INDEPENDENT_NOVELTY)}")
    print(f"    out-of-domain : {len(OUT_OF_DOMAIN)}")

    # Run pipeline
    print("\nRunning pipeline...")
    y_true = []
    y_pred = []
    errors = []  # (text, expected, predicted, features)
    rows = []   # all examples with their features (for analysis)

    for i, (text, expected) in enumerate(test_set):
        classification, features = run_pipeline(text, sim_engine, corpus)
        predicted = classification["label"]
        y_true.append(expected)
        y_pred.append(predicted)
        rows.append({
            "expected": expected,
            "predicted": predicted,
            "max_sim": features["max_similarity"],
            "mean_sim": features["mean_similarity"],
            "spread": features["similarity_spread"],
            "density": features["density_score"],
            "recency": features["recency_score"],
            "crosslink": features["crosslink_score"],
            "sim_pct": classification.get("percentiles", {}).get("similarity"),
            "crosslink_pct": classification.get("percentiles", {}).get("crosslink"),
            "text": text[:80],
        })
        if predicted != expected:
            errors.append((text, expected, predicted, features))
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(test_set)}")

    # Dump per-example for analysis
    import json
    with open("c:/tmp/eval_features.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"\n  features dumped to c:/tmp/eval_features.json")

    # Metrics
    print("\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)

    acc = accuracy_score(y_true, y_pred)
    print(f"Accuracy: {acc:.4f}")

    print("\nPer-class report:")
    print(classification_report(y_true, y_pred, labels=LABELS, digits=4, zero_division=0))

    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, average="macro", zero_division=0
    )
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, average="weighted", zero_division=0
    )

    print(f"Macro    -- precision: {macro_p:.4f}  recall: {macro_r:.4f}  f1: {macro_f1:.4f}")
    print(f"Weighted -- precision: {weighted_p:.4f}  recall: {weighted_r:.4f}  f1: {weighted_f1:.4f}")

    print("\nConfusion matrix (rows = true, cols = predicted):")
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    header = "  " + " ".join(f"{l[:10]:>11s}" for l in LABELS)
    print(header)
    for label, row in zip(LABELS, cm):
        print(f"  {label[:18]:18s} " + " ".join(f"{v:>11d}" for v in row))

    # Error breakdown
    print(f"\nMisclassifications: {len(errors)} / {len(test_set)}")
    by_pair = Counter((e[1], e[2]) for e in errors)
    for (expected, predicted), count in by_pair.most_common():
        print(f"  {expected!r:25s} -> {predicted!r:25s}  ({count})")

    return acc, macro_f1, weighted_f1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-known", type=int, default=50)
    args = p.parse_args()
    evaluate(n_known=args.n_known)


if __name__ == "__main__":
    main()
