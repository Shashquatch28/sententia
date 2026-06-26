"""
CSV Reasoning — generate_csv_reasoning()
Generates one candidate-specific reasoning string per decision using branching
string templates injected with the candidate's actual data (name, title, company,
skills, gaps). No LLM calls.

"CSV" = Candidate-Specific Value reasoning.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _build_candidate_context(decision: dict, profile: dict) -> dict:
    cid = decision["candidate_id"]
    fit = decision.get("fit_assessment", {})
    return {
        "candidate_id": cid,
        "name": decision.get("name") or profile.get("name", cid),
        "title": decision.get("current_title") or profile.get("current_title", ""),
        "company": decision.get("current_company") or profile.get("current_company", ""),
        "recommendation": decision.get("recommendation", ""),
        "match_score_pct": round(decision.get("overall_match_score", 0) * 100),
        "years_experience": profile.get("years_of_experience", 0),
        "top_skills": profile.get("top_skills", [])[:5],
        "required_skills_matched": decision.get("required_skills_matched", [])[:3],
        "top_evidence": decision.get("top_evidence", [])[:2],
        "technical_score": fit.get("technical", {}).get("score", 0) if isinstance(fit.get("technical"), dict) else 0,
        "product_score": fit.get("product", {}).get("score", 0) if isinstance(fit.get("product"), dict) else 0,
        "primary_gap": (
            (fit.get("technical", {}).get("gaps") or fit.get("product", {}).get("gaps") or [""])
            if isinstance(fit.get("technical"), dict) else [""]
        )[:1],
        "narrative_type": profile.get("narrative_type", ""),
        "green_flags": profile.get("green_flags", [])[:1],
        "hiring_risks": decision.get("hiring_risks", []),
    }


def _reasoning_string(ctx: dict, rank: int = 0) -> str:
    """
    Branching template per recommendation, injected with candidate-specific data.
    Matches spec format:
      STRONGLY_ADVANCE : {tech_evidence}; {product_outcome}. Concern: {risk or 'none'}.
      ADVANCE          : {tech_evidence}; gap: {gap or '-'}. Advancing for technical screen.
      REVIEW_FURTHER   : Adjacent fit via {evidence}; gap in {gap}. Review if top candidates unavailable.
      ADVANCE_IF_POOL_THIN: Below primary threshold — {gap}. Included as rank-{rank} given {evidence}.
      DECLINE          : Not recommended. {blocking_risk}.
    """
    name = ctx["name"]
    title = ctx["title"]
    company = ctx["company"]
    rec = ctx["recommendation"]
    score = ctx["match_score_pct"]
    yoe = ctx["years_experience"]
    skills = ctx["top_skills"]
    matched = ctx["required_skills_matched"]
    evidence_list = ctx["top_evidence"]
    gap_list = ctx["primary_gap"]
    risks = ctx.get("hiring_risks", [])

    primary_skill = matched[0] if matched else (skills[0] if skills else "technical background")
    tech_evidence = evidence_list[0] if evidence_list else f"{primary_skill} background"
    prod_outcome = evidence_list[1] if len(evidence_list) > 1 else f"experience at {company}"
    gap = gap_list[0] if gap_list and gap_list[0] else None
    blocking_risks = [r for r in risks if r.get("is_blocking")]
    top_risk = blocking_risks[0]["description"] if blocking_risks else (risks[0]["description"] if risks else None)

    label = f"{name} ({title} at {company}, {score}/100)"

    if rec == "STRONGLY_ADVANCE":
        concern = f"Concern: {top_risk}." if top_risk else "No blocking concerns."
        return f"{label} — {tech_evidence}; {prod_outcome}. {concern}"

    elif rec == "ADVANCE":
        gap_note = f"gap: {gap}" if gap else "no critical gaps"
        return f"{label} — {tech_evidence}; {gap_note}. Advancing for technical screen."

    elif rec == "REVIEW_FURTHER":
        gap_note = gap if gap else "full role alignment"
        return f"{label} — adjacent fit via {primary_skill}; gap in {gap_note}. Review if top candidates unavailable."

    elif rec == "ADVANCE_IF_POOL_THIN":
        gap_note = gap if gap else "below threshold"
        rank_str = f"rank-{rank}" if rank else "backup"
        return f"{label} — below primary threshold — {gap_note}. Included as {rank_str} given {tech_evidence}."

    elif rec == "DECLINE":
        reason = top_risk or gap or "does not meet minimum requirements"
        return f"{label} — not recommended. {reason}."

    # Fallback
    return f"{label} — {tech_evidence}. {rec.replace('_', ' ').title()}."


def generate_csv_reasoning(
    decisions: list,
    profiles: dict,
    job_intel: Optional[dict] = None,
    client=None,
    use_llm: bool = False,
) -> dict:
    """
    Generate one unique candidate-specific reasoning string per decision.
    Uses branching templates — no LLM calls regardless of use_llm flag.

    Args:
        decisions: List of RecruiterDecision dicts (from recruiter_decisions/*.json)
        profiles: Dict mapping candidate_id -> CandidateIntelligenceProfile dict
        job_intel: Unused (kept for API compatibility)
        client: Unused (kept for API compatibility)
        use_llm: Ignored — always uses templates

    Returns:
        Dict mapping candidate_id -> reasoning string (all unique)
    """
    reasoning: dict = {}

    for rank, decision in enumerate(decisions, start=1):
        cid = decision["candidate_id"]
        profile = profiles.get(cid, {})
        ctx = _build_candidate_context(decision, profile)
        reasoning[cid] = _reasoning_string(ctx, rank)

    # Deduplicate
    seen: dict = {}
    dupes = []
    for cid, text in reasoning.items():
        if text in seen:
            dupes.append(cid)
        else:
            seen[text] = cid

    if dupes:
        logger.warning(f"Deduplicating {len(dupes)} reasoning strings")
        for idx, cid in enumerate(dupes):
            reasoning[cid] = reasoning[cid].rstrip(".") + f" (peer group candidate #{idx + 2})."

    return reasoning


def generate_csv_reasoning_from_files(
    precomputed_root: Optional[Path] = None,
    use_llm: bool = False,
) -> dict:
    """Convenience wrapper that loads all required files automatically."""
    root = precomputed_root or Path(__file__).resolve().parents[4] / "precomputed"

    decisions = []
    for path in (root / "recruiter_decisions").glob("*.json"):
        with open(path, encoding="utf-8") as f:
            decisions.append(json.load(f))

    profiles: dict = {}
    for path in (root / "candidate_profiles").glob("*.json"):
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
            profiles[p["candidate_id"]] = p

    return generate_csv_reasoning(decisions, profiles)
