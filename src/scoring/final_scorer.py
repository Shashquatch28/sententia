from __future__ import annotations

from typing import Any

from src.hard_rules import apply_hard_rules
from src.honeypot import detect_honeypot
from src.models.feature_vector import CandidateFeatureVector
from src.scoring.availability_score import score_availability
from src.scoring.behavioral_multiplier import behavioral_multiplier
from src.scoring.career_progression_score import score_career_progression
from src.scoring.education_score import score_education
from src.scoring.experience_depth_score import score_experience_depth
from src.scoring.skill_match_score import score_skill_match
from src.scoring.title_role_score import score_title_role
from src.scoring.semantic_score import semantic_score


WEIGHTS = {
    "title_role_score": 0.15,
    "skill_match_score": 0.30,
    "career_progression_score": 0.25,
    "experience_depth_score": 0.10,
    "education_score": 0.05,
    "availability_score": 0.15
}


def score_candidate(candidate: dict[str, Any], jd: dict[str, Any]) -> CandidateFeatureVector:
    candidate_id = str(candidate.get("candidate_id", ""))
    is_honeypot, honeypot_flags = detect_honeypot(candidate)
    if is_honeypot:
        return CandidateFeatureVector(
            candidate_id=candidate_id,
            title_role_score=0.0,
            skill_match_score=0.0,
            career_progression_score=0.0,
            experience_depth_score=0.0,
            education_score=0.0,
            availability_score=0.0,
            behavioral_multiplier=0.2,
            is_honeypot=True,
            honeypot_flags=honeypot_flags,
            final_score=0.0,
            risk_flags=honeypot_flags
        )

    title_score, title_risks = score_title_role(candidate, jd)

    keyword_skill_score, top_skills, missing_skills, skill_risks = score_skill_match(candidate, jd)

    semantic = semantic_score(candidate_id)

    skill_score = (
        0.90 * keyword_skill_score +
        0.10 * semantic
    )
    career_score, career_metrics, career_risks = score_career_progression(candidate, jd)
    exp_score, exp_risks = score_experience_depth(candidate, jd)
    edu_score = score_education(candidate)
    availability, availability_risks = score_availability(candidate, jd)
    multiplier, behavioral_risks = behavioral_multiplier(candidate)
    hard_rule = apply_hard_rules(candidate, jd)

    base_score = (
        WEIGHTS["title_role_score"] * title_score +
        WEIGHTS["skill_match_score"] * skill_score +
        WEIGHTS["career_progression_score"] * career_score +
        WEIGHTS["experience_depth_score"] * exp_score +
        WEIGHTS["education_score"] * edu_score +
        WEIGHTS["availability_score"] * availability
    )
    final_score = min(base_score * multiplier, 1.0)
    if hard_rule.score_cap is not None:
        final_score = min(final_score, hard_rule.score_cap)

    risks = [
        *title_risks,
        *skill_risks,
        *career_risks,
        *exp_risks,
        *availability_risks,
        *behavioral_risks
    ]

    return CandidateFeatureVector(
        candidate_id=candidate_id,
        title_role_score=title_score,
        skill_match_score=skill_score,
        career_progression_score=career_score,
        experience_depth_score=exp_score,
        education_score=edu_score,
        availability_score=availability,
        behavioral_multiplier=multiplier,
        is_honeypot=False,
        honeypot_flags=[],
        disqualifier_triggered=hard_rule.triggered_rule,
        score_cap=hard_rule.score_cap,
        final_score=final_score,
        top_matching_skills=top_skills,
        missing_core_skills=missing_skills,
        career_highlight=str(career_metrics.get("career_highlight") or ""),
        risk_flags=risks,
        ai_fraction=float(career_metrics.get("ai_fraction") or 0.0),
        product_fraction=float(career_metrics.get("product_fraction") or 0.0),
        production_evidence_count=int(career_metrics.get("production_evidence_count") or 0)
    )
