"""
src/ai/copilot.py

Recruiter Copilot orchestration.

Responsibilities
----------------
- Accept recruiter questions.
- Retrieve relevant candidate context.
- Build prompts.
- Invoke the configured LLM.
- Return recruiter-ready answers.

No database queries.
No prompt definitions.
No provider-specific code.
"""

from __future__ import annotations

from src.ai.client import get_client
from src.ai.prompts import (
    SYSTEM_PROMPT,
    COPILOT_SYSTEM_PROMPT,
)

from src.ai.retrieval import (
    get_complete_context,
)


from src.ai.base import AIBase

class RecruiterCopilot(AIBase):
    """
    Main AI entrypoint.
    """

    def __init__(self):
        super().__init__()

    def answer_candidate_question(
        self,
        candidate_id: str,
        question: str,
    ) -> str:
        """
        Answer a recruiter question about one candidate.
        """

        context = self._get_context(candidate_id)

        from src.ai.formatter import format_candidate_context

        formatted_context = self._format_context(candidate_id)

        if (
            context["candidate_profile"] is None
            or context["recruiter_decision"] is None
        ):
            return "Candidate not found."

        user_prompt = f"""
Candidate Context
=================

{formatted_context}

Recruiter Question
==================

{question}

Instructions
============

Answer using ONLY the supplied context.

Do not invent facts.

Be concise and recruiter-focused.
"""

        system_prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + COPILOT_SYSTEM_PROMPT
        )

        return self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )