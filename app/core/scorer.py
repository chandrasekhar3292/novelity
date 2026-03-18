"""Novelty scoring against the loaded FAISS index"""

import numpy as np

from app.core import embedder
from app.core import index as faiss_index


def interpret(score: float) -> str:
    if score >= 0.80:
        return "highly novel"
    elif score >= 0.60:
        return "moderately novel"
    elif score >= 0.40:
        return "somewhat novel"
    else:
        return "low novelty — closely matches existing work"


def score(title: str, abstract: str, top_k: int, papers: list[dict]) -> dict:
    """
    Embed the query, search the FAISS index, and return a novelty assessment.

    Novelty score = 1 - max_cosine_similarity_to_corpus
    (0 = identical to existing work, 1 = completely novel)
    """
    text = f"{title}. {abstract}"
    emb = embedder.encode([text])

    similarities, indices = faiss_index.search(emb[0], top_k)

    if len(similarities) == 0:
        return {
            "novelty_score": 1.0,
            "interpretation": "highly novel (corpus is empty)",
            "nearest_neighbors": [],
        }

    novelty_score = round(float(1.0 - similarities[0]), 4)

    neighbors = []
    for sim, i in zip(similarities, indices):
        i = int(i)
        if i < 0 or i >= len(papers):
            continue
        paper = papers[i]
        neighbors.append({
            "title": paper.get("title", ""),
            "similarity": round(float(sim), 4),
            "url": paper.get("url"),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
        })

    return {
        "novelty_score": novelty_score,
        "interpretation": interpret(novelty_score),
        "nearest_neighbors": neighbors,
    }
