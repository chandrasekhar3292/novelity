# app/corpus/fetcher_s2.py
"""Bulk-fetch papers from the Semantic Scholar Academic Graph API.

Uses the bulk search endpoint for efficient large-scale retrieval.
Docs: https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_paper_bulk_search

Rate limits (no API key): ~1 req/s, 1000 results per page.
With API key: ~10 req/s.
"""

import os
import time
from typing import Optional, Generator

import requests

S2_BULK_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIELDS = "paperId,title,abstract,authors,year,url,s2FieldsOfStudy,externalIds"


def fetch_s2(
    query: str,
    max_results: int = 50_000,
    year_range: Optional[str] = None,
    fields_of_study: Optional[list[str]] = None,
    api_key: Optional[str] = None,
    progress_callback=None,
) -> Generator[list[dict], None, None]:
    """
    Fetch papers from Semantic Scholar bulk search endpoint.

    Yields batches of papers (each batch = one API page, up to 1000).

    Args:
        query: Search query (e.g. "deep learning")
        max_results: Stop after this many papers
        year_range: Year filter (e.g. "2018-2024" or "2020-")
        fields_of_study: Filter by S2 fields (e.g. ["Computer Science"])
        api_key: Optional S2 API key for higher rate limits
        progress_callback: Called with (fetched_so_far, batch_size) after each page
    """
    if api_key is None:
        api_key = os.getenv("S2_API_KEY")

    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "query": query,
        "fields": S2_FIELDS,
    }

    if year_range:
        params["year"] = year_range
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    total_fetched = 0
    token = None

    while total_fetched < max_results:
        if token:
            params["token"] = token

        try:
            resp = requests.get(
                S2_BULK_SEARCH, params=params, headers=headers, timeout=30
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"[S2] Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[S2] Request error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        data = resp.json()
        raw_papers = data.get("data", [])
        if not raw_papers:
            break

        papers = []
        for item in raw_papers:
            paper = _convert_paper(item)
            if paper:
                papers.append(paper)

        if papers:
            yield papers
            total_fetched += len(papers)

        if progress_callback:
            progress_callback(total_fetched, len(papers))

        # Token-based pagination
        token = data.get("token")
        if not token:
            break

        # Rate limit: 1 req/s without key, faster with key
        time.sleep(0.2 if api_key else 1.0)


def fetch_s2_all(
    query: str,
    max_results: int = 50_000,
    year_range: Optional[str] = None,
    fields_of_study: Optional[list[str]] = None,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Non-generator convenience wrapper — returns all papers as a flat list."""
    all_papers = []
    for batch in fetch_s2(
        query=query,
        max_results=max_results,
        year_range=year_range,
        fields_of_study=fields_of_study,
        api_key=api_key,
        progress_callback=lambda total, batch: print(f"  [S2] {total} papers fetched..."),
    ):
        all_papers.extend(batch)
    return all_papers


def _convert_paper(item: dict) -> Optional[dict]:
    """Convert a Semantic Scholar paper to our corpus schema."""
    abstract = (item.get("abstract") or "").strip()
    if not abstract or len(abstract) < 20:
        return None

    paper_id = item.get("paperId", "")
    title = (item.get("title") or "").strip()

    authors = []
    for author in (item.get("authors") or [])[:20]:
        name = author.get("name", "")
        if name:
            authors.append(name)

    year = item.get("year")
    url = item.get("url") or ""

    # Extract field of study names as concepts
    concepts = []
    for fos in (item.get("s2FieldsOfStudy") or []):
        cat = fos.get("category", "")
        if cat:
            concepts.append(cat)

    # Use DOI or ArXiv ID if available for cross-source dedup
    ext_ids = item.get("externalIds") or {}

    return {
        "id": f"s2_{paper_id}",
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "url": url,
        "concepts": concepts,
        "source": "s2",
        "_arxiv_id": ext_ids.get("ArXiv"),
        "_doi": ext_ids.get("DOI"),
    }
