# app/core/classifier.py

from typing import Dict


def classify_novelty(features: Dict) -> Dict:
    max_sim = features["max_similarity"]
    density = features["density_score"]
    cross = features["crosslink_score"]

    # Thresholds
    VERY_HIGH_SIM = 0.80
    MED_SIM = 0.45
    OUT_OF_DOMAIN_SIM = 0.15
    HIGH_DENSITY = 2.5
    HIGH_CROSSLINK = 0.6

    # 1. Essentially no match — idea is outside the corpus scope
    if max_sim < OUT_OF_DOMAIN_SIM:
        return {
            "label": "Out-of-Domain",
            "confidence": 0.60,
        }

    # 2. Very high similarity — incremental / gap-filling work
    if max_sim >= VERY_HIGH_SIM:
        return {
            "label": "Direct Gap Fill",
            "confidence": 0.90,
        }

    # 3. Moderate similarity + rare concept combination — bridging gap
    if MED_SIM <= max_sim < VERY_HIGH_SIM and cross >= HIGH_CROSSLINK:
        return {
            "label": "Cross-Link Novelty",
            "confidence": 0.80,
        }

    # 4. Low similarity + sparse area — genuinely new direction
    if max_sim < MED_SIM and density < HIGH_DENSITY:
        return {
            "label": "Independent Novelty",
            "confidence": 0.75,
        }

    return {
        "label": "Uncertain Novelty",
        "confidence": 0.50,
    }
