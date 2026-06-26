import gzip
import json
from pathlib import Path
from typing import Iterator

from app.models.candidate import Candidate
from app.parsers.candidate_parser import CandidateParser


class DatasetLoader:
    """
    Streams candidates from disk one at a time.

    Supported formats:
        - .json
        - .jsonl
        - .jsonl.gz
    """

    @staticmethod
    def load(path: str | Path) -> Iterator[Candidate]:

        path = Path(path)

        # --------------------------
        # JSONL.GZ
        # --------------------------

        if path.suffixes[-2:] == [".jsonl", ".gz"]:

            with gzip.open(path, "rt", encoding="utf-8") as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    yield CandidateParser.parse(json.loads(line))

            return

        # --------------------------
        # JSONL
        # --------------------------

        if path.suffix == ".jsonl":

            with open(path, "r", encoding="utf-8") as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    yield CandidateParser.parse(json.loads(line))

            return

        # --------------------------
        # JSON
        # --------------------------

        if path.suffix == ".json":

            with open(path, "r", encoding="utf-8") as f:

                data = json.load(f)

            if isinstance(data, list):

                for candidate in data:
                    yield CandidateParser.parse(candidate)

            else:
                yield CandidateParser.parse(data)

            return

        raise ValueError(f"Unsupported file format: {path}")