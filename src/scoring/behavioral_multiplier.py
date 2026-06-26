from __future__ import annotations

from datetime import date
from typing import Any

from src.scoring.common import clamp


def _days_since(date_string: str | None, today: date) -> int | None:
    if not date_string:
        return None
    try:
        return (today - date.fromisoformat(date_string)).days
    except ValueError:
        return None


def behavioral_multiplier(candidate: dict[str, Any], today: date | None = None) -> tuple[float, list[str]]:
    today = today or date.today()
    signals = candidate.get("redrob_signals", {}) or {}
    risks: list[str] = []

    days_inactive = _days_since(signals.get("last_active_date"), today)
    if days_inactive is None:
        recency = 0.45
        risks.append("missing recent activity signal")
    elif days_inactive <= 30:
        recency = 1.0
    elif days_inactive <= 90:
        recency = 0.75
    elif days_inactive <= 180:
        recency = 0.45
        risks.append("not recently active")
    else:
        recency = 0.20
        risks.append("stale platform activity")

    response = clamp(float(signals.get("recruiter_response_rate") or 0.0))
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.65
    github_raw = float(signals.get("github_activity_score", -1))
    github = 0.55 if github_raw < 0 else 0.50 + 0.50 * clamp(github_raw / 100.0)
    icr = clamp(float(signals.get("interview_completion_rate") or 0.0))
    offer_rate = float(signals.get("offer_acceptance_rate", -1))
    offer = 1.0
    if 0 <= offer_rate < 0.40:
        offer = 0.85
        risks.append("historically low offer acceptance")

    engagement = (
        0.30 * recency +
        0.25 * response +
        0.20 * open_to_work +
        0.15 * github +
        0.10 * icr
    ) * offer
    multiplier = 0.20 + engagement
    return clamp(multiplier, 0.20, 1.20), risks
