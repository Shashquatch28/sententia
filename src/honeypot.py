from __future__ import annotations

from datetime import date
from typing import Any

from src.scoring.common import contains_any, text


AI_SKILL_TERMS = (
    "recommendation",
    "fine-tuning",
    "prompt engineering",
    "langchain",
    "pinecone",
    "vector search",
    "embeddings",
    "faiss",
    "llm",
    "rag"
)

NON_AI_TITLE_TERMS = (
    "project manager",
    "marketing manager",
    "sales",
    "customer support",
    "hr manager",
    "operations manager"
)


def detect_honeypot(candidate: dict[str, Any], today: date | None = None) -> tuple[bool, list[str]]:
    today = today or date.today()
    flags: list[str] = []
    skills = candidate.get("skills", []) or []
    profile = candidate.get("profile", {}) or {}
    history = candidate.get("career_history", []) or []
    education = candidate.get("education", []) or []

    if any(text(s.get("proficiency")) == "expert" and int(s.get("duration_months") or 0) < 6 for s in skills):
        flags.append("expert skill claimed with less than 6 months duration")
    if any(text(s.get("proficiency")) == "advanced" and int(s.get("duration_months") or 0) < 3 for s in skills):
        flags.append("advanced skill claimed with less than 3 months duration")

    zero_endorse_experts = [
        s for s in skills
        if text(s.get("proficiency")) == "expert" and int(s.get("endorsements") or 0) == 0
    ]
    if len(zero_endorse_experts) >= 3:
        flags.append("three or more expert skills have zero endorsements")

    ai_skill_claims = [
        s for s in skills
        if contains_any(text(s.get("name")), AI_SKILL_TERMS)
    ]
    low_trust_ai_claims = [
        s for s in ai_skill_claims
        if int(s.get("endorsements") or 0) <= 4 and int(s.get("duration_months") or 0) <= 18
    ]
    current_title = text(profile.get("current_title"))
    if contains_any(current_title, NON_AI_TITLE_TERMS) and len(ai_skill_claims) >= 5:
        flags.append("non-AI current title with dense AI keyword claims")
    if len(low_trust_ai_claims) >= 5:
        flags.append("multiple low-trust AI skill claims")

    total_history_months = sum(max(0, int(job.get("duration_months") or 0)) for job in history)
    claimed_yoe_months = float(profile.get("years_of_experience") or 0) * 12
    if claimed_yoe_months > 0 and total_history_months > claimed_yoe_months * 1.3:
        flags.append("career duration materially exceeds claimed years of experience")

    grad_years = [
        int(edu.get("end_year"))
        for edu in education
        if isinstance(edu.get("end_year"), int)
    ]
    if grad_years:
        earliest_grad = min(grad_years)
        max_possible_yoe = today.year - earliest_grad + 2
        if float(profile.get("years_of_experience") or 0) > max_possible_yoe:
            flags.append("claimed years of experience exceed graduation timeline")

    return len(flags) >= 2, flags
