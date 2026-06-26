from __future__ import annotations

from typing import Any


def score_experience_depth(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, list[str]]:
    yoe = float(candidate.get("profile", {}).get("years_of_experience") or 0)
    exp = jd.get("experience_range", {})
    ideal_min = float(exp.get("ideal_min", 6))
    ideal_max = float(exp.get("ideal_max", 8))
    minimum = float(exp.get("min", 5))
    maximum = float(exp.get("max", 9))
    risks: list[str] = []

    if ideal_min <= yoe <= ideal_max:
        return 1.0, risks
    if minimum <= yoe < ideal_min or ideal_max < yoe <= maximum:
        return 0.85, risks
    if 4 <= yoe < minimum or maximum < yoe <= 12:
        risks.append("experience is outside the ideal 6-8 year band")
        return 0.65, risks
    if yoe < 4:
        risks.append("experience may be shallow for the senior applied AI role")
        return 0.35, risks
    risks.append("very senior profile may be less hands-on for this role")
    return 0.70, risks
