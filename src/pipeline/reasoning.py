from __future__ import annotations

from typing import Any

from src.models.feature_vector import CandidateFeatureVector


def fallback_reasoning(
    candidate: dict[str, Any],
    features: CandidateFeatureVector,
    rank: int,
) -> str:
    """
    Runtime fallback.

    This should only be used when reasoning_map.json does not contain
    an entry for a candidate.

    The structure intentionally mirrors Agent 5 so that runtime and
    offline reasoning stay consistent.
    """

    profile = candidate.get("profile", {}) or {}

    name = (
        profile.get("anonymized_name")
        or profile.get("name")
        or "Candidate"
    )

    title = profile.get("current_title") or "Unknown Title"
    company = profile.get("current_company") or "Unknown Company"

    score = int(features.final_score * 100)

    skills = features.top_matching_skills[:2]
    skill_summary = ", ".join(skills) if skills else "relevant AI/ML skills"

    evidence = _career_evidence(features)
    concern = _primary_concern(features)

    if features.disqualifier_triggered:
        return (
            f"{name} ({title} at {company}, {score}/100) demonstrates "
            f"{skill_summary}; however {features.disqualifier_triggered.replace('_', ' ')} "
            f"limits confidence. Primary follow-up: {concern}."
        )

    return (
        f"{name} ({title} at {company}, {score}/100) demonstrates "
        f"{skill_summary}; {evidence}. Primary interview focus: {concern}."
    )


def generate_reasoning_string(
    decision: dict[str, Any],
    profile: dict[str, Any],
    rank: int,
) -> str:
    """
    Canonical offline reasoning generator used by Agent 5.

    This is the primary implementation. `fallback_reasoning()` remains only
    as an emergency runtime fallback when the precomputed map is missing.
    """

    cid = decision.get("candidate_id", "unknown")
    name = decision.get("name") or profile.get("name", cid)
    title = decision.get("current_title") or profile.get("current_title", "unknown role")
    company = decision.get("current_company") or profile.get("current_company", "unknown company")
    rec = decision.get("recommendation", "REVIEW_FURTHER")
    score = int(float(decision.get("overall_match_score", 0)) * 100)
    skills = profile.get("top_skills", []) or []
    matched = decision.get("required_skills_matched", []) or []
    evidence_list = decision.get("top_evidence", []) or []
    yoe = float(profile.get("years_of_experience", 0) or 0)

    fit = decision.get("fit_assessment", {}) or {}
    tech_gaps = (fit.get("technical", {}) or {}).get("gaps", []) or []
    prod_gaps = (fit.get("product", {}) or {}).get("gaps", []) or []
    all_gaps = list(dict.fromkeys(tech_gaps + prod_gaps + (decision.get("identified_gaps", []) or [])))

    risks = decision.get("hiring_risks", []) or []
    blocking_risks = [r for r in risks if r.get("is_blocking")]
    top_risk_desc = (
        blocking_risks[0].get("description")
        if blocking_risks
        else (risks[0].get("description") if risks else None)
    )

    primary_skill = matched[0] if matched else (skills[0] if skills else "ML background")
    secondary_skill = matched[1] if len(matched) > 1 else (skills[1] if len(skills) > 1 else "")
    skill_summary = f"{primary_skill} and {secondary_skill}" if secondary_skill else primary_skill
    tech_evidence = evidence_list[0] if evidence_list else f"{primary_skill} background at {company}"
    prod_outcome = evidence_list[1] if len(evidence_list) > 1 else (
        f"product-company context ({title})" if company else "product exposure"
    )
    gap = all_gaps[0] if all_gaps else None
    variant = abs(hash(cid)) % 3

    if rec == "STRONGLY_ADVANCE":
        concern = f"Watch: {top_risk_desc}." if top_risk_desc else "No blocking concerns identified."
        if variant == 0:
            return (
                f"{name} ({title} at {company}, {score}/100) — {tech_evidence}; "
                f"{prod_outcome}. {concern}"
            )
        if variant == 1:
            return (
                f"Strong hire at {score}/100. {name} brings {skill_summary} with demonstrated "
                f"product-company depth ({company}). {prod_outcome}. {concern} "
                f"Recommend immediate technical screen."
            )
        return (
            f"{score}/100 match — {name}'s {yoe:.0f}-year career ({title}, {company}) directly "
            f"addresses LLM/RAG requirements via {skill_summary}. {prod_outcome}. {concern}"
        )

    if rec == "ADVANCE":
        gap_note = f"gap to probe: {gap}" if gap else "no critical gaps identified"
        if variant == 0:
            return (
                f"{name} ({title} at {company}, {score}/100) — {tech_evidence}; "
                f"{gap_note}. Advancing for technical screen."
            )
        if variant == 1:
            return (
                f"Advance to phone screen. {name} ({company}) scores {score}/100 — "
                f"{skill_summary} aligns with role. Key check: {gap_note}."
            )
        return (
            f"{name} ({title}, {score}/100) — {tech_evidence}. {gap_note.capitalize()}. "
            f"Profile is strong enough for a technical screen; verify depth in LLM/RAG ownership."
        )

    if rec == "REVIEW_FURTHER":
        gap_note = gap if gap else "full role alignment"
        if variant == 0:
            return (
                f"{name} ({title} at {company}, {score}/100) — adjacent fit via {primary_skill}; "
                f"gap in {gap_note}. Review if top candidates are unavailable."
            )
        return (
            f"{name} ({title}, {company}) has adjacent ML skills ({primary_skill}) but "
            f"{gap_note} is unverified at {score}/100. Borderline — include only if pipeline is thin."
        )

    if rec == "ADVANCE_IF_POOL_THIN":
        gap_note = gap if gap else "multiple gaps present"
        if variant == 0:
            return (
                f"{name} ({title} at {company}, {score}/100) — below primary threshold — "
                f"{gap_note}. Included as rank-{rank} given {tech_evidence}."
            )
        return (
            f"Rank {rank} at {score}/100. {name} ({title}, {company}) falls below our primary "
            f"bar — {gap_note}. Advance only if stronger candidates decline or are unavailable."
        )

    if rec == "DECLINE":
        reason = top_risk_desc or gap or "does not meet minimum requirements for this role"
        if variant == 0:
            return f"{name} ({title} at {company}, {score}/100) — not recommended. {reason}."
        return (
            f"Do not advance. {name} ({title}, {company}) scores {score}/100 — "
            f"{reason}. Falls below the minimum bar for Senior AI Engineer."
        )

    return (
        f"{name} ({title} at {company}, {score}/100) — {tech_evidence}. "
        f"{rec.replace('_', ' ').title()}."
    )


def _career_evidence(features: CandidateFeatureVector) -> str:
    if features.production_evidence_count > 0:
        return (
            f"{features.production_evidence_count} production role(s) "
            "show deployment or retrieval experience"
        )

    if features.ai_fraction >= 0.50:
        return "career history is strongly AI/ML focused"

    if features.product_fraction >= 0.50:
        return "strong product-company experience complements technical profile"

    return "career progression suggests relevant transferable experience"


def _primary_concern(features: CandidateFeatureVector) -> str:
    if features.missing_core_skills:
        return "verify " + ", ".join(features.missing_core_skills[:2])

    if features.risk_flags:
        return features.risk_flags[0]

    return "confirm production-scale retrieval and ranking ownership"
