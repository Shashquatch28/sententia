"""
src/ai/retrieval.py

Retrieval layer for the HireIQ / Sententia AI system.

Responsibilities
----------------
- Read candidate data from the Knowledge Store.
- Return unified retrieval objects.
- Contain NO business logic.
- Contain NO LLM calls.
"""

from __future__ import annotations

from knowledge.storage import get_connection


# ---------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------

def _fetch_one(table: str, candidate_id: str) -> dict | None:
    """
    Fetch a single candidate record from the specified table.
    """

    with get_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()

    return dict(row) if row else None


def _fetch_job() -> dict | None:
    """
    Fetch the job intelligence record.
    """

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM job LIMIT 1"
        ).fetchone()

    return dict(row) if row else None


# ---------------------------------------------------------------------
# Public Retrieval API
# ---------------------------------------------------------------------

def get_candidate_profile(candidate_id: str) -> dict | None:
    """
    Retrieve the candidate profile.
    """
    return _fetch_one("candidate_profiles", candidate_id)


def get_match_score(candidate_id: str) -> dict | None:
    """
    Retrieve the candidate match score.
    """
    return _fetch_one("match_scores", candidate_id)


def get_recruiter_decision(candidate_id: str) -> dict | None:
    """
    Retrieve the recruiter decision.
    """
    return _fetch_one("recruiter_decisions", candidate_id)


def get_job_intelligence() -> dict | None:
    """
    Retrieve job intelligence.
    """
    return _fetch_job()


def get_complete_context(candidate_id: str) -> dict:
    """
    Retrieve the complete recruiter context for a candidate.
    """

    return {
        "candidate_profile": get_candidate_profile(candidate_id),
        "match_score": get_match_score(candidate_id),
        "recruiter_decision": get_recruiter_decision(candidate_id),
        "job_intelligence": get_job_intelligence(),
    }