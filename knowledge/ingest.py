"""
knowledge/ingest.py

Imports existing precomputed recruiter artifacts into the
SQLite Knowledge Store.

This module NEVER generates intelligence.

It simply mirrors the JSON artifacts produced by the offline
agent pipeline into SQLite for retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from knowledge.storage import get_connection

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

PRECOMPUTED = ROOT / "precomputed"

CANDIDATE_DIR = PRECOMPUTED / "candidate_profiles"
MATCH_DIR = PRECOMPUTED / "match_scores"
DECISION_DIR = PRECOMPUTED / "recruiter_decisions"

JOB_FILE = PRECOMPUTED / "job_intelligence.json"
DEMO_FILE = PRECOMPUTED / "demo_data.json"

# ---------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------

INSERT_JOB = """
INSERT OR REPLACE INTO job
(job_id, role_name, created_at, payload)
VALUES (?, ?, ?, ?)
"""

INSERT_CANDIDATE = """
INSERT OR REPLACE INTO candidate_profiles
(
    candidate_id,
    name,
    current_title,
    current_company,
    narrative_type,
    consistency_score,
    fast_score,
    years_of_experience,
    payload
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_MATCH = """
INSERT OR REPLACE INTO match_scores
(
    candidate_id,
    overall_match_score,
    payload
)
VALUES (?, ?, ?)
"""

INSERT_DECISION = """
INSERT OR REPLACE INTO recruiter_decisions
(
    candidate_id,
    recommendation,
    overall_match_score,
    payload
)
VALUES (?, ?, ?, ?)
"""

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_json(directory: Path) -> Iterable[Path]:
    return sorted(directory.glob("*.json"))


# ---------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------

def ingest_job(conn) -> int:
    """
    Import job_intelligence.json.
    """

    if not JOB_FILE.exists():
        return 0

    job = _load_json(JOB_FILE)

    conn.execute(
        INSERT_JOB,
        (
            "default",
            job.get("role_name", ""),
            job.get("generated_at", ""),
            json.dumps(job, ensure_ascii=False),
        ),
    )

    return 1

# ---------------------------------------------------------------------
# Candidate Profiles
# ---------------------------------------------------------------------

def ingest_candidate_profiles(conn) -> int:

    count = 0

    for path in _iter_json(CANDIDATE_DIR):

        candidate = _load_json(path)

        conn.execute(
            INSERT_CANDIDATE,
            (
                candidate["candidate_id"],
                candidate.get("name", ""),
                candidate.get("current_title", ""),
                candidate.get("current_company", ""),
                candidate.get("narrative_type", ""),
                candidate.get("consistency_score", 0.0),
                candidate.get("fast_score", 0.0),
                candidate.get("years_of_experience", 0.0),
                json.dumps(candidate, ensure_ascii=False),
            ),
        )

        count += 1

    return count

# ---------------------------------------------------------------------
# Match Scores
# ---------------------------------------------------------------------

def ingest_match_scores(conn) -> int:

    count = 0

    for path in _iter_json(MATCH_DIR):

        match = _load_json(path)

        conn.execute(
            INSERT_MATCH,
            (
                match["candidate_id"],
                match.get("overall_match_score", 0.0),
                json.dumps(match, ensure_ascii=False),
            ),
        )

        count += 1

    return count


# ---------------------------------------------------------------------
# Recruiter Decisions
# ---------------------------------------------------------------------

def ingest_recruiter_decisions(conn) -> int:

    count = 0

    for path in _iter_json(DECISION_DIR):

        decision = _load_json(path)

        conn.execute(
            INSERT_DECISION,
            (
                decision["candidate_id"],
                decision.get("recommendation", ""),
                decision.get("overall_match_score", 0.0),
                json.dumps(decision, ensure_ascii=False),
            ),
        )

        count += 1

    return count

# ---------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------

def ingest_all() -> dict[str, int]:
    """
    Import every precomputed artifact into SQLite.
    """

    stats = {}

    with get_connection() as conn:

        stats["job"] = ingest_job(conn)

        stats["candidate_profiles"] = ingest_candidate_profiles(conn)

        stats["match_scores"] = ingest_match_scores(conn)

        stats["recruiter_decisions"] = ingest_recruiter_decisions(conn)

        conn.commit()

    return stats


def ingest_demo_data() -> dict[str, int]:
    """
    Import the compact frontend demo artifact into SQLite.

    This is a deployment fallback for hosts where the per-candidate
    precomputed directories are not present, but demo_data.json is.
    """

    if not DEMO_FILE.exists():
        return {
            "job": 0,
            "candidate_profiles": 0,
            "match_scores": 0,
            "recruiter_decisions": 0,
        }

    demo = _load_json(DEMO_FILE)
    candidates = demo.get("all_candidates", []) or []
    job = demo.get("job_intelligence", {}) or {}

    with get_connection() as conn:
        if job:
            conn.execute(
                INSERT_JOB,
                (
                    "default",
                    job.get("role_name", "Recommendation Systems Engineer"),
                    job.get("generated_at", ""),
                    json.dumps(job, ensure_ascii=False),
                ),
            )

        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            match_payload = {
                **candidate,
                "match_evidence": candidate.get("top_evidence", []),
                "identified_gaps": _collect_gaps(candidate),
            }

            conn.execute(
                INSERT_CANDIDATE,
                (
                    candidate_id,
                    candidate.get("name", ""),
                    candidate.get("current_title", ""),
                    candidate.get("current_company", ""),
                    candidate.get("narrative_type", ""),
                    candidate.get("consistency_score", 0.0),
                    candidate.get("fast_score", candidate.get("overall_match_score", 0.0)),
                    candidate.get("years_of_experience", 0.0),
                    json.dumps(candidate, ensure_ascii=False),
                ),
            )
            conn.execute(
                INSERT_MATCH,
                (
                    candidate_id,
                    candidate.get("overall_match_score", 0.0),
                    json.dumps(match_payload, ensure_ascii=False),
                ),
            )
            conn.execute(
                INSERT_DECISION,
                (
                    candidate_id,
                    candidate.get("recommendation", ""),
                    candidate.get("overall_match_score", 0.0),
                    json.dumps(candidate, ensure_ascii=False),
                ),
            )

        conn.commit()

    return {
        "job": 1 if job else 0,
        "candidate_profiles": len(candidates),
        "match_scores": len(candidates),
        "recruiter_decisions": len(candidates),
    }


def _collect_gaps(candidate: dict) -> list[str]:
    gaps: list[str] = []
    for dimension in (candidate.get("fit_assessment") or {}).values():
        if isinstance(dimension, dict):
            gaps.extend(str(gap) for gap in dimension.get("gaps", []) if gap)
    return gaps
