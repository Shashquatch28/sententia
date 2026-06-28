"""
src/ai/formatter.py

Formats retrieved data into compact LLM-ready context.
"""

from __future__ import annotations

import json


def _parse(payload: str | None) -> dict:
    if not payload:
        return {}

    try:
        return json.loads(payload)
    except Exception:
        return {}


def format_candidate_context(context: dict) -> str:

    candidate = context["candidate_profile"]
    match = context["match_score"]
    decision = context["recruiter_decision"]

    if candidate is None:
        return "Candidate not found."

    candidate_payload = _parse(candidate.get("payload"))
    match_payload = _parse(match.get("payload"))
    decision_payload = _parse(decision.get("payload"))

    matched_skills = ", ".join(
        match_payload.get("required_skills_matched", [])[:5]
    ) or "None"

    gaps = ", ".join(
        match_payload.get("identified_gaps", [])[:5]
    ) or "None"

    evidence = "\n".join(
        f"- {e}"
        for e in match_payload.get("match_evidence", [])[:3]
    )

    rationale = decision_payload.get(
        "recommendation_rationale",
        "N/A",
    )

    interview_focus = "\n".join(
        f"- {q['question']}"
        for q in decision_payload.get(
            "interview_focus",
            []
        )[:2]
    )

    risks = "\n".join(
        f"- {r['description']}"
        for r in decision_payload.get(
            "hiring_risks",
            []
        )[:2]
    )

    return f"""
Candidate
---------
Name: {candidate["name"]}
Current Title: {candidate["current_title"]}
Company: {candidate["current_company"]}
Experience: {candidate["years_of_experience"]:.1f} years
Narrative: {candidate["narrative_type"]}

Match
-----
Overall Score: {match["overall_match_score"]:.3f}

Matched Skills:
{matched_skills}

Skill Gaps:
{gaps}

Top Evidence:
{evidence}

Recommendation
--------------
{decision["recommendation"]}

Rationale:
{rationale}

Hiring Risks:
{risks}

Interview Focus:
{interview_focus}
"""