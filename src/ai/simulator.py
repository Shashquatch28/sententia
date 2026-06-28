"""
src/ai/simulator.py

Hiring decision simulator.

Responsibilities
----------------
- Simulate hypothetical hiring scenarios.
- Reuse retrieval, formatter and client.
- Never modify stored data.
"""

from __future__ import annotations

from src.ai.client import get_client
from src.ai.formatter import format_candidate_context
from src.ai.prompts import SYSTEM_PROMPT
from src.ai.retrieval import get_complete_context


class DecisionSimulator:
    """
    Simulates hypothetical recruiter decisions.
    """

    def __init__(self):
        self.client = get_client()

    def simulate(
        self,
        candidate_id: str,
        scenario: str,
    ) -> str:

        context = get_complete_context(candidate_id)

        if context["candidate_profile"] is None:
            return "Candidate not found."

        formatted = format_candidate_context(context)

        prompt = f"""
Candidate Context
=================

{formatted}

Scenario
========

{scenario}

Instructions
============

Assume ONLY the scenario above changes.

Everything else remains unchanged.

Explain:

1. Would your hiring recommendation change?
2. Why?
3. What evidence supports your reasoning?
4. What risks remain?
"""

        return self.client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )