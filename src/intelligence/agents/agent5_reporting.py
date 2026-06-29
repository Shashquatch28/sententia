"""
Agent 5 - Reporting Agent.

Reads recruiter decisions, candidate profiles and job intelligence from the
shared ranked candidate set. Writes the CSV reasoning map, adjacent candidate
comparisons and the aggregated demo payload.
"""

import json
import logging
from pathlib import Path

from src.intelligence.paths import (
    COMPARISONS_FILE,
    DECISIONS_DIR,
    DEMO_DATA_FILE,
    JOB_INTEL_FILE,
    PROFILES_DIR,
    REASONING_MAP_FILE,
    is_test_mode,
    required_decisions,
)
from src.pipeline.reasoning import generate_reasoning_string

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent5-Report] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_DECISIONS = required_decisions()
COMPARISON_TOP_N = min(50, REQUIRED_DECISIONS)


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_decisions(candidate_ids: list[str] | None = None) -> list[dict]:
    if candidate_ids:
        decisions = []
        for cid in list(dict.fromkeys(candidate_ids)):
            path = DECISIONS_DIR / f"{cid}.json"
            if path.exists():
                decisions.append(_load_json(path))
        return decisions

    decisions = []
    for path in DECISIONS_DIR.glob("*.json"):
        try:
            decisions.append(_load_json(path))
        except Exception as exc:
            logger.warning(f"Could not load {path}: {exc}")
    decisions.sort(key=lambda d: d.get("overall_match_score", 0), reverse=True)
    return decisions


def _load_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for path in PROFILES_DIR.glob("*.json"):
        try:
            profile = _load_json(path)
            profiles[profile["candidate_id"]] = profile
        except Exception as exc:
            logger.warning(f"Could not load profile {path}: {exc}")
    return profiles


def generate_reasoning_map(decisions: list[dict], profiles: dict[str, dict]) -> dict[str, str]:
    reasoning_map: dict[str, str] = {}

    for rank, decision in enumerate(decisions, start=1):
        cid = decision["candidate_id"]
        reasoning_map[cid] = generate_reasoning_string(
            decision=decision,
            profile=profiles.get(cid, {}),
            rank=rank,
        )

    seen: dict[str, str] = {}
    for cid, text in list(reasoning_map.items()):
        if text in seen:
            rank = list(reasoning_map.keys()).index(cid) + 1
            reasoning_map[cid] = text.rstrip(".") + f" [rank {rank}]."
        else:
            seen[text] = cid

    return reasoning_map


def _compare_pair(a: dict, b: dict, profiles: dict[str, dict]) -> dict:
    cid_a = a["candidate_id"]
    cid_b = b["candidate_id"]
    profile_a = profiles.get(cid_a, {})
    profile_b = profiles.get(cid_b, {})
    name_a = a.get("name") or profile_a.get("name", cid_a)
    name_b = b.get("name") or profile_b.get("name", cid_b)
    title_a = a.get("current_title") or profile_a.get("current_title", "")
    company_a = a.get("current_company") or profile_a.get("current_company", "")
    fit_a = a.get("fit_assessment", {})
    fit_b = b.get("fit_assessment", {})

    dim_map = {
        "Technical": "technical",
        "Product": "product",
        "Cultural": "cultural",
        "Growth": "growth",
    }

    dim_comparison = {}
    a_wins = []

    for dim_name, key in dim_map.items():
        score_a = fit_a.get(key, {}).get("score", 0.5) if isinstance(fit_a.get(key), dict) else 0.5
        score_b = fit_b.get(key, {}).get("score", 0.5) if isinstance(fit_b.get(key), dict) else 0.5
        diff = score_a - score_b
        if diff > 0.05:
            winner = "A"
            a_wins.append(dim_name)
            rationale = f"{name_a} leads on {dim_name.lower()} ({score_a:.0%} vs {score_b:.0%})"
        elif diff < -0.05:
            winner = "B"
            rationale = f"{name_b} leads on {dim_name.lower()} ({score_b:.0%} vs {score_a:.0%})"
        else:
            winner = "TIE"
            rationale = f"Comparable {dim_name.lower()} fit ({score_a:.0%} vs {score_b:.0%})"
        dim_comparison[dim_name] = {
            "winner": winner,
            "a_score": round(score_a, 2),
            "b_score": round(score_b, 2),
            "rationale": rationale,
        }

    score_a = a.get("overall_match_score", 0)
    score_b = b.get("overall_match_score", 0)
    a_wins_str = ", ".join(a_wins[:2]) if a_wins else "overall fit"
    skills_b = profile_b.get("top_skills", [])

    return {
        "pair_key": f"{cid_a}_{cid_b}",
        "dimension_comparison": dim_comparison,
        "why_a_over_b": (
            f"{name_a} ({title_a} at {company_a}) ranks higher at "
            f"{int(score_a * 100)} vs {int(score_b * 100)} overall. "
            f"Stronger on {a_wins_str}."
        ),
        "b_salvage_scenario": (
            f"{name_b} would be preferred if the role scope narrows to focus on "
            f"{skills_b[0] if skills_b else 'their core strength'}, "
            f"or if {name_a} declines the offer."
        ),
    }


def generate_comparisons(top_n: list[dict], profiles: dict[str, dict]) -> dict[str, dict]:
    comparisons: dict[str, dict] = {}
    pairs = [(top_n[i], top_n[i + 1]) for i in range(len(top_n) - 1)]
    logger.info(f"Generating {len(pairs)} adjacent-pair comparisons (heuristic)...")

    for a, b in pairs:
        result = _compare_pair(a, b, profiles)
        comparisons[result["pair_key"]] = result

    return comparisons


def build_demo_data(
    decisions: list[dict],
    profiles: dict[str, dict],
    reasoning_map: dict[str, str],
    comparisons: dict[str, dict],
    job_intel: dict,
) -> dict:
    tiers: dict[str, list] = {
        "STRONGLY_ADVANCE": [],
        "ADVANCE": [],
        "REVIEW_FURTHER": [],
        "ADVANCE_IF_POOL_THIN": [],
        "DECLINE": [],
    }

    for decision in decisions:
        rec = decision.get("recommendation", "REVIEW_FURTHER")
        tier = tiers.get(rec, tiers["REVIEW_FURTHER"])
        cid = decision["candidate_id"]
        profile = profiles.get(cid, {})
        tier.append(
            {
                "candidate_id": cid,
                "name": decision.get("name") or profile.get("name", cid),
                "current_title": decision.get("current_title") or profile.get("current_title", ""),
                "current_company": decision.get("current_company") or profile.get("current_company", ""),
                "recommendation": rec,
                "overall_match_score": decision.get("overall_match_score", 0),
                "top_evidence": decision.get("top_evidence", [])[:2],
                "reasoning": reasoning_map.get(cid, ""),
                "fast_score": profile.get("fast_score", 0),
            }
        )

    for tier_list in tiers.values():
        tier_list.sort(key=lambda x: x["overall_match_score"], reverse=True)

    sorted_all = sorted(decisions, key=lambda d: d.get("overall_match_score", 0), reverse=True)
    stats = {
        "total_evaluated": len(decisions),
        "by_tier": {tier: len(lst) for tier, lst in tiers.items()},
        "avg_match_score": round(
            sum(d.get("overall_match_score", 0) for d in decisions) / max(len(decisions), 1),
            3,
        ),
    }

    return {
        "job_intelligence": job_intel,
        "candidates_by_tier": tiers,
        "all_candidates": sorted_all,
        "top_50_ids": [d["candidate_id"] for d in sorted_all[:50]],
        "comparisons": comparisons,
        "stats": stats,
    }


def run(candidate_ids: list[str] | None = None) -> dict:
    logger.info("=" * 60)
    mode_label = "TEST" if is_test_mode() else "FULL"
    logger.info(f"Agent 5: Reporting  [{mode_label} - expecting {REQUIRED_DECISIONS} decisions]")
    logger.info("=" * 60)

    decisions = _load_decisions(candidate_ids)
    logger.info(f"Loaded {len(decisions)} decisions")

    if len(decisions) < REQUIRED_DECISIONS:
        raise RuntimeError(
            f"Agent 5 requires {REQUIRED_DECISIONS} decisions. "
            f"Found: {len(decisions)}. Run agents 1-4 first."
        )

    decisions = decisions[:REQUIRED_DECISIONS]
    profiles = _load_profiles()

    if not JOB_INTEL_FILE.exists():
        raise FileNotFoundError(f"Missing {JOB_INTEL_FILE}. Run Agent 1 first.")
    job_intel = _load_json(JOB_INTEL_FILE)

    logger.info("Generating reasoning_map.json...")
    reasoning_map = generate_reasoning_map(decisions, profiles)

    logger.info("Generating comparisons.json...")
    comparisons = generate_comparisons(decisions[:COMPARISON_TOP_N], profiles)

    logger.info("Building demo_data.json...")
    demo_data = build_demo_data(decisions, profiles, reasoning_map, comparisons, job_intel)

    with open(REASONING_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(reasoning_map, f, indent=2)
    logger.info(f"Written: {REASONING_MAP_FILE}")

    with open(COMPARISONS_FILE, "w", encoding="utf-8") as f:
        json.dump(comparisons, f, indent=2)
    logger.info(f"Written: {COMPARISONS_FILE}")

    with open(DEMO_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(demo_data, f, indent=2)
    logger.info(f"Written: {DEMO_DATA_FILE}")

    assert len(reasoning_map) == REQUIRED_DECISIONS, (
        f"reasoning_map has {len(reasoning_map)} entries, expected {REQUIRED_DECISIONS}"
    )
    assert len(set(reasoning_map.values())) == REQUIRED_DECISIONS, (
        f"Duplicate reasoning strings detected: {REQUIRED_DECISIONS - len(set(reasoning_map.values()))}"
    )

    logger.info(f"Agent 5 complete - {len(decisions)} candidates reported")
    return demo_data


if __name__ == "__main__":
    run()
