# search.py
from typing import List, Dict, Any

from rapidfuzz import fuzz

from storage import fetch_all_images


def search_best_match(conn, query: str, limit: int = 1) -> List[Dict[str, Any]]:
    """
    Return up to `limit` best-matching image rows based on index_text.

    If score < 50, we drop the match (garbage filter).
    """
    rows = list(fetch_all_images(conn))
    if not rows:
        return []

    scored = []
    for row in rows:
        index_text = row.get("index_text") or ""
        score = fuzz.token_sort_ratio(query, index_text)
        scored.append((score, row))

    # sort by similarity descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # threshold
    filtered = [row for score, row in scored if score >= 50]

    return filtered[:limit]

