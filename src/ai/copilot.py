"""
src/ai/copilot.py

Backward-compatible wrapper around AIService.
"""

from __future__ import annotations

from src.ai.service import AIService


class RecruiterCopilot:

    def __init__(self):
        self.service = AIService()

    def answer_candidate_question(
        self,
        candidate_id: str,
        question: str,
    ) -> str:

        return self.service.generate(
            task="copilot",
            candidate_id=candidate_id,
            question=question,
        )