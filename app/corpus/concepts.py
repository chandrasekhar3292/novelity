# app/corpus/concepts.py
"""
Fast concept extraction using TF-IDF (sklearn).
Used for user-uploaded papers that don't have arXiv category labels.
No model loading — runs in milliseconds.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def extract_concepts_tfidf(texts: list[str], top_n: int = 8) -> list[list[str]]:
    """
    Extract top TF-IDF keywords for each text in a batch.
    Returns one list of concepts per input text.
    """
    if not texts:
        return []

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        max_features=5000,
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    results = []
    for row in tfidf_matrix:
        scores = row.toarray().flatten()
        top_indices = np.argsort(scores)[::-1][:top_n]
        keywords = [feature_names[i] for i in top_indices if scores[i] > 0]
        results.append(keywords)

    return results


def tag_papers(papers: list[dict], overwrite: bool = False) -> int:
    """
    Add TF-IDF concepts to papers that have no concepts.
    Papers with existing concepts (e.g. arXiv categories) are skipped.

    Args:
        papers: list of paper dicts (modified in place)
        overwrite: if True, re-extract even if concepts already exist

    Returns:
        Number of papers tagged
    """
    to_tag = [
        (i, p) for i, p in enumerate(papers)
        if overwrite or not p.get("concepts")
    ]
    if not to_tag:
        return 0

    texts = [
        f"{p.get('title', '')} {p.get('abstract', '')}".strip()
        for _, p in to_tag
    ]
    all_concepts = extract_concepts_tfidf(texts)

    for (i, paper), concepts in zip(to_tag, all_concepts):
        papers[i]["concepts"] = concepts

    return len(to_tag)
