"""Pydantic request/response models for NOVELITY"""

from pydantic import BaseModel, Field
from typing import Optional


class NoveltyRequest(BaseModel):
    title: str = Field(..., min_length=3, description="Paper title")
    abstract: str = Field(..., min_length=10, description="Paper abstract or research description")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of similar papers to return")


class PaperMatch(BaseModel):
    title: str
    similarity: float = Field(..., description="Cosine similarity (0=unrelated, 1=identical)")
    url: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None


class NoveltyResponse(BaseModel):
    novelty_score: float = Field(
        ..., description="0 = identical to existing work, 1 = completely novel"
    )
    interpretation: str
    nearest_neighbors: list[PaperMatch]
    embedding_model: str
    corpus_size: int


class FetchRequest(BaseModel):
    query: str = Field(..., description="arXiv search query (e.g. 'large language models')")
    max_results: int = Field(default=200, ge=1, le=1000)


class CorpusStatus(BaseModel):
    corpus_size: int
    index_loaded: bool
    embedding_model: str
