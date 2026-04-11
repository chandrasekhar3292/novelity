#!/usr/bin/env python
"""
Bulk-fetch 50k+ AI/ML papers — primarily from arXiv, with a small
supplement from OpenAlex and Semantic Scholar.

Usage:
    # Default: 50k from arXiv + 50 OpenAlex + 50 S2
    python scripts/fetch_bulk_corpus.py

    # Custom arXiv target
    python scripts/fetch_bulk_corpus.py --arxiv 60000

    # Limit per category (8 AI/ML categories)
    python scripts/fetch_bulk_corpus.py --arxiv 50000 --per-cat 8000

    # Filter by year
    python scripts/fetch_bulk_corpus.py --from-year 2018

    # Skip extras (arXiv only)
    python scripts/fetch_bulk_corpus.py --no-extras

    # Skip index building (just fetch)
    python scripts/fetch_bulk_corpus.py --no-index

    # Append to existing corpus
    python scripts/fetch_bulk_corpus.py --append
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Bulk-fetch AI/ML papers (arXiv + extras)"
    )
    parser.add_argument(
        "--arxiv", type=int, default=50_000,
        help="Max papers from arXiv (default: 50000)"
    )
    parser.add_argument(
        "--per-cat", type=int, default=None,
        help="Max papers per arXiv category (default: auto = arxiv / 8)"
    )
    parser.add_argument(
        "--extras", type=int, default=100,
        help="Papers from OpenAlex + S2 combined (default: 100, split 50/50)"
    )
    parser.add_argument(
        "--no-extras", action="store_true",
        help="Skip OpenAlex and S2 entirely"
    )
    parser.add_argument(
        "--from-year", type=int, default=None,
        help="Only fetch papers from this year onward"
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing corpus"
    )
    parser.add_argument(
        "--no-index", action="store_true",
        help="Skip FAISS index building"
    )
    parser.add_argument(
        "--save-every", type=int, default=5000,
        help="Checkpoint every N papers (default: 5000)"
    )
    args = parser.parse_args()

    per_cat = args.per_cat or max(args.arxiv // 8, 1000)
    extras_each = 0 if args.no_extras else args.extras // 2

    print("=" * 60)
    print("  NOVELITY Bulk Corpus Fetcher")
    print(f"  arXiv target:    {args.arxiv:,} papers ({per_cat:,}/category)")
    if not args.no_extras:
        print(f"  OpenAlex extras: {extras_each}")
        print(f"  S2 extras:       {extras_each}")
    if args.from_year:
        print(f"  From year:       {args.from_year}")
    print("=" * 60)

    os.makedirs(settings.DATA_DIR, exist_ok=True)

    # Load existing
    if args.append:
        from app.corpus.loader import load_papers
        all_papers = load_papers()
        print(f"\nLoaded {len(all_papers):,} existing papers.")
    else:
        all_papers = []

    existing_ids = {p["id"] for p in all_papers}
    start_time = time.time()
    added = {"arxiv": 0, "openalex": 0, "s2": 0}
    skipped = 0

    # ── Phase 1: arXiv (bulk) ──────────────────────────────────
    print(f"\n{'-' * 40}")
    print("Phase 1: Fetching from arXiv...")
    print(f"{'-' * 40}")

    from app.corpus.fetcher import fetch_arxiv_bulk, AI_ML_CATEGORIES

    for batch in fetch_arxiv_bulk(
        categories=AI_ML_CATEGORIES,
        max_per_category=per_cat,
        max_total=args.arxiv,
        progress_callback=_progress("arXiv", args.arxiv),
    ):
        new_count = 0
        for paper in batch:
            if paper["id"] in existing_ids:
                skipped += 1
                continue
            # Year filter (arXiv API doesn't support date range in cat queries)
            if args.from_year and paper.get("year") and paper["year"] < args.from_year:
                continue
            all_papers.append(paper)
            existing_ids.add(paper["id"])
            new_count += 1

        added["arxiv"] += new_count

        if added["arxiv"] % args.save_every < len(batch):
            _save_checkpoint(all_papers)

    print(f"\n  arXiv: {added['arxiv']:,} papers added")

    # ── Phase 2: Extras (small) ────────────────────────────────
    if not args.no_extras and extras_each > 0:
        print(f"\n{'-' * 40}")
        print(f"Phase 2: Fetching {extras_each} extras each from OpenAlex & S2...")
        print(f"{'-' * 40}")

        # OpenAlex
        try:
            from app.corpus.fetcher_openalex import fetch_openalex
            for batch in fetch_openalex(
                query="machine learning",
                max_results=extras_each,
            ):
                for paper in batch:
                    if paper["id"] not in existing_ids:
                        paper.pop("_doi", None)
                        paper.pop("_arxiv_id", None)
                        all_papers.append(paper)
                        existing_ids.add(paper["id"])
                        added["openalex"] += 1
            print(f"  OpenAlex: {added['openalex']} papers added")
        except Exception as e:
            print(f"  OpenAlex failed: {e}")

        # Semantic Scholar
        try:
            from app.corpus.fetcher_s2 import fetch_s2
            for batch in fetch_s2(
                query="deep learning neural network",
                max_results=extras_each,
                fields_of_study=["Computer Science"],
            ):
                for paper in batch:
                    if paper["id"] not in existing_ids:
                        paper.pop("_doi", None)
                        paper.pop("_arxiv_id", None)
                        all_papers.append(paper)
                        existing_ids.add(paper["id"])
                        added["s2"] += 1
            print(f"  S2: {added['s2']} papers added")
        except Exception as e:
            print(f"  S2 failed: {e}")

    # ── Results ────────────────────────────────────────────────
    elapsed = time.time() - start_time
    total_new = sum(added.values())

    print(f"\n{'=' * 60}")
    print(f"  RESULTS")
    print(f"{'=' * 60}")
    print(f"  arXiv:     {added['arxiv']:,}")
    print(f"  OpenAlex:  {added['openalex']:,}")
    print(f"  S2:        {added['s2']:,}")
    print(f"  Skipped:   {skipped:,} duplicates")
    print(f"  Total new: {total_new:,}")
    print(f"  Corpus:    {len(all_papers):,} papers")
    print(f"  Time:      {elapsed / 60:.1f} minutes")
    print(f"{'=' * 60}")

    from app.corpus.loader import save_papers
    save_papers(all_papers)
    print(f"\nSaved {len(all_papers):,} papers to {settings.PAPERS_PATH}")

    # ── Index ──────────────────────────────────────────────────
    if not args.no_index and len(all_papers) > 0:
        print("\nTagging papers with concepts...")
        from app.corpus.concepts import tag_papers
        tagged = tag_papers(all_papers)
        save_papers(all_papers)
        print(f"Tagged {tagged:,} papers.")

        print("\nBuilding FAISS index...")
        from app.corpus.builder import build_index
        index, _ = build_index()
        print(f"Done. {index.index.ntotal:,} vectors indexed.")
    elif args.no_index:
        print("\nSkipped index building. Run: python scripts/build_index.py")


def _progress(source, target):
    def cb(total, cat):
        pct = min(total / target * 100, 100) if target > 0 else 0
        print(f"  [{source}] {total:,} / {target:,} ({pct:.1f}%) — {cat}", end="\r")
    return cb


def _save_checkpoint(papers):
    from app.corpus.loader import save_papers
    save_papers(papers)
    print(f"\n  [checkpoint] {len(papers):,} papers saved to disk.")


if __name__ == "__main__":
    main()
