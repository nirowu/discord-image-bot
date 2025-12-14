# search.py
from typing import List, Dict, Any
from rapidfuzz import fuzz
from storage import fetch_all_images

MIN_SCORE = 50  # Minimum score to consider a match

def search_best_match(conn, query: str, limit: int = 1) -> List[Dict[str, Any]]:
    rows = list(fetch_all_images(conn))
    if not rows:
        return []

    scored = []
    for row in rows:
        text = row.get("index_text") or ""
        if not text:
            continue

        score1 = fuzz.partial_ratio(query, text)
        score2 = fuzz.WRatio(query, text)
        score = max(score1, score2)

        if score >= MIN_SCORE:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:limit]]
