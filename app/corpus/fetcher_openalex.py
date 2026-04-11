# app/corpus/fetcher_openalex.py
"""Bulk-fetch papers from the OpenAlex API (free, no key required).

OpenAlex concepts for AI/ML:
  C154945302 = "Artificial intelligence"
  C119857082 = "Machine learning"
  C41008148  = "Computer science"
  C108827166 = "Deep learning"
  C204321447 = "Natural language processing"
  C31972630  = "Computer vision"

Docs: https://docs.openalex.org/api-entities/works
"""

import time
from typing import Optional, Generator

import requests

OPENALEX_API = "https://api.openalex.org/works"

# OpenAlex concept IDs for AI/ML sub-fields
AI_ML_CONCEPTS = [
    "C154945302",  # Artificial intelligence
    "C119857082",  # Machine learning
    "C108827166",  # Deep learning
    "C204321447",  # Natural language processing
    "C31972630",   # Computer vision
]

DEFAULT_FILTER = "concepts.id:" + "|".join(AI_ML_CONCEPTS)


def fetch_openalex(
    query: Optional[str] = None,
    concept_filter: str = DEFAULT_FILTER,
    max_results: int = 50_000,
    per_page: int = 200,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    mailto: Optional[str] = None,
    progress_callback=None,
) -> Generator[list[dict], None, None]:
    """
    Fetch papers from OpenAlex using cursor pagination.

    Yields batches of papers (each batch = one API page, up to `per_page`).
    This is a generator so callers can save incrementally.

    Args:
        query: Full-text search query (optional, adds to filter)
        concept_filter: OpenAlex filter string for concepts
        max_results: Stop after this many papers
        per_page: Results per API page (max 200)
        from_year: Filter papers published from this year
        to_year: Filter papers published up to this year
        mailto: Email for OpenAlex polite pool (faster rate limits)
        progress_callback: Called with (fetched_so_far, batch_size) after each page
    """
    params = {
        "per_page": min(per_page, 200),
        "cursor": "*",
        "select": "id,title,authorships,publication_year,primary_location,concepts,abstract_inverted_index",
    }

    # Build filter
    filters = []
    if concept_filter:
        filters.append(concept_filter)
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    filters.append("has_abstract:true")

    params["filter"] = ",".join(filters)

    if query:
        params["search"] = query

    if mailto:
        params["mailto"] = mailto

    total_fetched = 0

    while total_fetched < max_results:
        try:
            resp = requests.get(OPENALEX_API, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[OpenAlex] Request error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        papers = []
        for work in results:
            paper = _convert_work(work)
            if paper:
                papers.append(paper)

        if papers:
            yield papers
            total_fetched += len(papers)

        if progress_callback:
            progress_callback(total_fetched, len(papers))

        # Cursor pagination
        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

        # Polite rate limiting: ~10 req/s for polite pool, ~1 req/s otherwise
        time.sleep(0.15 if mailto else 1.0)


def fetch_openalex_all(
    query: Optional[str] = None,
    max_results: int = 50_000,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    mailto: Optional[str] = None,
) -> list[dict]:
    """Non-generator convenience wrapper — returns all papers as a flat list."""
    all_papers = []
    for batch in fetch_openalex(
        query=query,
        max_results=max_results,
        from_year=from_year,
        to_year=to_year,
        mailto=mailto,
        progress_callback=lambda total, batch: print(f"  [OpenAlex] {total} papers fetched..."),
    ):
        all_papers.extend(batch)
    return all_papers


def _convert_work(work: dict) -> Optional[dict]:
    """Convert an OpenAlex work object to our corpus schema."""
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
    if not abstract or len(abstract) < 20:
        return None

    openalex_id = work.get("id", "")
    # e.g. "https://openalex.org/W2741809807" → "W2741809807"
    short_id = openalex_id.split("/")[-1] if openalex_id else ""

    title = work.get("title") or ""

    authors = []
    for authorship in (work.get("authorships") or [])[:20]:  # cap at 20 authors
        name = authorship.get("author", {}).get("display_name", "")
        if name:
            authors.append(name)

    year = work.get("publication_year")

    # Get DOI or landing page URL
    url = None
    loc = work.get("primary_location") or {}
    if loc.get("landing_page_url"):
        url = loc["landing_page_url"]

    # Extract concept names
    concepts = []
    for c in (work.get("concepts") or []):
        if c.get("score", 0) >= 0.3:  # only keep reasonably confident concepts
            concepts.append(c.get("display_name", ""))
    concepts = [c for c in concepts if c]

    return {
        "id": f"openalex_{short_id}",
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "url": url,
        "concepts": concepts,
        "source": "openalex",
    }


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""

    # inverted_index: {"word": [pos1, pos2, ...], ...}
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)
