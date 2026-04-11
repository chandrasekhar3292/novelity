# app/routes/corpus.py
"""Corpus management — add papers manually, upload JSON, rebuild index."""

import json

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

from app.corpus.loader import load_papers, save_papers
from app.corpus.builder import build_index, load_index
from app.corpus.embedder import Embedder
from app.core import similarity as sim_module
from app.config import settings

router = APIRouter()


class PaperIn(BaseModel):
    id: str = Field(..., description="Unique paper identifier (e.g. arxiv ID or your own)")
    title: str = Field(default="", description="Paper title")
    abstract: str = Field(..., min_length=10, description="Paper abstract")
    year: Optional[int] = Field(default=None, description="Publication year")
    authors: Optional[list[str]] = Field(default=[], description="Author names")
    url: Optional[str] = Field(default=None, description="Link to full paper")
    concepts: Optional[list[str]] = Field(default=[], description="Key concepts (improves cross-link scoring)")


class AddPapersRequest(BaseModel):
    papers: list[PaperIn]


def _rebuild(papers: list[dict]):
    """Tag missing concepts, persist papers, and rebuild the FAISS index."""
    from app.corpus.concepts import tag_papers
    tag_papers(papers)  # fills concepts for any paper that has none
    save_papers(papers)
    embedder = sim_module._embedder or Embedder()
    index, _ = build_index(embedder=embedder)
    sim_module.init(embedder, index)


@router.post("/corpus/papers")
def add_papers(req: AddPapersRequest):
    """
    Add one or more papers to the corpus and rebuild the index.

    Duplicate IDs are ignored (existing paper is kept).
    """
    existing = load_papers()
    existing_ids = {p["id"] for p in existing}

    new_papers = [p.model_dump() for p in req.papers if p.id not in existing_ids]
    skipped = len(req.papers) - len(new_papers)

    if not new_papers:
        return {
            "status": "no_change",
            "added": 0,
            "skipped": skipped,
            "corpus_size": len(existing),
        }

    updated = existing + new_papers
    _rebuild(updated)

    return {
        "status": "ok",
        "added": len(new_papers),
        "skipped": skipped,
        "corpus_size": len(updated),
    }


@router.post("/corpus/upload")
async def upload_papers(file: UploadFile = File(...)):
    """
    Upload a JSON file containing an array of papers.

    Expected format — array of objects with at minimum: id, abstract.
    Optional fields: title, year, authors, url, concepts.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted.")

    content = await file.read()
    try:
        incoming = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(incoming, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of paper objects.")

    # Validate required fields
    valid, invalid = [], []
    for i, p in enumerate(incoming):
        if not isinstance(p, dict) or not p.get("id") or not p.get("abstract", "").strip():
            invalid.append(i)
        else:
            valid.append(p)

    if not valid:
        raise HTTPException(
            status_code=422,
            detail=f"No valid papers found. Each paper needs 'id' and 'abstract'.",
        )

    existing = load_papers()
    existing_ids = {p["id"] for p in existing}
    new_papers = [p for p in valid if p["id"] not in existing_ids]
    skipped_dup = len(valid) - len(new_papers)

    updated = existing + new_papers
    _rebuild(updated)

    return {
        "status": "ok",
        "added": len(new_papers),
        "skipped_duplicates": skipped_dup,
        "skipped_invalid": len(invalid),
        "corpus_size": len(updated),
    }


@router.delete("/corpus/papers/{paper_id}")
def delete_paper(paper_id: str):
    """Remove a paper from the corpus by ID and rebuild the index."""
    existing = load_papers()
    updated = [p for p in existing if p["id"] != paper_id]

    if len(updated) == len(existing):
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found.")

    if updated:
        _rebuild(updated)
    else:
        save_papers([])

    return {
        "status": "ok",
        "removed": paper_id,
        "corpus_size": len(updated),
    }


@router.get("/corpus/papers")
def list_papers(limit: int = 50, offset: int = 0):
    """List papers currently in the corpus."""
    papers = load_papers()
    page = papers[offset: offset + limit]
    return {
        "total": len(papers),
        "offset": offset,
        "limit": limit,
        "papers": [
            {"id": p["id"], "title": p.get("title", ""), "year": p.get("year")}
            for p in page
        ],
    }


class ArxivFetchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="arXiv search query (e.g. 'transformer attention')")
    max_results: int = Field(default=100, ge=1, le=500, description="Max papers to fetch")


class OpenAlexFetchRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Full-text search query (optional)")
    max_results: int = Field(default=1000, ge=1, le=50000, description="Max papers to fetch")
    from_year: Optional[int] = Field(default=None, description="Papers published from this year")
    to_year: Optional[int] = Field(default=None, description="Papers published up to this year")
    mailto: Optional[str] = Field(default=None, description="Email for polite pool (faster rate limits)")


class S2FetchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search query (e.g. 'deep learning')")
    max_results: int = Field(default=1000, ge=1, le=50000, description="Max papers to fetch")
    year_range: Optional[str] = Field(default=None, description="Year filter (e.g. '2018-2024')")
    fields_of_study: Optional[list[str]] = Field(default=None, description="S2 fields (e.g. ['Computer Science'])")


@router.post("/corpus/fetch-arxiv")
def fetch_from_arxiv(req: ArxivFetchRequest):
    """
    Fetch papers from arXiv by query, add to corpus, and rebuild index.
    Duplicate IDs are skipped.
    """
    from app.corpus.fetcher import fetch_arxiv

    fetched = fetch_arxiv(req.query, req.max_results)
    if not fetched:
        return {
            "status": "no_results",
            "fetched": 0,
            "added": 0,
            "skipped": 0,
            "corpus_size": len(load_papers()),
        }

    existing = load_papers()
    existing_ids = {p["id"] for p in existing}
    new_papers = [p for p in fetched if p["id"] not in existing_ids]
    skipped = len(fetched) - len(new_papers)

    if not new_papers:
        return {
            "status": "no_change",
            "fetched": len(fetched),
            "added": 0,
            "skipped": skipped,
            "corpus_size": len(existing),
        }

    updated = existing + new_papers
    _rebuild(updated)

    return {
        "status": "ok",
        "fetched": len(fetched),
        "added": len(new_papers),
        "skipped": skipped,
        "corpus_size": len(updated),
    }


@router.post("/corpus/fetch-openalex")
def fetch_from_openalex(req: OpenAlexFetchRequest):
    """
    Fetch papers from OpenAlex (AI/ML concepts), add to corpus, and rebuild index.
    No API key needed. Use mailto for faster rate limits.
    """
    from app.corpus.fetcher_openalex import fetch_openalex

    existing = load_papers()
    existing_ids = {p["id"] for p in existing}
    new_papers = []
    total_fetched = 0

    for batch in fetch_openalex(
        query=req.query,
        max_results=req.max_results,
        from_year=req.from_year,
        to_year=req.to_year,
        mailto=req.mailto,
    ):
        for paper in batch:
            total_fetched += 1
            if paper["id"] not in existing_ids:
                # Strip internal dedup fields
                paper.pop("_doi", None)
                paper.pop("_arxiv_id", None)
                new_papers.append(paper)
                existing_ids.add(paper["id"])

    if not new_papers:
        return {
            "status": "no_change",
            "fetched": total_fetched,
            "added": 0,
            "skipped": total_fetched,
            "corpus_size": len(existing),
        }

    updated = existing + new_papers
    _rebuild(updated)

    return {
        "status": "ok",
        "fetched": total_fetched,
        "added": len(new_papers),
        "skipped": total_fetched - len(new_papers),
        "corpus_size": len(updated),
    }


@router.post("/corpus/fetch-s2")
def fetch_from_s2(req: S2FetchRequest):
    """
    Fetch papers from Semantic Scholar, add to corpus, and rebuild index.
    Set S2_API_KEY env var for higher rate limits.
    """
    from app.corpus.fetcher_s2 import fetch_s2

    existing = load_papers()
    existing_ids = {p["id"] for p in existing}
    new_papers = []
    total_fetched = 0

    for batch in fetch_s2(
        query=req.query,
        max_results=req.max_results,
        year_range=req.year_range,
        fields_of_study=req.fields_of_study,
    ):
        for paper in batch:
            total_fetched += 1
            if paper["id"] not in existing_ids:
                paper.pop("_doi", None)
                paper.pop("_arxiv_id", None)
                new_papers.append(paper)
                existing_ids.add(paper["id"])

    if not new_papers:
        return {
            "status": "no_change",
            "fetched": total_fetched,
            "added": 0,
            "skipped": total_fetched,
            "corpus_size": len(existing),
        }

    updated = existing + new_papers
    _rebuild(updated)

    return {
        "status": "ok",
        "fetched": total_fetched,
        "added": len(new_papers),
        "skipped": total_fetched - len(new_papers),
        "corpus_size": len(updated),
    }


@router.get("/corpus/status")
def corpus_status():
    """Current corpus and index status."""
    papers = load_papers()
    return {
        "corpus_size": len(papers),
        "index_ready": sim_module.is_ready(),
        "embedding_model": settings.EMBEDDING_MODEL,
        "papers_path": settings.PAPERS_PATH,
        "index_path": settings.FAISS_INDEX_PATH,
    }
