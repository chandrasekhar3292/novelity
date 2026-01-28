# app/corpus/loader.py

import json
from typing import List, Dict

from app.config import settings


REQUIRED_FIELDS = {"id", "abstract", "year", "concepts"}


def load_papers() -> List[Dict]:
    """
    Loads paper metadata from a local JSON file.
    Expected schema per paper:
    {
        "id": str,
        "abstract": str,
        "year": int,
        "concepts": [str, ...]
    }
    """

    with open(settings.PAPERS_PATH, "r", encoding="utf-8") as f:
        papers = json.load(f)

    if not isinstance(papers, list):
        raise ValueError("papers.json must contain a list")

    cleaned = []

    for p in papers:
        if not REQUIRED_FIELDS.issubset(p.keys()):
            raise ValueError(f"Paper missing required fields: {p}")

        if not p["abstract"].strip():
            continue  # skip useless entries

        cleaned.append({
            "id": p["id"],
            "abstract": p["abstract"].strip(),
            "year": int(p["year"]),
            "concepts": p["concepts"]
        })

    return cleaned
