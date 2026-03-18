#!/usr/bin/env python
"""
Build the FAISS vector index from data/papers.json.

Usage:
    python scripts/build_index.py

The index is saved to data/index.faiss (configurable via FAISS_INDEX_PATH).
Run this script whenever papers.json is updated.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.corpus.builder import build_index


def main():
    try:
        index, papers = build_index()
        print(f"Done. Indexed {len(papers)} papers.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
