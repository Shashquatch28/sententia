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
        candidate_id: str,
        question: str | None = None,
        scenario: str | None = None,
    ) -> str:

        context = self._get_context(candidate_id)

        if context["candidate_profile"] is None:
            return "Candidate not found."

        formatted = self._format_context(candidate_id)

        if task == "copilot":

            prompt = f"""
{formatted}

Recruiter Question

{question}

Answer only using the supplied context.
"""

            system = (
                SYSTEM_PROMPT
                + "\n\n"
                + COPILOT_SYSTEM_PROMPT
            )

        elif task == "memo":

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

            prompt = f"""
{formatted}

Scenario

{scenario}

Assume only this scenario changes.

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