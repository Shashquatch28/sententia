"""
src/ai/formatter.py

Formats retrieved data into compact LLM-ready context.

Responsibilities
----------------
- Convert retrieval output into readable text.
- Reduce token usage.
- Keep formatting separate from prompts and retrieval.
"""

from __future__ import annotations


def format_candidate_context(context: dict) -> str:

    candidate = context["candidate_profile"]
    match = context["match_score"]
    decision = context["recruiter_decision"]

    if candidate is None:
        return "Candidate not found."

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

Decision
--------
Recommendation: {decision["recommendation"]}
"""