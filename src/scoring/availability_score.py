from __future__ import annotations

from typing import Any


def score_availability(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, list[str]]:
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {}) or {}
    location = str(profile.get("location", "")).lower()
    country = str(profile.get("country", "")).lower()
    relocate = bool(signals.get("willing_to_relocate", False))
    preferred_locs = jd.get("preferred_locations", [])
    preferred_countries = jd.get("preferred_countries", ["india"])
    risks: list[str] = []

    if any(loc in location for loc in preferred_locs):
        location_score = 1.0
    elif country in preferred_countries and relocate:
        location_score = 0.80
    elif country in preferred_countries:
        location_score = 0.55
        risks.append("not in a preferred city and relocation is unclear")
    else:
        location_score = 0.30 if relocate else 0.10
        risks.append("outside preferred India hiring locations")

    notice = int(signals.get("notice_period_days") or 90)
    if notice <= jd.get("preferred_notice_days", 30):
        notice_score = 1.0
    elif notice <= 60:
        notice_score = 0.70
        risks.append("60 day notice period")
    elif notice <= 90:
        notice_score = 0.50
        risks.append("long notice period")
    else:
        notice_score = 0.25
        risks.append("notice period is above 90 days")

    work_mode = str(signals.get("preferred_work_mode") or "flexible").lower()
    work_mode_score = {"flexible": 1.0, "hybrid": 0.90, "onsite": 0.85, "remote": 0.60}.get(work_mode, 0.75)
    if work_mode == "remote":
        risks.append("remote preference may need alignment")

    return 0.50 * location_score + 0.30 * notice_score + 0.20 * work_mode_score, risks
