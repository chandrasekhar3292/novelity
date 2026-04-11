# app/main.py

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.health import router as health_router
from app.routes.novelty import router as novelty_router
from app.routes.corpus import router as corpus_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("NOVELTYNET starting...")

    # Load embedding model once (shared across all requests)
    from app.corpus.embedder import Embedder
    from app.corpus.builder import load_index
    from app.corpus.loader import load_papers
    from app.core import similarity as sim_module
    from app.core.corpus_stats import init_stats

    print(f"  Loading embedding model: {settings.EMBEDDING_MODEL}")
    embedder = Embedder()

    print(f"  Loading FAISS index from: {settings.FAISS_INDEX_PATH}")
    index = load_index()

    papers = []
    if index is not None:
        print(f"  Index loaded — {index.index.ntotal} vectors")
        papers = load_papers()
        print(f"  Loaded {len(papers)} papers")
    else:
        print(
            "  No index found. "
            "Run 'python scripts/build_index.py' to build one."
        )

    sim_module.init(embedder, index, papers)

    # Cache corpus submission timeline for the recency signal
    if papers:
        from app.corpus.recency import init_corpus_range
        init_corpus_range(papers)

    # Compute corpus statistics for adaptive classifier
    if index is not None and papers:
        print("  Computing corpus statistics...")
        init_stats(papers, index, embedder)

    yield

    # --- Shutdown ---
    print("NOVELTYNET shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Research novelty detection API. "
        "Combines semantic similarity, density, recency, "
        "and cross-link signals to classify how novel a research idea is."
    ),
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS — open for frontend / demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(novelty_router, prefix=settings.API_PREFIX, tags=["novelty"])
app.include_router(corpus_router, prefix=settings.API_PREFIX, tags=["corpus"])
