from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.scoring.common import contains_any, text


@dataclass(slots=True)
class HardRuleResult:
    triggered_rule: str | None = None
    score_cap: float | None = None


def apply_hard_rules(candidate: dict[str, Any], jd: dict[str, Any]) -> HardRuleResult:
    profile = candidate.get("profile", {}) or {}
    current_title = text(profile.get("current_title"))
    if contains_any(current_title, jd.get("disqualifier_titles", [])):
        return HardRuleResult("disqualified_title", 0.05)

    history = candidate.get("career_history", []) or []
    total_months = sum(max(0, int(job.get("duration_months") or 0)) for job in history)
    if total_months:
        consulting_months = 0
        for job in history:
            company = text(job.get("company"))
            if contains_any(company, jd.get("disqualifier_companies", [])):
                consulting_months += max(0, int(job.get("duration_months") or 0))
        if consulting_months / total_months > 0.95:
            return HardRuleResult("consulting_only", 0.10)

    return HardRuleResult()
