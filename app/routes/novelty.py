# app/routes/novelty.py

import re
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.idea import process_idea
from app.core.similarity import SimilarityEngine, is_ready
from app.core.density import compute_density
from app.core.crosslink import compute_crosslink_score
from app.core.features import build_feature_vector
from app.core.classifier import classify_novelty
from app.core.explanation import generate_narrative_explanation
from app.corpus.loader import load_papers
from app.corpus.recency import compute_recency

router = APIRouter()


_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def _normalize_words(text: str) -> set:
    return set(w.lower() for w in _WORD_RE.findall(text or "") if len(w) >= 3)


def _detect_duplicate(idea_text: str, top_paper: Optional[dict]) -> bool:
    """
    True when the idea is essentially the same as the top match.

    Heuristic: strip a leading "Name:" prefix from the title (handles paper
    naming conventions like "VOID: Video Object..."), then check whether
    >=80% of the title's content words appear in the idea text. This catches
    users pasting a paper title or near-verbatim abstract into the analyzer.
    """
    if not top_paper:
        return False
    title = (top_paper.get("title") or "").strip()
    if len(title) < 10:
        return False

    # Strip leading "ACRONYM: " or "Name: " prefix
    title_clean = re.sub(r"^[A-Za-z0-9\-]+:\s*", "", title)

    title_words = _normalize_words(title_clean)
    if len(title_words) < 3:
        return False

    text_words = _normalize_words(idea_text)
    overlap = len(title_words & text_words) / len(title_words)
    return overlap >= 0.8

_sim_engine = SimilarityEngine()


class NoveltyRequest(BaseModel):
    idea: str


def _run_pipeline(idea_text: str, use_llm: bool = True) -> dict:
    """Core pipeline shared by /analyze and /analyze/lite."""
    if use_llm:
        idea_info = process_idea(idea_text)
    else:
        from app.core.idea import _fallback_extraction
        tags = _fallback_extraction(idea_text)
        idea_info = {"idea_text": idea_text, **tags}

    # Pass extracted concepts for category-aware similarity
    idea_concepts = idea_info.get("concepts", []) + idea_info.get("domains", [])
    similarity = _sim_engine.analyze(idea_text, idea_concepts=idea_concepts)

    corpus = load_papers()
    similar_papers = [
        {**corpus[i], "similarity": float(score)}
        for i, score in zip(similarity["top_indices"], similarity["scores"])
        if 0 <= i < len(corpus)
    ]

    density = compute_density(similar_papers)
    recency = compute_recency(similar_papers)
    crosslink = compute_crosslink_score(
        idea_info["concepts"], corpus, similar_papers=similar_papers,
    )
    features = build_feature_vector(similarity, density, recency, crosslink)
    classification = classify_novelty(features)

    # Duplicate override: if the user pasted a paper title verbatim, the
    # classifier will land on Direct Gap Fill but the verdict should be
    # the harder "not novel" — there is no gap to investigate, the work
    # already exists.
    top = similar_papers[0] if similar_papers else None
    if _detect_duplicate(idea_text, top):
        classification["verdict"] = "not_novel"
        classification["verdict_text"] = (
            f"Not novel — closely matches \u2018{top.get('title', '')}\u2019"
        )
        classification["is_duplicate"] = True

    explanation = generate_narrative_explanation(
        idea_text=idea_text,
        top_paper=top,
        features=features,
        classification=classification,
        idea_concepts=idea_info.get("concepts"),
    )

    return {
        "idea": idea_info,
        "similar_papers": similar_papers[:5],
        "features": features,
        "classification": classification,
        "explanation": explanation,
    }


def _require_index():
    if not is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Corpus index not loaded. "
                "Run 'python scripts/build_index.py' to build it first."
            ),
        )


@router.post("/analyze")
def analyze_idea(request: NoveltyRequest):
    """
    Full pipeline: semantic similarity + density + recency + cross-link.
    Uses OpenAI to extract domains and concepts from the idea.
    Requires OPENAI_API_KEY in environment.
    """
    _require_index()
    try:
        return _run_pipeline(request.idea, use_llm=True)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/lite")
def analyze_idea_lite(request: NoveltyRequest):
    """
    Lite pipeline: same signals but uses keyword extraction instead of OpenAI.
    Works without an OPENAI_API_KEY — ideal for testing and local development.
    Cross-link score may be less accurate due to simpler concept extraction.
    """
    _require_index()
    try:
        return _run_pipeline(request.idea, use_llm=False)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
