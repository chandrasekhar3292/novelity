# app/corpus/fetcher.py
"""Fetch papers from the arXiv API and convert to the corpus schema."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import requests

ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(query: str, max_results: int = 200) -> list[dict]:
    """
    Query the arXiv API and return papers in NOVELITY corpus format.

    Args:
        query: arXiv search query, e.g. "large language models"
        max_results: number of papers to retrieve (max 1000)

    Returns:
        List of paper dicts with keys: id, title, abstract, authors, year, url, concepts
    """
    params = {
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API, params=params, timeout=60)
    resp.raise_for_status()
    return _parse_feed(resp.text)


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

        # Parse arXiv subject categories (e.g. cs.LG, cs.AI, stat.ML)
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
            "concepts": categories,  # arXiv taxonomy labels
        })

    return papers


def _text(element, tag: str) -> Optional[str]:
    el = element.find(tag, _NS)
    return el.text if el is not None else None
