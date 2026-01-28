# scripts/build_index.py

from app.corpus.loader import load_papers
from app.corpus.embedder import Embedder
from app.corpus.index import VectorIndex
from app.config import settings


def main():
    print("📚 Loading papers...")
    papers = load_papers()

    print(f"✅ Loaded {len(papers)} papers")

    abstracts = [p["abstract"] for p in papers]

    print("🧠 Generating embeddings...")
    embedder = Embedder()
    vectors = embedder.embed_batch(abstracts)

    print("📐 Building FAISS index...")
    index = VectorIndex(dim=vectors.shape[1])
    index.add(vectors)

    print("💾 Saving index...")
    index.save(settings.FAISS_INDEX_PATH)

    print("🎉 Index build complete")
    print(f"Saved to: {settings.FAISS_INDEX_PATH}")


if __name__ == "__main__":
    main()
