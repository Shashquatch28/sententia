from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _load_scores() -> dict[str, float]:
    path = Path("precomputed") / "semantic_scores.json"

    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    return {str(k): float(v) for k, v in data.items()}


def semantic_score(candidate_id: str) -> float:
    return _load_scores().get(candidate_id, 0.0)