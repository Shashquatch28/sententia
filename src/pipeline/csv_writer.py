from __future__ import annotations

import csv
import json
from pathlib import Path

from src.pipeline.reasoning import fallback_reasoning
from src.pipeline.top_k_buffer import RankedCandidate


HEADER = ["candidate_id", "rank", "score", "reasoning"]


def load_reasoning_map(precomputed_dir: str | Path | None) -> dict[str, str]:
    if not precomputed_dir:
        return {}
    path = Path(precomputed_dir) / "reasoning_map.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value}


def write_submission(
    ranked: list[RankedCandidate],
    out_path: str | Path,
    precomputed_dir: str | Path | None = None
) -> None:
    reasoning_map = load_reasoning_map(precomputed_dir)
    top_100 = ranked[:100]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True) if out.parent != Path(".") else None

    with open(out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for index, item in enumerate(top_100, 1):
            reasoning = reasoning_map.get(item.candidate_id)
            if not reasoning:
                reasoning = fallback_reasoning(item.candidate, item.features, index)
            writer.writerow([
                item.candidate_id,
                index,
                f"{item.score:.6f}",
                reasoning
            ])
