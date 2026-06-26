from __future__ import annotations

from typing import Any

from src.models.feature_vector import CandidateFeatureVector


def fallback_reasoning(candidate: dict[str, Any], features: CandidateFeatureVector, rank: int) -> str:
    profile = candidate.get("profile", {}) or {}
    title = profile.get("current_title") or "Candidate"
    company = profile.get("current_company") or "current company"
    skills = ", ".join(features.top_matching_skills[:2]) if features.top_matching_skills else "relevant ML signals"
    strongest_gap = _strongest_gap(features)
    evidence = _career_evidence(features)

    if features.disqualifier_triggered:
        return (
            f"{title} at {company} has some signal in {skills}, but {features.disqualifier_triggered.replace('_', ' ')} caps confidence. "
            f"Rank {rank} is driven by {strongest_gap}."
        )
    return (
        f"{title} at {company} matches on {skills}; {evidence}. "
        f"Primary screen: {strongest_gap}."
    )


def _career_evidence(features: CandidateFeatureVector) -> str:
    if features.production_evidence_count:
        return f"{features.production_evidence_count} role(s) show production ranking/retrieval evidence"
    if features.ai_fraction >= 0.5:
        return "career history is substantially AI/ML aligned"
    if features.product_fraction >= 0.5:
        return "product-company background helps offset weaker direct AI depth"
    return "career evidence is thinner than the strongest candidates"


def _strongest_gap(features: CandidateFeatureVector) -> str:
    if features.missing_core_skills:
        return "verify " + ", ".join(features.missing_core_skills[:2])
    if features.risk_flags:
        return features.risk_flags[0]
    return "confirm depth of shipped retrieval/ranking ownership"
