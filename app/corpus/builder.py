# app/corpus/builder.py
"""Build and persist the FAISS index from papers.json"""

import os
from typing import Optional

from app.corpus.embedder import Embedder
from app.corpus.index import VectorIndex
from app.corpus.loader import load_papers
from app.config import settings


def build_index(embedder: Optional[Embedder] = None) -> tuple[VectorIndex, list[dict]]:
    """
    Load papers, embed abstracts, build FAISS index, and save to disk.
    Returns (VectorIndex, papers) so the caller can keep both in memory.
    """
    papers = load_papers()
    if not papers:
        raise ValueError(
            f"No papers found at {settings.PAPERS_PATH}. "
            "Run scripts/fetch_corpus.py first."
        )

    if embedder is None:
        embedder = Embedder()

    texts = [
        f"{p.get('title', '')}. {p['abstract']}".strip()
        for p in papers
    ]

    print(f"Embedding {len(texts)} papers...")
    vectors = embedder.embed_batch(texts)

    dim = vectors.shape[1]
    index = VectorIndex(dim)
    index.add(vectors)

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    index.save(settings.FAISS_INDEX_PATH)
    print(f"Index saved to {settings.FAISS_INDEX_PATH}")

    return index, papers


def load_index() -> Optional[VectorIndex]:
    """Load an existing FAISS index from disk, or return None if not found."""
    try:
        return VectorIndex.load(settings.FAISS_INDEX_PATH)
    except FileNotFoundError:
        return None
