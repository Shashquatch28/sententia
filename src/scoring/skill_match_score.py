from __future__ import annotations

import math
from typing import Any

from src.scoring.common import PROFICIENCY_WEIGHTS, candidate_text, clamp, text


def skill_trust(skill: dict[str, Any]) -> float:
    prof_w = PROFICIENCY_WEIGHTS.get(text(skill.get("proficiency")), 0.25)
    endorsements = max(0, int(skill.get("endorsements") or 0))
    duration = max(0, int(skill.get("duration_months") or 0))
    endorsement_factor = min(1.0, math.log1p(endorsements) / math.log1p(50))
    duration_factor = math.sqrt(min(duration, 60)) / math.sqrt(60)
    return clamp(prof_w * (0.4 + 0.3 * endorsement_factor + 0.3 * duration_factor))


def _skill_names(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {text(skill.get("name")): skill for skill in candidate.get("skills", []) or []}


def score_skill_match(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, list[str], list[str], list[str]]:
    skills_by_name = _skill_names(candidate)
    full_text = candidate_text(candidate)
    assessments = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {}) or {}
    assessments_by_name = {text(k): float(v) for k, v in assessments.items()}
    required = jd.get("required_skill_aliases", {})
    top_matches: list[tuple[float, str]] = []
    missing: list[str] = []
    total = 0.0

    for req_skill, aliases in required.items():
        best = 0.0
        best_label = ""
        for alias in aliases:
            alias_l = text(alias)
            skill = skills_by_name.get(alias_l)
            if skill:
                trust = skill_trust(skill)
                assessment = assessments_by_name.get(text(skill.get("name")))
                if assessment is not None:
                    trust = trust * 0.6 + clamp(assessment / 100.0) * 0.4
                if trust > best:
                    best = trust
                    best_label = str(skill.get("name", alias))
            elif alias_l and alias_l in full_text:
                if best < 0.25:
                    best = 0.25
                    best_label = alias
        if best <= 0.05:
            missing.append(req_skill)
        else:
            top_matches.append((best, best_label or req_skill))
        total += best

    nice_bonus = 0.0
    for nice in jd.get("nice_to_have_skills", []):
        nice_l = text(nice)
        if nice_l in skills_by_name or nice_l in full_text:
            nice_bonus += 0.015

    denom = max(1, len(required))
    score = clamp(total / denom + min(nice_bonus, 0.10))
    top_matching_skills = [label for _, label in sorted(top_matches, reverse=True)[:5]]
    risks = []
    if missing:
        risks.append("missing or weak evidence for " + ", ".join(missing[:3]))
    return score, top_matching_skills, missing, risks
