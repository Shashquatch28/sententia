from __future__ import annotations

from typing import Any

from src.scoring.common import clamp, contains_any, text


def score_title_role(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, list[str]]:
    profile = candidate.get("profile", {})
    current_title = text(profile.get("current_title", ""))
    history_titles = [text(job.get("title", "")) for job in candidate.get("career_history", []) or []]
    all_titles = [current_title, *history_titles]
    risks: list[str] = []

    if contains_any(current_title, jd.get("disqualifier_titles", [])):
        return 0.05, ["current title is outside target AI/engineering roles"]

    strong_titles = jd.get("strong_ai_titles", [])
    medium_titles = jd.get("medium_titles", [])

    if contains_any(current_title, strong_titles):
        score = 1.0
    elif contains_any(current_title, medium_titles):
        score = 0.45
    else:
        score = 0.20
        risks.append("current title has weak direct AI/ML alignment")

    if score < 1.0 and any(contains_any(title, strong_titles) for title in history_titles):
        score = max(score, 0.75)
    elif score < 0.75 and any(contains_any(title, medium_titles) for title in all_titles):
        score = max(score, 0.45)

    return clamp(score), risks
