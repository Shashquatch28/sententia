from __future__ import annotations

import json
import sys
from pathlib import Path

from src.pipeline.csv_writer import write_submission
from src.pipeline.stream_parser import stream_candidates
from src.pipeline.top_k_buffer import TopKBuffer
from src.scoring.final_scorer import score_candidate


def load_jd_requirements(path: str | Path = "config/jd_requirements.json") -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_ranking_pipeline(
    candidates_path: str | Path,
    out_path: str | Path,
    precomputed_dir: str | Path | None = None,
    jd_path: str | Path = "config/jd_requirements.json",
    heap_size: int = 200
) -> int:
    jd = load_jd_requirements(jd_path)
    top_k = TopKBuffer(heap_size)
    processed = 0

    for candidate in stream_candidates(candidates_path):
        processed += 1
        features = score_candidate(candidate, jd)
        top_k.push(candidate, features)
        if processed % 10000 == 0:
            print(f"processed={processed}", file=sys.stderr, flush=True)

    ranked = top_k.sorted_desc()
    if len(ranked) < 100:
        print(f"fatal: only {len(ranked)} rankable candidates; need at least 100", file=sys.stderr)
        return 1

    write_submission(ranked, out_path, precomputed_dir)
    print(f"ranked {processed} candidates; wrote {out_path}", file=sys.stderr)
    return 0
