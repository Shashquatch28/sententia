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

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
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