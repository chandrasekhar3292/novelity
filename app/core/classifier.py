# app/core/classifier.py
"""
Combined novelty classifier:
  1. Adaptive thresholds  — percentiles from corpus, no magic numbers
  2. Fuzzy membership     — smooth transitions instead of hard cutoffs
  3. Weighted composite   — single 0-100 novelty score
  4. Bayesian confidence  — calibrated using corpus distributions

Falls back to rule-based when corpus stats aren't available (lite mode).
"""

import math
from typing import Dict, Optional

from app.core.corpus_stats import CorpusStats, get_stats
from app.core.fuzzy import FuzzyMembership


# ---------------------------------------------------------------------------
# Empirical thresholds — derived from labeled eval (scripts/eval_metrics.py).
#
# OoD floor: corpus self-similarity has mean ~0.66, std ~0.08 (5th percentile
# ~0.55). Non-domain ideas (medieval art, archaeology, etc.) embed at
# 0.19-0.51 against an AI/ML corpus, with median ~0.28. A floor at 0.40
# captures the OoD population while leaving sparse-domain ML ideas
# (geothermal, soil microbiome, etc.) above the line.
#
# Cross-Link cutoffs: cross-domain ideas that combine multiple corpus topics
# embed at 0.46-0.66 (mean ~0.58). Independent novelty ideas in sparse
# domains embed at 0.36-0.57 (mean ~0.49). The two distributions overlap
# in the 0.50-0.57 band, so we use an OR of two complementary signals:
# either the raw similarity is high enough OR the percentile is in the
# moderate (not bottom) range. 0.567 vs 0.568 is irreducible overlap.
# ---------------------------------------------------------------------------
ABS_OUT_OF_DOMAIN_SIM = 0.40
CROSS_LINK_MIN_SIM = 0.56
CROSS_LINK_MIN_PCT = 10.0
ABS_HIGH_SIM = 0.70  # Above this, there's clearly related work


def _novelty_from_similarity(sim_pct: float) -> float:
    """High similarity percentile = low novelty."""
    return max(0.0, min(100.0, 100.0 - sim_pct))


def _novelty_from_density(density_pct: float) -> float:
    """High density percentile = crowded = lower novelty."""
    return max(0.0, min(100.0, 100.0 - density_pct))


def _novelty_from_recency(recency_pct: float) -> float:
    """Moderate activity = neutral. Extremes are ambiguous."""
    deviation = abs(recency_pct - 50.0)
    return max(0.0, min(100.0, 70.0 - deviation * 0.4))


def _novelty_from_crosslink(crosslink_pct: float, informative: bool) -> float:
    """High crosslink = rare combinations = novel.
    If crosslink signal has no variance, return neutral.
    Cap at 85th percentile to prevent outlier domination."""
    if not informative:
        return 50.0
    # Cap: external ideas almost always produce outlier crosslink values
    # because their keywords rarely match corpus arXiv categories.
    # Beyond 85th percentile, diminishing returns.
    capped = min(crosslink_pct, 85.0)
    return max(0.0, min(100.0, capped))


def _novelty_from_spread(spread_pct: float) -> float:
    """High spread = diverse matches = more novel."""
    return max(0.0, min(100.0, spread_pct))


def _compute_composite_score(features: Dict, stats: CorpusStats) -> float:
    """
    Weighted combination of all signal contributions → 0-100 score.
    Uses adaptive weights that account for signal variance.

    When a signal is an extreme outlier (>2 std from corpus mean),
    its weight is redistributed to similarity (the most reliable signal).
    """
    sim_pct = stats.get_percentile_rank("similarity", features["max_similarity"])
    density_pct = stats.get_percentile_rank("density", features["density_score"])
    recency_pct = stats.get_percentile_rank("recency", features["recency_score"])
    crosslink_pct = stats.get_percentile_rank("crosslink", features["crosslink_score"])
    spread_pct = stats.get_percentile_rank("similarity", features["similarity_spread"])

    crosslink_informative = stats.is_signal_informative("crosslink")

    contributions = {
        "similarity": _novelty_from_similarity(sim_pct),
        "density": _novelty_from_density(density_pct),
        "recency": _novelty_from_recency(recency_pct),
        "crosslink": _novelty_from_crosslink(crosslink_pct, crosslink_informative),
        "spread": _novelty_from_spread(spread_pct),
    }

    # Start with adaptive weights
    weights = dict(stats.signal_weights)

    # Outlier dampening: if crosslink is an extreme outlier, reduce its weight
    # and redistribute to similarity
    crosslink_z = abs(features["crosslink_score"] - stats.crosslink_mean) / max(stats.crosslink_std, 1e-6)
    if crosslink_z > 2.0:
        dampening = min(0.8, (crosslink_z - 2.0) * 0.2)  # reduce up to 80%
        redistributed = weights.get("crosslink", 0) * dampening
        weights["crosslink"] = weights.get("crosslink", 0) * (1 - dampening)
        weights["similarity"] = weights.get("similarity", 0) + redistributed

    score = sum(
        contributions[signal] * weights.get(signal, 0.1)
        for signal in contributions
    )

    return round(max(0.0, min(100.0, score)), 1)


def _bayesian_confidence(features: Dict, stats: CorpusStats, label: str) -> float:
    """
    Bayesian-inspired confidence using corpus distributions.
    Only uses signals that have meaningful variance.
    """
    def _z_score(value, mean, std):
        return (value - mean) / max(std, 1e-6)

    z_sim = _z_score(features["max_similarity"], stats.similarity_mean, stats.similarity_std)

    # Only use informative signals
    z_density = 0.0
    z_crosslink = 0.0
    if stats.is_signal_informative("density"):
        z_density = _z_score(features["density_score"], stats.density_mean, stats.density_std)
    if stats.is_signal_informative("crosslink"):
        z_crosslink = _z_score(features["crosslink_score"], stats.crosslink_mean, stats.crosslink_std)

    if label == "Independent Novelty":
        alignment = (-z_sim * 0.5) + (-z_density * 0.2) + (z_crosslink * 0.3)
    elif label == "Cross-Link Novelty":
        alignment = (-abs(z_sim) * 0.2) + (z_crosslink * 0.5) + (-z_density * 0.3)
    elif label == "Direct Gap Fill":
        alignment = (z_sim * 0.6) + (z_density * 0.2) + (-z_crosslink * 0.2)
    elif label == "Out-of-Domain":
        alignment = (-z_sim * 0.8) + (-z_density * 0.2)
    else:
        alignment = 0.0

    raw_confidence = 1.0 / (1.0 + math.exp(-alignment))
    confidence = 0.40 + raw_confidence * 0.55

    return round(confidence, 2)


def _classify_combined(features: Dict, stats: CorpusStats) -> str:
    """
    Hybrid classification driven by max_sim with corpus-percentile context.

    Decision tree (empirically derived from labeled eval):
      1. max_sim < 0.40                       -> Out-of-Domain
      2. sim_pct >= 50                        -> Direct Gap Fill
      3. max_sim >= 0.55 OR strong crosslink  -> Cross-Link Novelty
      4. otherwise                            -> Independent Novelty

    The crosslink fuzzy signal is only consulted when corpus_stats reports
    it as informative — in fallback (no-LLM) mode the crosslink score is
    degenerate because idea concepts get mixed with neighbor categories.
    """
    max_sim = features["max_similarity"]
    composite = _compute_composite_score(features, stats)

    # --- 1. Out-of-Domain: embedding floor ---
    if max_sim < ABS_OUT_OF_DOMAIN_SIM:
        return "Out-of-Domain", composite

    sim_pct = stats.get_percentile_rank("similarity", max_sim)

    # --- 2. Direct Gap Fill: above-median corpus similarity ---
    if sim_pct >= 50:
        return "Direct Gap Fill", composite

    # --- 3. Cross-Link vs 4. Independent ---
    # Cross-Link: idea touches multiple corpus topics → high max_sim OR
    # moderate-but-not-bottom percentile rank. Independent: sparse-domain
    # → low max_sim AND bottom-percentile rank.
    #
    # We do NOT use the crosslink fuzzy signal here. In fallback (no-LLM)
    # mode the crosslink score is degenerate because the upstream pipeline
    # mixes idea concepts with neighbor categories, producing 97th-pct
    # values for every input. Trusting it collapses Independent into
    # Cross-Link. The full-LLM pipeline can re-introduce it if needed.
    if max_sim >= CROSS_LINK_MIN_SIM or sim_pct >= CROSS_LINK_MIN_PCT:
        return "Cross-Link Novelty", composite

    return "Independent Novelty", composite


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Verdict mapping for the four labels.
# Direct Gap Fill   = closely related work exists, but the idea may still
#                     fill an unaddressed gap — worth investigating
# Cross-Link / Independent = novel
# Out-of-Domain     = no comparable work in the corpus → not assessable
_VERDICT_MAP = {
    "Direct Gap Fill": (
        "gap_to_investigate",
        "Investigate — closely related work exists, but may leave a gap to fill",
    ),
    "Cross-Link Novelty": (
        "novel",
        "Novel — combines existing topics in a new way",
    ),
    "Independent Novelty": (
        "novel",
        "Novel — explores sparse / unexplored territory",
    ),
    "Out-of-Domain": (
        "out_of_scope",
        "Out of scope — no comparable work in this corpus",
    ),
    "Uncertain Novelty": ("uncertain", "Uncertain — signals are conflicting"),
}


def classify_novelty(features: Dict) -> Dict:
    """
    Combined classifier entry point.
    Uses adaptive + fuzzy + composite + Bayesian when corpus stats exist.
    Falls back to simple rule-based when they don't.
    """
    stats = get_stats()

    if stats is None or not stats.ready:
        result = _classify_rule_based(features)
        verdict, verdict_text = _VERDICT_MAP.get(
            result["label"], ("uncertain", "Uncertain")
        )
        result["verdict"] = verdict
        result["verdict_text"] = verdict_text
        return result

    label, composite_score = _classify_combined(features, stats)
    confidence = _bayesian_confidence(features, stats, label)
    verdict, verdict_text = _VERDICT_MAP.get(label, ("uncertain", "Uncertain"))

    percentiles = {
        "similarity": round(stats.get_percentile_rank("similarity", features["max_similarity"]), 1),
        "density": round(stats.get_percentile_rank("density", features["density_score"]), 1),
        "recency": round(stats.get_percentile_rank("recency", features["recency_score"]), 1),
        "crosslink": round(stats.get_percentile_rank("crosslink", features["crosslink_score"]), 1),
    }

    # Fuzzy memberships for API/debug
    fuzzy = FuzzyMembership(stats)
    memberships = fuzzy.compute_all(features)

    return {
        "label": label,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "confidence": confidence,
        "novelty_score": composite_score,
        "percentiles": percentiles,
        "fuzzy_memberships": memberships,
        "informative_signals": {
            "similarity": stats.is_signal_informative("similarity"),
            "density": stats.is_signal_informative("density"),
            "recency": stats.is_signal_informative("recency"),
            "crosslink": stats.is_signal_informative("crosslink"),
        },
    }


def _classify_rule_based(features: Dict) -> Dict:
    """Fallback: original rule-based classifier for lite mode."""
    max_sim = features["max_similarity"]
    density = features["density_score"]
    cross = features["crosslink_score"]

    if max_sim < 0.15:
        label, conf = "Out-of-Domain", 0.60
    elif max_sim >= 0.80:
        label, conf = "Direct Gap Fill", 0.90
    elif 0.45 <= max_sim < 0.80 and cross >= 0.6:
        label, conf = "Cross-Link Novelty", 0.80
    elif max_sim < 0.45 and density < 2.5:
        label, conf = "Independent Novelty", 0.75
    else:
        label, conf = "Uncertain Novelty", 0.50

    return {
        "label": label,
        "confidence": conf,
    }
