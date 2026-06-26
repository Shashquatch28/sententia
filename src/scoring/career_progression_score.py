from __future__ import annotations

from typing import Any

from src.scoring.common import clamp, contains_any, text


AI_TITLE_KEYWORDS = (
    "ml",
    "machine learning",
    "nlp",
    "search",
    "recommendation",
    "ai ",
    "applied scientist",
    "data scientist"
)


def career_metrics(candidate: dict[str, Any], jd: dict[str, Any]) -> dict[str, float | int | str]:
    history = candidate.get("career_history", []) or []
    consulting = jd.get("disqualifier_companies", [])
    production_signals = jd.get("career_keywords", {}).get("production_signals", [])
    positive_keywords = jd.get("career_keywords", {}).get("strong_positive", [])

    ai_months = 0
    product_months = 0
    consulting_months = 0
    production_evidence_count = 0
    best_highlight = ""

    for job in history:
        duration = max(0, int(job.get("duration_months") or 0))
        company = text(job.get("company"))
        title = text(job.get("title"))
        description = text(job.get("description"))
        combined = f"{title} {description}"

        if contains_any(combined, AI_TITLE_KEYWORDS) or contains_any(combined, positive_keywords):
            ai_months += duration
        if contains_any(company, consulting):
            consulting_months += duration
        else:
            product_months += duration
        if contains_any(description, production_signals):
            production_evidence_count += 1
            if not best_highlight:
                best_highlight = str(job.get("description", ""))[:220]

    total_months = sum(max(0, int(job.get("duration_months") or 0)) for job in history) or 1
    return {
        "ai_fraction": ai_months / total_months,
        "product_fraction": product_months / total_months,
        "consulting_fraction": consulting_months / total_months,
        "production_evidence_count": production_evidence_count,
        "production_fraction": production_evidence_count / max(1, len(history)),
        "career_highlight": best_highlight
    }


def score_career_progression(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, dict[str, float | int | str], list[str]]:
    metrics = career_metrics(candidate, jd)
    consulting_fraction = float(metrics["consulting_fraction"])
    risks: list[str] = []
    if consulting_fraction >= 0.95:
        return 0.10, metrics, ["career is almost entirely in consulting/IT services companies"]

    score = (
        0.40 * float(metrics["ai_fraction"]) +
        0.35 * (1 - min(consulting_fraction, 0.6) / 0.6) +
        0.25 * float(metrics["production_fraction"])
    )
    if float(metrics["ai_fraction"]) < 0.25:
        risks.append("limited sustained AI/ML career trajectory")
    if int(metrics["production_evidence_count"]) == 0:
        risks.append("limited production deployment evidence")
    return clamp(score), metrics, risks
