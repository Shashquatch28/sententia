"""
run_agents.py - HireIQ Intelligence Pipeline.

The ranking pipeline writes precomputed/ranked_candidates.json. Agents 2-5 use
that manifest so intelligence artifacts are generated for the same candidate
set that appears in submission.csv.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HireIQ Intelligence Pipeline")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use test-mode funnel sizes after rank.py has written ranked_candidates.json",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--from",
        dest="from_agent",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Resume from this agent number, inclusive",
    )
    group.add_argument(
        "--only",
        dest="only_agent",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run only this agent",
    )
    return parser.parse_args()


args = _parse_args()

if args.test:
    os.environ["HIREIQ_TEST"] = "1"

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
------------------------------------------------------------+
|           HireIQ - Intelligence Pipeline                   |
|           Offline Pre-Computation Phase                    |
|           Mode: {'TEST' if _TEST_MODE else 'FULL':<41}|
------------------------------------------------------------+
"""


def _ensure_dirs() -> None:
    from src.intelligence.paths import ensure_output_dirs

    ensure_output_dirs()
    logger.info("precomputed/ directories ready")


def _section(title: str) -> None:
    bar = "-" * 60
    logger.info(f"\n{bar}")
    logger.info(f"  {title}")
    logger.info(bar)


def _ranked_candidate_ids(run_list: list[int]) -> list[str]:
    if not any(agent_num >= 2 for agent_num in run_list):
        return []

    from src.intelligence.paths import RANKED_CANDIDATES_FILE, load_ranked_candidates

    ranked = load_ranked_candidates()
    if not ranked:
        raise RuntimeError(
            f"Missing shared ranked candidate manifest: {RANKED_CANDIDATES_FILE}. "
            "Run rank.py first with --precomputed precomputed."
        )

    ids = [item["candidate_id"] for item in ranked]
    logger.info(f"Loaded shared ranked candidate manifest: {len(ids)} candidate(s)")
    return ids


def _agent_4_count() -> int:
    return 20 if _TEST_MODE else 100


def run_agent_1() -> dict:
    _section("AGENT 1 - Job Intelligence")
    t0 = time.time()
    from src.intelligence.agents.agent1_job import run

    result = run()
    logger.info(f"  Done in {time.time() - t0:.1f}s")
    return result


def run_agent_2(candidate_ids: list[str]) -> list:
    _section(f"AGENT 2 - Candidate Intelligence ({len(candidate_ids)} ranked candidates)")
    t0 = time.time()
    from src.intelligence.agents.agent2_candidate import run

    profiles = run(candidate_ids=candidate_ids)
    logger.info(f"  Done in {time.time() - t0:.1f}s - {len(profiles)} profiles written")
    return profiles


def run_agent_3(candidate_ids: list[str]) -> list:
    _section(f"AGENT 3 - Matching Intelligence ({len(candidate_ids)} ranked candidates)")
    t0 = time.time()
    from src.intelligence.agents.agent3_matching import run

    scores = run(candidate_ids=candidate_ids)
    logger.info(f"  Done in {time.time() - t0:.1f}s - {len(scores)} match scores written")
    return scores


def run_agent_4(candidate_ids: list[str]) -> list:
    n = _agent_4_count()
    _section(f"AGENT 4 - Recruiter Intelligence (top-{n})")
    t0 = time.time()
    from src.intelligence.agents.agent4_recruiter import run

    decisions = run(candidate_ids=candidate_ids[:n])
    logger.info(f"  Done in {time.time() - t0:.1f}s - {len(decisions)} decisions written")
    return decisions


def run_agent_5(candidate_ids: list[str]) -> dict:
    n = _agent_4_count()
    _section(f"AGENT 5 - Reporting & reasoning_map ({n} decisions)")
    t0 = time.time()
    from src.intelligence.agents.agent5_reporting import run

    demo_data = run(candidate_ids=candidate_ids[:n])
    stats = demo_data.get("stats", {})
    logger.info(f"  Done in {time.time() - t0:.1f}s")
    logger.info(f"  Total evaluated : {stats.get('total_evaluated', 0)}")
    logger.info(f"  Avg match score : {stats.get('avg_match_score', 0):.1%}")
    for tier, count in stats.get("by_tier", {}).items():
        if count:
            logger.info(f"    {tier:<25} {count}")
    return demo_data


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

    try:
        ranked_ids = _ranked_candidate_ids(run_list)
    except RuntimeError as exc:
        _section("PIPELINE STOPPED BEFORE AGENT RUN")
        logger.error(str(exc))
        sys.exit(1)

    pipeline_start = time.time()
    failed_at = None

    for agent_num in run_list:
        try:
            if agent_num == 1:
                agents[agent_num]()
            else:
                agents[agent_num](ranked_ids)
        except FileNotFoundError as exc:
            logger.error(f"\nAgent {agent_num} failed - missing prerequisite:\n  {exc}")
            failed_at = agent_num
            break
        except RuntimeError as exc:
            logger.error(f"\nAgent {agent_num} failed:\n  {exc}")
            failed_at = agent_num
            break
        except Exception as exc:
            logger.error(f"\nAgent {agent_num} unexpected error: {exc}", exc_info=True)
            failed_at = agent_num
            break

    total = time.time() - pipeline_start
    if failed_at is None:
        _section("PIPELINE COMPLETE")
        logger.info(f"  Total elapsed: {total:.1f}s")
        logger.info(f"  reasoning_map.json ready: {ROOT / 'precomputed' / 'reasoning_map.json'}")
    else:
        _section(f"PIPELINE STOPPED AT AGENT {failed_at}")
        logger.info(f"  Total elapsed: {total:.1f}s")
        test_flag = " --test" if _TEST_MODE else ""
        logger.info(f"  Fix the error above, then resume with: python run_agents.py{test_flag} --from {failed_at}")
        sys.exit(1)


if __name__ == "__main__":
    main()
