"""Health check endpoint"""
from fastapi import APIRouter

from app.core.similarity import is_ready
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Returns service status and corpus info."""
    from app.corpus.loader import load_papers
    papers = load_papers()
    return {
        "status": "ok",
        "corpus_size": len(papers),
        "index_ready": is_ready(),
        "embedding_model": settings.EMBEDDING_MODEL,
    }
