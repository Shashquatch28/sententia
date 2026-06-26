from __future__ import annotations

from typing import Any


PROFICIENCY_WEIGHTS = {
    "beginner": 0.25,
    "intermediate": 0.50,
    "advanced": 0.80,
    "expert": 1.00
}

TIER_SCORES = {
    "tier_1": 1.00,
    "tier_2": 0.75,
    "tier_3": 0.50,
    "tier_4": 0.25,
    "unknown": 0.35
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def text(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def contains_any(haystack: str, needles: list[str] | tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def candidate_text(candidate: dict[str, Any]) -> str:
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_company", "")
    ]
    for job in candidate.get("career_history", []) or []:
        parts.extend([job.get("title", ""), job.get("company", ""), job.get("description", "")])
    return text(" ".join(str(p) for p in parts if p))
