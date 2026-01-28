# app/routes/novelty.py

import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.idea import process_idea
from app.core.similarity import SimilarityEngine


router = APIRouter()


class NoveltyRequest(BaseModel):
    idea: str


@router.post("/analyze")
def analyze_idea(request: NoveltyRequest):
    try:
        # Step 3: Idea processing
        idea_info = process_idea(request.idea)

        # Step 4: Similarity
        sim_engine = SimilarityEngine()
        similarity = sim_engine.analyze(request.idea)

        # Load corpus metadata
        from app.corpus.loader import load_papers
        corpus = load_papers()

        # Map indices → papers
        similar_papers = [
            corpus[i] for i in similarity["top_indices"]
            if i < len(corpus)
        ]

        # Step 5 & 6
        from app.core.density import compute_density
        from app.corpus.recency import compute_recency

        density = compute_density(similar_papers)
        recency = compute_recency(similar_papers)

        # Step 7
        from app.core.crosslink import compute_crosslink_score
        crosslink = compute_crosslink_score(
            idea_info["concepts"], corpus
        )

        # Step 8
        from app.core.features import build_feature_vector
        features = build_feature_vector(
            similarity, density, recency, crosslink
        )

        # Step 9
        from app.core.classifier import classify_novelty
        classification = classify_novelty(features)

        # Step 10
        from app.core.explanation import generate_rule_based_explanation
        explanation = generate_rule_based_explanation(
            idea_info["domains"],
            features,
            classification
        )

        return {
            "idea": idea_info,
            "features": features,
            "classification": classification,
            "explanation": explanation
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
