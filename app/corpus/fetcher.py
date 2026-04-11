# app/corpus/fetcher.py
"""Fetch papers from the arXiv API and convert to the corpus schema.

Supports both single queries and bulk fetching with pagination.
arXiv API: max 1000 per request, paginate with `start` offset.
Rate limit: 1 request per 3 seconds.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Generator

import requests

ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}

# AI/ML arXiv categories
AI_ML_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.NE",   # Neural and Evolutionary Computing
    "cs.IR",   # Information Retrieval
    "cs.RO",   # Robotics
    "stat.ML", # Machine Learning (Statistics)
]


def fetch_arxiv(query: str, max_results: int = 200) -> list[dict]:
    """
    Query the arXiv API and return papers in corpus format.
    For small fetches (<=1000). Use fetch_arxiv_bulk for larger.
    """
    params = {
        "search_query": f"all:{query}",
        "max_results": min(max_results, 1000),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API, params=params, timeout=60)
    resp.raise_for_status()
    return _parse_feed(resp.text)


def fetch_arxiv_bulk(
    categories: list[str] | None = None,
    max_per_category: int = 10_000,
    max_total: int = 50_000,
    page_size: int = 1000,
    progress_callback=None,
) -> Generator[list[dict], None, None]:
    """
    Bulk-fetch papers from arXiv by category with pagination.

    Yields batches of papers. Each batch = 1 API page (up to page_size).

    Args:
        categories: arXiv categories to fetch (default: AI_ML_CATEGORIES)
        max_per_category: Max papers per category
        max_total: Overall cap
        page_size: Results per API request (max 1000)
        progress_callback: Called with (total_fetched, category) after each page
    """
    if categories is None:
        categories = AI_ML_CATEGORIES

    page_size = min(page_size, 1000)
    total_fetched = 0

    for cat in categories:
        if total_fetched >= max_total:
            break

        cat_fetched = 0
        start = 0

        while cat_fetched < max_per_category and total_fetched < max_total:
            search_query = f"cat:{cat}"
            params = {
                "search_query": search_query,
                "start": start,
                "max_results": min(page_size, max_per_category - cat_fetched),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            try:
                resp = requests.get(ARXIV_API, params=params, timeout=60)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  [arXiv] Error fetching {cat} at offset {start}: {e}. Retrying...")
                time.sleep(5)
                continue

            papers = _parse_feed(resp.text)
            if not papers:
                break  # No more results for this category

            yield papers
            cat_fetched += len(papers)
            total_fetched += len(papers)
            start += len(papers)

            if progress_callback:
                progress_callback(total_fetched, cat)

            # arXiv rate limit: 1 request per 3 seconds
            time.sleep(3)

        print(f"  [arXiv] {cat}: {cat_fetched:,} papers fetched")


def fetch_arxiv_bulk_all(
    categories: list[str] | None = None,
    max_per_category: int = 10_000,
    max_total: int = 50_000,
) -> list[dict]:
    """Non-generator convenience wrapper."""
    all_papers = []
    for batch in fetch_arxiv_bulk(
        categories=categories,
        max_per_category=max_per_category,
        max_total=max_total,
        progress_callback=lambda total, cat: print(
            f"  [arXiv] {total:,} papers fetched ({cat})...", end="\r"
        ),
    ):
        all_papers.extend(batch)
    return all_papers


def _parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", _NS):
        arxiv_id = _text(entry, "atom:id")
        if arxiv_id:
            arxiv_id = arxiv_id.split("/abs/")[-1].strip()

        title = _text(entry, "atom:title") or ""
        title = re.sub(r"\s+", " ", title).strip()

        abstract = _text(entry, "atom:summary") or ""
        abstract = re.sub(r"\s+", " ", abstract).strip()

        if not abstract:
            continue

        published = _text(entry, "atom:published") or ""
        year: Optional[int] = None
        if published:
            try:
                year = datetime.fromisoformat(published[:10]).year
            except ValueError:
                pass

        authors = [
            _text(a, "atom:name") or ""
            for a in entry.findall("atom:author", _NS)
        ]
        authors = [a.strip() for a in authors if a.strip()]

        categories = [
            el.get("term", "")
            for el in entry.findall("atom:category", _NS)
            if el.get("term", "")
        ]

        papers.append({
            "id": arxiv_id or f"arxiv_{len(papers)}",
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
            "concepts": categories,
        })

    return papers


def _text(element, tag: str) -> Optional[str]:
    el = element.find(tag, _NS)
    return el.text if el is not None else None
