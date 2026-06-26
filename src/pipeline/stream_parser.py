from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterator


def stream_candidates(path: str | Path) -> Iterator[dict[str, Any]]:
    candidate_path = Path(path)
    suffixes = candidate_path.suffixes

    if suffixes[-2:] == [".jsonl", ".gz"] or candidate_path.suffix == ".gz":
        opener = gzip.open
        mode = "rt"
    else:
        opener = open
        mode = "r"

    if candidate_path.suffix == ".json":
        with open(candidate_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
        elif isinstance(data, dict):
            yield data
        return

    with opener(candidate_path, mode, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if isinstance(parsed, dict):
                yield parsed
