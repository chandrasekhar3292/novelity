# app/core/classifier.py

from typing import Dict


def classify_novelty(features: Dict) -> Dict:
    max_sim = features["max_similarity"]
    density = features["density_score"]
    cross = features["crosslink_score"]

    # Thresholds
    VERY_HIGH_SIM = 0.80
    MED_SIM = 0.45
    HIGH_DENSITY = 2.5
    HIGH_CROSSLINK = 0.6

    # 1. Very high similarity ALWAYS means incremental
    if max_sim >= VERY_HIGH_SIM:
        return {
            "label": "Direct Gap Fill",
            "confidence": 0.90
        }

    # 2. Moderate similarity + rare combination
    if MED_SIM <= max_sim < VERY_HIGH_SIM and cross >= HIGH_CROSSLINK:
        return {
            "label": "Cross-Link Novelty",
            "confidence": 0.80
        }

    # 3. Low similarity + low density
    if max_sim < MED_SIM and density < HIGH_DENSITY:
        return {
            "label": "Independent Novelty",
            "confidence": 0.75
        }

    # 4. Very low similarity
    if max_sim < 0.2:
        return {
            "label": "Out-of-Domain",
            "confidence": 0.60
        }

    return {
        "label": "Uncertain Novelty",
        "confidence": 0.50
    }
