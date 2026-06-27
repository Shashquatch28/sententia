"""
run_agents.py — HireIQ Intelligence Pipeline
Runs all 5 agents in sequence with clear console logging per step.

Usage:
    python run_agents.py              # Full run  (500 → 200 → 100 → report)
    python run_agents.py --test       # Test run  (50 → 50 → 20 → report) using sample_candidates.json
    python run_agents.py --from 3    # Resume from agent 3
    python run_agents.py --only 1    # Run only agent 1
    python run_agents.py --test --from 2   # Test mode, resume from agent 2
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# IMPORTANT: parse args and set HIREIQ_TEST *before* any agent imports,
# because agents read is_test_mode() at module-import time for TOP_N constants.
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HireIQ Intelligence Pipeline")
    parser.add_argument(
        "--test", action="store_true",
        help="Use sample_candidates.json (50 candidates) for a fast end-to-end smoke test",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--from", dest="from_agent", type=int, choices=[1, 2, 3, 4, 5],
        help="Resume from this agent number (inclusive)",
    )
    group.add_argument(
        "--only", dest="only_agent", type=int, choices=[1, 2, 3, 4, 5],
        help="Run only this agent",
    )
    return parser.parse_args()


args = _parse_args()

if args.test:
    os.environ["HIREIQ_TEST"] = "1"

# ---------------------------------------------------------------------------
# Logging (after arg parsing so HIREIQ_TEST is set before any module loads)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent

sys.stdout.reconfigure(encoding="utf-8")

_TEST_MODE = os.getenv("HIREIQ_TEST") == "1"

BANNER = f"""
+------------------------------------------------------------+
|           HireIQ — Intelligence Pipeline                  |
|           Dev B: Offline Pre-Computation Phase            |
|           Mode: {'TEST (sample_candidates.json)     ' if _TEST_MODE else 'FULL (candidates.jsonl / 100K)     '}|
+------------------------------------------------------------+
"""


def _ensure_dirs() -> None:
    from src.intelligence.paths import ensure_output_dirs
    ensure_output_dirs()
    logger.info("✓ precomputed/ directories ready")


def _section(title: str) -> None:
    bar = "─" * 60
    logger.info(f"\n{bar}")
    logger.info(f"  {title}")
    logger.info(bar)


# ---------------------------------------------------------------------------
# Per-agent wrappers — imports happen here so HIREIQ_TEST is already set
# ---------------------------------------------------------------------------

def run_agent_1() -> dict:
    label = "AGENT 1 — Job Intelligence  (job_description.docx)"
    _section(label)
    t0 = time.time()
    from src.intelligence.agents.agent1_job import run
    result = run()
    logger.info(f"  Done in {time.time() - t0:.1f}s")
    return result


def run_agent_2() -> list:
    n = 50 if _TEST_MODE else 500
    _section(f"AGENT 2 — Candidate Intelligence  (top-{n})")
    t0 = time.time()
    from src.intelligence.agents.agent2_candidate import run
    profiles = run()
    logger.info(f"  Done in {time.time() - t0:.1f}s — {len(profiles)} profiles written")
    return profiles


def run_agent_3() -> list:
    n = 50 if _TEST_MODE else 200
    _section(f"AGENT 3 — Matching Intelligence  (top-{n})")
    t0 = time.time()
    from src.intelligence.agents.agent3_matching import run
    scores = run()
    logger.info(f"  Done in {time.time() - t0:.1f}s — {len(scores)} match scores written")
    return scores


def run_agent_4() -> list:
    n = 20 if _TEST_MODE else 100
    _section(f"AGENT 4 — Recruiter Intelligence  (top-{n})")
    t0 = time.time()
    from src.intelligence.agents.agent4_recruiter import run
    decisions = run()
    logger.info(f"  Done in {time.time() - t0:.1f}s — {len(decisions)} decisions written")
    return decisions


def run_agent_5() -> dict:
    n = 20 if _TEST_MODE else 100
    _section(f"AGENT 5 — Reporting & reasoning_map  ({n} decisions)")
    t0 = time.time()
    from src.intelligence.agents.agent5_reporting import run
    demo_data = run()
    elapsed = time.time() - t0
    stats = demo_data.get("stats", {})
    logger.info(f"  Done in {elapsed:.1f}s")
    logger.info(f"  Total evaluated : {stats.get('total_evaluated', 0)}")
    logger.info(f"  Avg match score : {stats.get('avg_match_score', 0):.1%}")
    for tier, count in stats.get("by_tier", {}).items():
        if count:
            logger.info(f"    {tier:<25} {count}")
    return demo_data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(BANNER)
    _ensure_dirs()

    agents = {
        1: run_agent_1,
        2: run_agent_2,
        3: run_agent_3,
        4: run_agent_4,
        5: run_agent_5,
    }

    if args.only_agent:
        run_list = [args.only_agent]
    elif args.from_agent:
        run_list = list(range(args.from_agent, 6))
    else:
        run_list = [1, 2, 3, 4, 5]

    pipeline_start = time.time()
    failed_at = None

    for agent_num in run_list:
        try:
            agents[agent_num]()
        except FileNotFoundError as exc:
            logger.error(f"\n✗ Agent {agent_num} failed — missing prerequisite:\n  {exc}")
            logger.error("  Make sure earlier agents ran successfully.")
            failed_at = agent_num
            break
        except RuntimeError as exc:
            logger.error(f"\n✗ Agent {agent_num} failed:\n  {exc}")
            failed_at = agent_num
            break
        except Exception as exc:
            logger.error(f"\n✗ Agent {agent_num} unexpected error: {exc}", exc_info=True)
            failed_at = agent_num
            break

    total = time.time() - pipeline_start
    if failed_at is None:
        _section("PIPELINE COMPLETE")
        logger.info(f"  Total elapsed: {total:.1f}s")
        logger.info("")
        logger.info("  ✓ reasoning_map.json ready for Dev A handoff")
        logger.info(f"    → {ROOT / 'precomputed' / 'reasoning_map.json'}")
        logger.info("")
        logger.info("  Launch Streamlit UI:")
        logger.info("    streamlit run app/streamlit_app.py")
    else:
        _section(f"PIPELINE STOPPED AT AGENT {failed_at}")
        logger.info(f"  Total elapsed: {total:.1f}s")
        test_flag = " --test" if _TEST_MODE else ""
        logger.info(
            f"  Fix the error above, then resume with: "
            f"python run_agents.py{test_flag} --from {failed_at}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
