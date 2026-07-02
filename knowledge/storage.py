"""
knowledge/storage.py

SQLite storage layer for the HireIQ / Sententia V3.10 Knowledge Store.

Responsibilities
----------------
- Create/open the SQLite database.
- Initialize the schema.
- Provide database connections.
- Expose simple transaction helpers.

This module intentionally knows nothing about
candidate JSON, LLMs, Streamlit, or the ranking pipeline.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from pathlib import Path

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("HIQ_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "hireiq.db"

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


# ---------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Return a SQLite connection.

    Foreign keys are enabled automatically.
    """
    DATA_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


# ---------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------

def initialize_database() -> None:
    """
    Create the database and execute schema.sql.
    Safe to call multiple times.
    """

    with get_connection() as conn:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema)
        conn.commit()


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def table_counts() -> dict[str, int]:
    """
    Return row counts for all major tables.
    Useful for verifying ingestion.
    """

    tables = [
        "job",
        "candidate_profiles",
        "match_scores",
        "recruiter_decisions",
    ]

    counts = {}

    with get_connection() as conn:
        cursor = conn.cursor()

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]

    return counts


def execute(
    query: str,
    params: tuple = (),
) -> None:
    """
    Execute a write query.
    """

    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()


# ---------------------------------------------------------------------
# Pipeline Decisions
# ---------------------------------------------------------------------

def get_decisions() -> list[dict]:
    """Return all pipeline decisions as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT candidate_id, status, decided_at FROM pipeline_decisions"
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_decision(candidate_id: str, status: str) -> None:
    """Insert or update a recruiter decision for a candidate."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO pipeline_decisions (candidate_id, status, decided_at)
               VALUES (?, ?, ?)
               ON CONFLICT(candidate_id) DO UPDATE SET status=excluded.status, decided_at=excluded.decided_at""",
            (candidate_id, status, now),
        )
        conn.commit()


def delete_decision(candidate_id: str) -> None:
    """Remove a decision for a candidate."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM pipeline_decisions WHERE candidate_id = ?",
            (candidate_id,),
        )
        conn.commit()


# ---------------------------------------------------------------------
# Run aggregate stats (for Copilot context)
# ---------------------------------------------------------------------

def get_run_stats() -> dict:
    """Return aggregate stats about the current candidate pool."""
    with get_connection() as conn:
        total_row = conn.execute("SELECT COUNT(*) FROM match_scores").fetchone()
        total = total_row[0] if total_row else 0

        avg_row = conn.execute("SELECT AVG(overall_match_score) FROM match_scores").fetchone()
        avg_score = round(avg_row[0], 3) if avg_row and avg_row[0] is not None else 0.0

        dist = conn.execute(
            """SELECT
               SUM(CASE WHEN overall_match_score >= 0.8 THEN 1 ELSE 0 END) AS strong,
               SUM(CASE WHEN overall_match_score >= 0.6 AND overall_match_score < 0.8 THEN 1 ELSE 0 END) AS good,
               SUM(CASE WHEN overall_match_score < 0.6 THEN 1 ELSE 0 END) AS weak
               FROM match_scores"""
        ).fetchone()

        top5 = conn.execute(
            """SELECT cp.name, cp.current_title, cp.years_of_experience,
                      ms.overall_match_score, rd.recommendation
               FROM match_scores ms
               JOIN candidate_profiles cp USING(candidate_id)
               LEFT JOIN recruiter_decisions rd USING(candidate_id)
               ORDER BY ms.overall_match_score DESC
               LIMIT 5"""
        ).fetchall()

        job_row = conn.execute("SELECT role_name FROM job LIMIT 1").fetchone()

    top5_list = [dict(r) for r in top5]
    return {
        "total": total,
        "avg_score": avg_score,
        "strong": int(dist["strong"] or 0) if dist else 0,
        "good": int(dist["good"] or 0) if dist else 0,
        "weak": int(dist["weak"] or 0) if dist else 0,
        "top5": top5_list,
        "role_name": job_row["role_name"] if job_row else "Unknown",
    }


# ---------------------------------------------------------------------
# Users (auth)
# ---------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, email, name, password_hash FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def verify_user(email: str, password: str) -> dict | None:
    """Return user dict if credentials match, else None."""
    user = get_user_by_email(email)
    if not user:
        return None
    if user["password_hash"] != _hash_password(password):
        return None
    return user


def create_user(email: str, name: str, password: str | None = None) -> dict:
    """Create a new user. Returns the created user dict."""
    user_id = uuid.uuid4().hex
    ph = _hash_password(password) if password else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (user_id, email, name, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, email.lower().strip(), name, ph),
        )
        conn.commit()
    return {"user_id": user_id, "email": email, "name": name}


def ensure_demo_user() -> dict:
    """Create the demo user if it doesn't exist yet."""
    user = get_user_by_email("demo@hireiq.com")
    if user:
        return user
    return create_user("demo@hireiq.com", "Demo Recruiter", "demo123")
