"""
src/ai/service.py

Unified AI service for HireIQ.

Responsibilities
----------------
- Single entrypoint for all AI features.
- Route requests to the appropriate prompt.
- Reuse retrieval, formatter and client.
"""

from __future__ import annotations

from src.ai.base import AIBase
from src.ai.prompts import (
    SYSTEM_PROMPT,
    COPILOT_SYSTEM_PROMPT,
    CANDIDATE_MEMO_PROMPT,
    COMPARISON_PROMPT,
    INTERVIEW_GUIDE_PROMPT,
)

from src.ai.retrieval import get_complete_context


class AIService(AIBase):

    def __init__(self):
        super().__init__()

    def generate(
        self,
        task: str,
        candidate_id: str | None = None,
        question: str | None = None,
        scenario: str | None = None,
        extra_context: str | None = None,
    ) -> str:

        context = self._get_context(candidate_id) if candidate_id else {}

        if task != "copilot" and (not candidate_id or context.get("candidate_profile") is None):
            return "Candidate not found."

        if task == "copilot":
            candidate_block = ""
            if candidate_id and context.get("candidate_profile"):
                candidate_block = self._format_context(candidate_id)

            ec = extra_context.strip() if extra_context else ""

            prompt = f"""
{ec}

{candidate_block}

Recruiter Question

{question}

Answer only using the supplied context. If the question is about the candidate pool as a whole, use the run statistics above.
"""

            system = (
                SYSTEM_PROMPT
                + "\n\n"
                + COPILOT_SYSTEM_PROMPT
            )

        elif task == "memo":
            formatted = self._format_context(candidate_id)

            prompt = f"""
{formatted}

Generate a recruiter memo.
"""

            system = (
                SYSTEM_PROMPT
                + "\n\n"
                + CANDIDATE_MEMO_PROMPT
            )

        elif task == "interview":
            formatted = self._format_context(candidate_id)

            prompt = f"""
{formatted}

Generate an interview guide.
"""

            system = (
                SYSTEM_PROMPT
                + "\n\n"
                + INTERVIEW_GUIDE_PROMPT
            )

        elif task == "simulation":
            candidate = context.get("candidate_profile") or {}
            match = context.get("match_score") or {}
            decision = context.get("recruiter_decision") or {}
            job = context.get("job_intelligence") or {}

            prompt = f"""
Candidate
---------
Name: {candidate.get("name", "N/A")}
Current Title: {candidate.get("current_title", "N/A")}
Company: {candidate.get("current_company", "N/A")}

Current Recommendation
----------------------
Recommendation: {decision.get("recommendation", "N/A")}
Match Score: {match.get("overall_match_score", "N/A")}
Top Evidence: {", ".join((decision.get("top_evidence", []) or [])[:2]) or "N/A"}
Notice Period: {decision.get("timing_assessment", {}).get("estimated_notice_weeks", "N/A")} weeks

Role
----
{job.get("role_summary", "N/A")}

Scenario

{scenario}

Assume only this scenario changes. Keep the response to 3 short bullets max.

Would your recommendation change?
Why?
"""

            system = SYSTEM_PROMPT

        else:
            raise ValueError(f"Unknown task: {task}")

        return self.client.generate(
            system_prompt=system,
            user_prompt=prompt,
        )
    

    def compare(
        self,
        candidate_a: str,
        candidate_b: str,
    ) -> str:
        """
        Compare two match-scored candidates.
        """

        context_a = get_complete_context(candidate_a)
        context_b = get_complete_context(candidate_b)

        if (
            context_a["match_score"] is None
            or context_b["match_score"] is None
        ):
            return (
                "Comparison unavailable. One or both candidates "
                "have not completed match scoring."
            )

        formatted_a = self._format_context(candidate_a)
        formatted_b = self._format_context(candidate_b)

        prompt = f"""
    Candidate A
    ===========

    {formatted_a}

    Candidate B
    ===========

    {formatted_b}

    Compare the two candidates.

    Include:

    - Technical strengths
    - Technical weaknesses
    - Skill gaps
    - Hiring risks
    - Match quality
    - Interview priority
    - Final hiring recommendation

    Use only the supplied evidence.
    """

        return self.client.generate(
            system_prompt=(
                SYSTEM_PROMPT
                + "\n\n"
                + COMPARISON_PROMPT
            ),
            user_prompt=prompt,
        )
