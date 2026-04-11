# app/corpus/recency.py

import re
from typing import Dict, List, Optional

# arXiv IDs encode submission date as YYMM in the leading 4 digits, e.g.
# "2604.02330v1" = April 2026. Year-only data is too coarse for a corpus
# that spans only one or two years; the YYMM format gives us month-level
# resolution while still being deterministic and offline.
_ARXIV_ID_RE = re.compile(r"^(\d{2})(\d{2})\.")


_corpus_month_range: Optional[tuple] = None  # (min_month, max_month) cache


def _months_from_paper(p: Dict) -> Optional[int]:
    """Return YYYY*12 + MM for the paper, or None if unparseable."""
    m = _ARXIV_ID_RE.match(p.get("id") or "")
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        if 1 <= mm <= 12:
            return (2000 + yy) * 12 + mm
    # Fallback to year-only data, mid-year
    year = p.get("year")
    if isinstance(year, int) and year > 1900:
        return year * 12 + 6
    return None


def init_corpus_range(papers: List[Dict]) -> None:
    """
    Cache the corpus's min/max submission month at startup so compute_recency
    can normalize neighbor positions against the full timeline rather than
    against the local neighborhood (which would always look like the full
    corpus and produce constant scores).
    """
    global _corpus_month_range
    months = [m for m in (_months_from_paper(p) for p in papers) if m]
    if months:
        _corpus_month_range = (min(months), max(months))
    else:
        _corpus_month_range = None


def compute_recency(similar_papers: List[Dict]) -> float:
    """
    Recency = where the top-K neighbors sit on the corpus submission
    timeline, expressed on a [0, 10] scale where 10 is the most recent
    submission month and 0 is the oldest.

    Concretely: take the mean submission month of the neighbors, then
    project it onto the cached corpus min..max month range. Topics whose
    neighbors cluster in the most recent months score high; topics whose
    neighbors live in older months score low.

    This is more robust on heavily skewed corpora than a recent/past
    ratio, which saturates whenever almost everything was submitted in
    the last few months.
    """
    if not similar_papers:
        return 0.0

    months = [m for m in (_months_from_paper(p) for p in similar_papers) if m]
    if not months:
        return 0.0

    mean_month = sum(months) / len(months)

    if _corpus_month_range is None:
        # No cached range — fall back to using local neighborhood span.
        local_min, local_max = min(months), max(months)
    else:
        local_min, local_max = _corpus_month_range

    span = local_max - local_min
    if span <= 0:
        return 5.0  # corpus has no temporal spread; return mid-scale

    normalized = (mean_month - local_min) / span  # [0, 1]
    return float(round(max(0.0, min(1.0, normalized)) * 10, 3))
