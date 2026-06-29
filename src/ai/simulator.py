"""
src/ai/simulator.py

Backward-compatible wrapper around AIService.
"""

from __future__ import annotations

from src.ai.service import AIService


class DecisionSimulator:

    def __init__(self):
        self.service = AIService()

    def simulate(
        self,
        candidate_id: str,
        scenario: str,
    ) -> str:

        return self.service.generate(
            task="simulation",
            candidate_id=candidate_id,
            scenario=scenario,
        )