# app/routes/novelty.py

import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.idea import process_idea
from app.core.similarity import SimilarityEngine, is_ready
from app.core.density import compute_density
from app.core.crosslink import compute_crosslink_score
from app.core.features import build_feature_vector
from app.core.classifier import classify_novelty
from app.core.explanation import generate_rule_based_explanation
from app.corpus.loader import load_papers
from app.corpus.recency import compute_recency

router = APIRouter()

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

    similarity = _sim_engine.analyze(idea_text)

    corpus = load_papers()
    similar_papers = [
        corpus[i] for i in similarity["top_indices"]
        if 0 <= i < len(corpus)
    ]

    density = compute_density(similar_papers)
    recency = compute_recency(similar_papers)
    crosslink = compute_crosslink_score(idea_info["concepts"], corpus)
    features = build_feature_vector(similarity, density, recency, crosslink)
    classification = classify_novelty(features)
    explanation = generate_rule_based_explanation(
        idea_info["domains"], features, classification
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
