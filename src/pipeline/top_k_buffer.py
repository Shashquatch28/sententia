from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any

from src.models.feature_vector import CandidateFeatureVector


@dataclass(slots=True)
class RankedCandidate:
    candidate_id: str
    score: float
    candidate: dict[str, Any]
    features: CandidateFeatureVector


class TopKBuffer:
    def __init__(self, size: int) -> None:
        self.size = size
        self._heap: list[tuple[float, str, RankedCandidate]] = []

    def push(self, candidate: dict[str, Any], features: CandidateFeatureVector) -> None:
        if features.is_honeypot:
            return
        item = RankedCandidate(
            candidate_id=features.candidate_id,
            score=features.final_score,
            candidate=candidate,
            features=features
        )
        heap_item = (item.score, _reverse_id(item.candidate_id), item)
        if len(self._heap) < self.size:
            heapq.heappush(self._heap, heap_item)
            return
        if heap_item > self._heap[0]:
            heapq.heapreplace(self._heap, heap_item)

    def sorted_desc(self) -> list[RankedCandidate]:
        return [
            item
            for _, _, item in sorted(
                self._heap,
                key=lambda row: (-row[2].score, row[2].candidate_id)
            )
        ]


def _reverse_id(candidate_id: str) -> str:
    return "".join(chr(255 - ord(char)) for char in candidate_id)
