"""
src/ai/base.py

Shared utilities for AI modules.
"""

from __future__ import annotations

from src.ai.client import get_client
from src.ai.formatter import format_candidate_context
from src.ai.retrieval import get_complete_context


class AIBase:
    """
    Base class for all AI features.
    """

    def __init__(self):
        self.client = get_client()

    def _get_context(self, candidate_id: str):
        return get_complete_context(candidate_id)

    def _format_context(self, candidate_id: str):
        context = self._get_context(candidate_id)

        if context["candidate_profile"] is None:
            return None

        return format_candidate_context(context)