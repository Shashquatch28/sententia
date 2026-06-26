from __future__ import annotations

from typing import Any

from src.scoring.common import TIER_SCORES, text


CS_FIELDS = (
    "computer science",
    "computer engineering",
    "artificial intelligence",
    "machine learning",
    "data science",
    "information technology",
    "mathematics",
    "statistics"
)


def score_education(candidate: dict[str, Any]) -> float:
    education = candidate.get("education", []) or []
    if not education:
        return 0.30
    best = 0.0
    for edu in education:
        tier_score = TIER_SCORES.get(text(edu.get("tier")) or "unknown", 0.35)
        field = text(edu.get("field_of_study"))
        field_score = 0.70 if any(name in field for name in CS_FIELDS) else 0.30
        best = max(best, tier_score * 0.6 + field_score * 0.4)
    return best
