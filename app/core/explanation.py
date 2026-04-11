# app/core/explanation.py

from typing import Dict, List, Optional

from openai import OpenAI

client = OpenAI()


# ---------------------------------------------------------------------------
# Narrative explanation — plain English, no scores or percentiles
# ---------------------------------------------------------------------------

# Map arXiv category codes to human-readable names. Covers the categories
# present in the current corpus; unknown codes are passed through unchanged.
_ARXIV_CATEGORY_MAP = {
    "cs.ai": "artificial intelligence",
    "cs.lg": "machine learning",
    "cs.cv": "computer vision",
    "cs.cl": "natural language processing",
    "cs.ne": "neural networks",
    "cs.ro": "robotics",
    "cs.ir": "information retrieval",
    "cs.hc": "human-computer interaction",
    "cs.si": "social networks",
    "cs.se": "software engineering",
    "cs.cr": "security",
    "cs.dc": "distributed computing",
    "cs.db": "databases",
    "cs.gr": "computer graphics",
    "cs.mm": "multimedia",
    "cs.sd": "audio processing",
    "cs.ar": "hardware architecture",
    "cs.cy": "computers and society",
    "cs.it": "information theory",
    "cs.ds": "data structures and algorithms",
    "cs.cc": "computational complexity",
    "cs.ma": "multi-agent systems",
    "cs.gt": "game theory",
    "cs.lo": "logic",
    "cs.pl": "programming languages",
    "stat.ml": "statistical machine learning",
    "stat.me": "statistical methodology",
    "stat.ap": "applied statistics",
    "q-bio.bm": "computational biology",
    "q-bio.nc": "neuroscience",
    "q-bio.qm": "quantitative biology methods",
    "eess.iv": "image and video processing",
    "eess.sp": "signal processing",
    "eess.as": "audio and speech processing",
    "eess.sy": "control systems",
    "math.oc": "optimization",
    "math.st": "statistics theory",
    "physics.comp-ph": "computational physics",
}


def _humanize_concept(c: str) -> str:
    """Translate arXiv category codes to plain English; pass others through."""
    if not c:
        return c
    key = c.strip().lower()
    return _ARXIV_CATEGORY_MAP.get(key, c.strip())


def _format_topics(concepts: List[str], limit: int = 3) -> str:
    if not concepts:
        return ""
    seen = []
    for raw in concepts:
        c = _humanize_concept(raw)
        if c and c not in seen:
            seen.append(c)
        if len(seen) >= limit:
            break
    if len(seen) == 1:
        return seen[0]
    if len(seen) == 2:
        return f"{seen[0]} and {seen[1]}"
    return f"{', '.join(seen[:-1])}, and {seen[-1]}"


def generate_narrative_explanation(
    idea_text: str,
    top_paper: Optional[Dict],
    features: Dict,
    classification: Dict,
    idea_concepts: Optional[List[str]] = None,
) -> str:
    """
    Plain-English explanation of the verdict. Mentions the closest paper by
    title and the topic mix where relevant. Never includes percentiles or
    raw signal values — those are shown in the gauges. Density / recency
    commentary only fires when the corpus stats flag those signals as
    informative.
    """
    label = classification.get("label", "")
    verdict = classification.get("verdict")
    informative = classification.get("informative_signals") or {}
    is_duplicate = classification.get("is_duplicate", False)

    top_title = (top_paper or {}).get("title") if top_paper else None
    top_concepts = (top_paper or {}).get("concepts") or []

    # Prefer the LLM-extracted idea concepts (real English phrases like
    # "Vision-language models") when available. Fall back to the neighbor
    # paper's arXiv categories (humanized) when the idea concepts look
    # like noisy keyword bigrams from the fallback extractor.
    def _looks_like_llm(concepts):
        """LLM concepts are capitalized noun phrases; fallback bigrams are
        lowercase token pairs like 'method parameter-efficient'."""
        if not concepts:
            return False
        capitalized = sum(
            1 for c in concepts[:6] if c and c[0:1].isupper()
        )
        return capitalized >= 2

    if idea_concepts and _looks_like_llm(idea_concepts):
        topic_phrase = _format_topics(idea_concepts)
    else:
        non_arxiv = [c for c in top_concepts if "." not in c]
        topic_phrase = _format_topics(non_arxiv or top_concepts)

    parts: List[str] = []

    # ----- Core verdict sentence -----
    if is_duplicate and top_title:
        parts.append(
            f"This idea closely matches \u2018{top_title}\u2019 — the work already exists, "
            f"so it is not a novel contribution."
        )
    elif label == "Direct Gap Fill" and top_title:
        parts.append(
            f"This direction is closely related to \u2018{top_title}\u2019 and the surrounding area is "
            f"already well covered. There may still be an unaddressed gap worth investigating, but "
            f"the core problem has been studied."
        )
    elif label == "Cross-Link Novelty":
        if topic_phrase:
            parts.append(
                f"Individual aspects of this idea exist in work on {topic_phrase}, but the particular "
                f"combination is uncommon. Cross-domain bridges like this often surface genuinely new "
                f"research directions that neither parent area has explored alone."
            )
        else:
            parts.append(
                "Individual aspects of this idea exist in prior work, but the particular combination "
                "is uncommon. Cross-domain bridges like this often surface genuinely new research "
                "directions."
            )
    elif label == "Independent Novelty":
        if top_title:
            parts.append(
                f"This idea explores territory that has barely been studied. The closest related "
                f"paper, \u2018{top_title}\u2019, is only loosely connected, and the broader area appears "
                f"to be sparse — so the idea is likely novel."
            )
        else:
            parts.append(
                "This idea explores territory that has barely been studied and appears to be novel."
            )
    elif label == "Out-of-Domain":
        parts.append(
            "This idea does not align with existing research in this area. It likely belongs to a "
            "different field entirely, so a meaningful novelty assessment is not possible from "
            "related work alone."
        )

    # ----- Optional crosslink commentary -----
    if (
        not is_duplicate
        and label not in ("Out-of-Domain",)
        and informative.get("crosslink")
    ):
        crosslink_score = features.get("crosslink_score", 0.0)
        if crosslink_score >= 0.75 and topic_phrase:
            parts.append(
                f"The combination of topics it touches ({topic_phrase}) is rare in published research."
            )

    # ----- Optional density commentary -----
    if informative.get("density"):
        density = features.get("density_score", 0.0)
        if density >= 5:
            parts.append("The research area is densely populated with existing work.")
        elif density <= 2 and label != "Out-of-Domain":
            parts.append("The research area is sparsely populated.")

    # ----- Optional recency commentary -----
    if informative.get("recency"):
        recency = features.get("recency_score", 0.0)
        if recency >= 3:
            parts.append("Activity in this area has been growing recently.")
        elif recency <= 1:
            parts.append("Activity in this area appears to be slowing down.")

    if not parts:
        parts.append("Unable to characterize this idea against the corpus with the available signals.")

    return " ".join(parts)


def generate_rule_based_explanation(
    idea_domains: List[str],
    features: Dict,
    classification: Dict
) -> str:
    """
    Deterministic explanation generator.
    Uses percentile ranks when available (combined classifier),
    falls back to raw values (lite mode).
    """

    parts = []
    label = classification["label"]
    percentiles = classification.get("percentiles")
    novelty_score = classification.get("novelty_score")
    informative = classification.get("informative_signals", {})

    if percentiles and novelty_score is not None:
        # --- Combined classifier: percentile-based explanation ---
        sim_pct = percentiles["similarity"]
        density_pct = percentiles["density"]
        recency_pct = percentiles["recency"]
        crosslink_pct = percentiles["crosslink"]

        parts.append(
            f"Novelty Score: {novelty_score}/100."
        )

        # Similarity
        if sim_pct > 80:
            parts.append(
                f"The idea is in the top {100 - sim_pct:.0f}% similarity with existing work "
                f"(max similarity: {features['max_similarity']:.2f}), indicating closely related research exists."
            )
        elif sim_pct > 40:
            parts.append(
                f"The idea shows moderate similarity to existing work "
                f"(percentile: {sim_pct:.0f}th, max similarity: {features['max_similarity']:.2f})."
            )
        else:
            parts.append(
                f"The idea has low similarity to existing literature "
                f"(bottom {sim_pct:.0f}th percentile), suggesting it explores less-charted territory."
            )

        # Density
        if density_pct > 70:
            parts.append(
                f"The research area is relatively crowded (density in {density_pct:.0f}th percentile)."
            )
        elif density_pct < 30:
            parts.append(
                f"The research area is sparse (density in {density_pct:.0f}th percentile), "
                f"with fewer competing publications."
            )

        # Crosslink
        if crosslink_pct > 70:
            parts.append(
                f"The concept combination is notably rare ({crosslink_pct:.0f}th percentile), "
                f"suggesting a novel cross-domain bridge."
            )
        elif crosslink_pct < 30:
            parts.append(
                f"The concept pairing is common in existing literature ({crosslink_pct:.0f}th percentile)."
            )

        # Recency — only report if the corpus has temporal variance.
        # An all-one-year corpus produces a degenerate distribution where
        # every percentile is meaningless.
        if informative.get("recency", True):
            if recency_pct > 70:
                parts.append(
                    f"This area shows growing research activity (recency: {recency_pct:.0f}th percentile)."
                )
            elif recency_pct < 30:
                parts.append(
                    f"Research activity in this area appears to be declining (recency: {recency_pct:.0f}th percentile)."
                )

        parts.append(f"Classification: '{label}'.")

    else:
        # --- Lite mode: raw-value explanation (original) ---
        parts.append(
            f"The idea shows a maximum semantic similarity of "
            f"{features['max_similarity']:.2f} with existing literature."
        )
        parts.append(
            f"The publication density in the relevant area is "
            f"{features['density_score']:.2f}, indicating "
            f"{'a crowded' if features['density_score'] > 3 else 'a relatively sparse'} research space."
        )
        parts.append(
            f"The recency trend score is {features['recency_score']:.2f}, "
            f"suggesting {'growing' if features['recency_score'] > 1 else 'stable or declining'} activity."
        )
        parts.append(
            f"The cross-link novelty score is {features['crosslink_score']:.2f}, "
            f"reflecting the rarity of the concept combinations."
        )
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

Write a concise, neutral explanation (3-4 sentences).
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
