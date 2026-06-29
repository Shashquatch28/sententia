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