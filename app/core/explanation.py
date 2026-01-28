# app/core/explanation.py

from typing import Dict, List, Optional

from openai import OpenAI

client = OpenAI()


def generate_rule_based_explanation(
    idea_domains: List[str],
    features: Dict,
    classification: Dict
) -> str:
    """
    Deterministic explanation generator.
    Always available, zero hallucination.
    """

    parts = []

    label = classification["label"]

    # Similarity
    parts.append(
        f"The idea shows a maximum semantic similarity of "
        f"{features['max_similarity']:.2f} with existing literature."
    )

    # Density
    parts.append(
        f"The publication density in the relevant area is "
        f"{features['density_score']:.2f}, indicating "
        f"{'a crowded' if features['density_score'] > 3 else 'a relatively sparse'} research space."
    )

    # Recency
    parts.append(
        f"The recency trend score is {features['recency_score']:.2f}, "
        f"suggesting {'growing' if features['recency_score'] > 1 else 'stable or declining'} activity."
    )

    # Cross-link
    parts.append(
        f"The cross-link novelty score is {features['crosslink_score']:.2f}, "
        f"reflecting the rarity of the concept combinations."
    )

    # Final interpretation
    parts.append(
        f"Based on these signals, the idea is classified as "
        f"'{label}'."
    )

    return " ".join(parts)


def generate_llm_explanation(
    idea_text: str,
    idea_domains: List[str],
    features: Dict,
    classification: Dict
) -> str:
    """
    Optional OpenAI-based explanation.
    Uses signals as ground truth, not as suggestions.
    """

    prompt = f"""
You are explaining a research novelty analysis result.

Rules:
- Do NOT exaggerate novelty
- Do NOT introduce new facts
- Only interpret the provided signals

Idea:
{idea_text}

Domains:
{", ".join(idea_domains)}

Signals:
- Max similarity: {features['max_similarity']}
- Mean similarity: {features['mean_similarity']}
- Density score: {features['density_score']}
- Recency score: {features['recency_score']}
- Cross-link score: {features['crosslink_score']}

Classification:
{classification['label']}

Write a concise, neutral explanation (3–4 sentences).
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You generate factual research explanations."},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content.strip()
