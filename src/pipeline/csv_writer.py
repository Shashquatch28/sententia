from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from src.pipeline.reasoning import fallback_reasoning
from src.pipeline.top_k_buffer import RankedCandidate
from src.intelligence.paths import RANKED_CANDIDATES_FILE

logger = logging.getLogger(__name__)

HEADER = ["candidate_id", "rank", "score", "reasoning"]


def load_reasoning_map(precomputed_dir: str | Path | None) -> dict[str, str]:
    if not precomputed_dir:
        return {}

    path = Path(precomputed_dir) / "reasoning_map.json"

    if not path.exists():
        logger.warning("reasoning_map.json not found. Using runtime fallback reasoning.")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to load reasoning_map.json. Using runtime fallback reasoning.")
        return {}

    if not isinstance(data, dict):
        logger.warning("Invalid reasoning_map.json format. Using runtime fallback reasoning.")
        return {}

    return {
        str(candidate_id): str(reasoning)
        for candidate_id, reasoning in data.items()
        if reasoning
    }


def write_submission(
    ranked: list[RankedCandidate],
    out_path: str | Path,
    precomputed_dir: str | Path | None = None,
) -> None:

    reasoning_map = load_reasoning_map(precomputed_dir)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)

        fallback_count = 0
        manifest: list[dict[str, object]] = []

        for rank, item in enumerate(ranked[:100], start=1):
            manifest.append(
                {
                    "candidate_id": item.candidate_id,
                    "rank": rank,
                    "score": round(float(item.score), 6),
                }
            )

            reasoning = reasoning_map.get(item.candidate_id)

            if reasoning is None:
                fallback_count += 1
                reasoning = fallback_reasoning(
                    item.candidate,
                    item.features,
                    rank,
                )

            writer.writerow(
                [
                    item.candidate_id,
                    rank,
                    f"{item.score:.6f}",
                    reasoning,
                ]
            )

    if precomputed_dir:
        manifest_path = Path(precomputed_dir) / RANKED_CANDIDATES_FILE.name
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    if fallback_count:
        logger.warning(
            "Generated fallback reasoning for %d candidate(s).",
            fallback_count,
        )
