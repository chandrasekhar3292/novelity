# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # App
    APP_NAME = "NOVELTYNET"
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"

    # API
    API_PREFIX = "/api"

    # Embeddings
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Paths
    DATA_DIR = os.getenv("DATA_DIR", "data")
    PAPERS_PATH = os.path.join(DATA_DIR, "papers.json")
    FAISS_INDEX_PATH = os.path.join(DATA_DIR, "index.faiss")

    # Retrieval
    TOP_K = int(os.getenv("TOP_K", 20))

settings = Settings()
