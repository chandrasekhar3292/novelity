
#!/usr/bin/env python
"""
Fetch papers from arXiv and build the FAISS index.

Usage:
    python scripts/fetch_corpus.py --query "large language models" --max 300
    python scripts/fetch_corpus.py --query "graph neural networks" --max 200 --append

Papers are saved to data/papers.json. The FAISS index is rebuilt automatically.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.corpus.fetcher import fetch_arxiv
from app.corpus.loader import load_papers, save_papers
from app.corpus.builder import build_index
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="Fetch arXiv papers and build the corpus index.")
    parser.add_argument("--query", required=True, help="arXiv search query (e.g. 'transformer attention')")
    parser.add_argument("--max", type=int, default=200, dest="max_results", help="Max papers to fetch (default: 200)")
    parser.add_argument("--append", action="store_true", help="Append to existing corpus instead of overwriting")
    args = parser.parse_args()

    print(f"Fetching up to {args.max_results} papers for query: '{args.query}'")
    new_papers = fetch_arxiv(args.query, args.max_results)
    print(f"Retrieved {len(new_papers)} papers from arXiv.")

    if args.append:
        existing = load_papers()
        existing_ids = {p["id"] for p in existing}
        added = [p for p in new_papers if p["id"] not in existing_ids]
        papers = existing + added
        print(f"Appended {len(added)} new papers (skipped {len(new_papers) - len(added)} duplicates).")
    else:
        papers = new_papers

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    save_papers(papers)
    print(f"Saved {len(papers)} papers to {settings.PAPERS_PATH}")

    print("Extracting concepts (KeyBERT)...")
    from app.corpus.concepts import tag_papers
    tagged = tag_papers(papers)
    save_papers(papers)
    print(f"Tagged {tagged} papers with concepts.")

    print("Building FAISS index...")
    index, _ = build_index()
    print(f"Done. {index.index.ntotal} vectors indexed.")


if __name__ == "__main__":
    main()
