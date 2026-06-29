"""
Shared path constants and test-mode config for all HireIQ agents.
Single source of truth — import from here, not from os.path or scattered ROOT definitions.
"""

import os
from pathlib import Path

# Project root — two levels up from src/intelligence/
ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Dataset directory (hackathon challenge folder)
# ---------------------------------------------------------------------------

DATASET_DIR = ROOT / "datasets"
CANDIDATES_DIR = DATASET_DIR / "candidates"
DOCS_DIR = DATASET_DIR / "docs"

# Primary input files
CANDIDATES_JSONL = CANDIDATES_DIR / "candidates.jsonl"
SAMPLE_CANDIDATES_JSON = CANDIDATES_DIR / "sample_candidates.json"
JD_DOCX = DOCS_DIR / "job_description.docx"
REDROB_SIGNALS_DOCX = DOCS_DIR / "redrob_signals_doc.docx"
CANDIDATE_SCHEMA_JSON = CANDIDATES_DIR / "candidate_schema.json"

# Markdown fallback (created during scaffolding, used if docx not found)
JD_MD_FALLBACK = ROOT / "job_description.md"
CONFIG_JSON_FALLBACK = ROOT / "config" / "jd_requirements.json"

# ---------------------------------------------------------------------------
# Precomputed output paths
# ---------------------------------------------------------------------------

PRECOMPUTED_DIR = ROOT / "precomputed"
PROFILES_DIR = PRECOMPUTED_DIR / "candidate_profiles"
MATCH_DIR = PRECOMPUTED_DIR / "match_scores"
DECISIONS_DIR = PRECOMPUTED_DIR / "recruiter_decisions"
JOB_INTEL_FILE = PRECOMPUTED_DIR / "job_intelligence.json"
REASONING_MAP_FILE = PRECOMPUTED_DIR / "reasoning_map.json"
COMPARISONS_FILE = PRECOMPUTED_DIR / "comparisons.json"
DEMO_DATA_FILE = PRECOMPUTED_DIR / "demo_data.json"
RANKED_CANDIDATES_FILE = PRECOMPUTED_DIR / "ranked_candidates.json"


def ensure_output_dirs() -> None:
    for d in (PROFILES_DIR, MATCH_DIR, DECISIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Test mode  (set HIREIQ_TEST=1 or pass --test to run_agents.py)
# ---------------------------------------------------------------------------

def is_test_mode() -> bool:
    return os.getenv("HIREIQ_TEST", "0") == "1"


# Pipeline depth limits — smaller in test mode so the full loop runs in seconds
def top_candidates() -> int:
    """Agent 2: how many candidates to profile."""
    return 50 if is_test_mode() else 500


def top_profiles() -> int:
    """Agent 3: how many profiles to score against the JD."""
    return 50 if is_test_mode() else 200


def top_matches() -> int:
    """Agent 4: how many match scores to turn into recruiter decisions."""
    return 20 if is_test_mode() else 100


def required_decisions() -> int:
    """Agent 5: expected size of reasoning_map (relaxed in test mode)."""
    return top_matches()


def load_ranked_candidates() -> list[dict]:
    """
    Load the ranked candidate manifest written by the ranking pipeline.

    The manifest is the shared candidate set for the offline intelligence
    agents. If it is missing, callers should decide whether to fall back to
    the legacy per-agent selection logic.
    """

    if not RANKED_CANDIDATES_FILE.exists():
        return []

    import json

    try:
        with open(RANKED_CANDIDATES_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    ranked: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cid = item.get("candidate_id")
        if not cid:
            continue
        ranked.append(
            {
                "candidate_id": str(cid),
                "rank": int(item.get("rank", len(ranked) + 1)),
                "score": float(item.get("score", 0.0)),
            }
        )
    ranked.sort(key=lambda item: item["rank"])
    return ranked
