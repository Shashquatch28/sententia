from __future__ import annotations

import sys
from pathlib import Path


DATASET_VALIDATOR = Path(__file__).parent / "datasets" / "validate_submission.py"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_output.py <submission.csv>")
        return 1

    namespace: dict[str, object] = {}
    exec(DATASET_VALIDATOR.read_text(encoding="utf-8"), namespace)
    errors = namespace["validate_submission"](sys.argv[1])
    if errors:
        print(f"Validation failed ({len(errors)} issue(s)):\n")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Submission is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
