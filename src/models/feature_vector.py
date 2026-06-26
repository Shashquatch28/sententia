from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CandidateFeatureVector:
    candidate_id: str

    title_role_score: float
    skill_match_score: float
    career_progression_score: float
    experience_depth_score: float
    education_score: float
    availability_score: float
    behavioral_multiplier: float

    is_honeypot: bool = False
    honeypot_flags: list[str] = field(default_factory=list)
    disqualifier_triggered: str | None = None
    score_cap: float | None = None
    final_score: float = 0.0

    top_matching_skills: list[str] = field(default_factory=list)
    missing_core_skills: list[str] = field(default_factory=list)
    career_highlight: str = ""
    risk_flags: list[str] = field(default_factory=list)

    ai_fraction: float = 0.0
    product_fraction: float = 0.0
    production_evidence_count: int = 0
