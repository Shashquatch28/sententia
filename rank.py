from __future__ import annotations

import argparse
import sys

from src.pipeline.runner import run_ranking_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream and rank Redrob candidates.")
    parser.add_argument("--candidates", required=True, help="Path to candidates .json, .jsonl, or .jsonl.gz")
    parser.add_argument("--out", required=True, help="Output submission CSV path")
    parser.add_argument("--precomputed", default="precomputed", help="Optional Dev B precomputed artifact directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run_ranking_pipeline(args.candidates, args.out, args.precomputed)
    except Exception as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
