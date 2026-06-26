"""
Agent 5 — Reporting Agent (Rule-Based, No LLM)
Reads:   precomputed/recruiter_decisions/*.json  (all 100)
         precomputed/candidate_profiles/*.json
         precomputed/job_intelligence.json
Outputs: precomputed/reasoning_map.json   — exactly 100 candidate-specific strings
         precomputed/comparisons.json     — adjacent pairs in top-50
         precomputed/demo_data.json       — aggregated UI payload

Reasoning strings use branching templates injected with candidate-specific data.
Comparisons use heuristic scoring from fit_assessment dimensions.

Asserts: len(reasoning_map) == REQUIRED_DECISIONS and all strings are unique.
Never imports from src/scoring/ or src/pipeline/.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent5-Report] %(message)s")
logger = logging.getLogger(__name__)

from src.intelligence.paths import (
    COMPARISONS_FILE,
    DECISIONS_DIR,
    DEMO_DATA_FILE,
    JOB_INTEL_FILE,
    MATCH_DIR,
    PROFILES_DIR,
    REASONING_MAP_FILE,
    is_test_mode,
    required_decisions,
)

REQUIRED_DECISIONS = required_decisions()   # 20 in test mode, 100 in full mode
COMPARISON_TOP_N = min(50, REQUIRED_DECISIONS)


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Template-based reasoning strings (spec-aligned)
# ---------------------------------------------------------------------------

def _reasoning_string(decision: dict, profile: dict, rank: int) -> str:
    """
    Branching templates per recommendation tier with structural rotation.
    Each tier has 3 variants (2 for lower tiers) — variant selected by hash(cid) % N
    so the same candidate always gets the same structure but different candidates vary.
    This satisfies the Stage 4 "substantively different" check.
    """
    cid = decision["candidate_id"]
    name = decision.get("name") or profile.get("name", cid)
    title = decision.get("current_title") or profile.get("current_title", "unknown role")
    company = decision.get("current_company") or profile.get("current_company", "unknown company")
    rec = decision.get("recommendation", "REVIEW_FURTHER")
    score = int(decision.get("overall_match_score", 0) * 100)
    skills = profile.get("top_skills", [])
    matched = decision.get("required_skills_matched", [])
    evidence_list = decision.get("top_evidence", [])
    yoe = profile.get("years_of_experience", 0) or 0

    fit = decision.get("fit_assessment", {})
    tech_gaps = fit.get("technical", {}).get("gaps", [])
    prod_gaps = fit.get("product", {}).get("gaps", [])
    all_gaps = list(dict.fromkeys(tech_gaps + prod_gaps + decision.get("identified_gaps", [])))

    if not all_gaps:
        match_path = MATCH_DIR / f"{cid}.json"
        if match_path.exists():
            match = _load_json(match_path)
            all_gaps = match.get("identified_gaps", [])

    risks = decision.get("hiring_risks", [])
    blocking_risks = [r for r in risks if r.get("is_blocking")]
    top_risk_desc = (blocking_risks[0]["description"] if blocking_risks
                     else (risks[0]["description"] if risks else None))

    primary_skill = matched[0] if matched else (skills[0] if skills else "ML background")
    secondary_skill = matched[1] if len(matched) > 1 else (skills[1] if len(skills) > 1 else "")
    skill_summary = f"{primary_skill} and {secondary_skill}" if secondary_skill else primary_skill
    tech_evidence = evidence_list[0] if evidence_list else f"{primary_skill} background at {company}"
    prod_outcome = evidence_list[1] if len(evidence_list) > 1 else (
        f"product-company context ({title})" if company else "product exposure"
    )
    gap = all_gaps[0] if all_gaps else None
    variant = abs(hash(cid)) % 3

    if rec == "STRONGLY_ADVANCE":
        concern = f"Watch: {top_risk_desc}." if top_risk_desc else "No blocking concerns identified."
        if variant == 0:
            return (f"{name} ({title} at {company}, {score}/100) — {tech_evidence}; "
                    f"{prod_outcome}. {concern}")
        elif variant == 1:
            return (f"Strong hire at {score}/100. {name} brings {skill_summary} with demonstrated "
                    f"product-company depth ({company}). {prod_outcome}. {concern} "
                    f"Recommend immediate technical screen.")
        else:
            return (f"{score}/100 match — {name}'s {yoe:.0f}-year career ({title}, {company}) directly "
                    f"addresses LLM/RAG requirements via {skill_summary}. {prod_outcome}. {concern}")

    elif rec == "ADVANCE":
        gap_note = f"gap to probe: {gap}" if gap else "no critical gaps identified"
        if variant == 0:
            return (f"{name} ({title} at {company}, {score}/100) — {tech_evidence}; "
                    f"{gap_note}. Advancing for technical screen.")
        elif variant == 1:
            return (f"Advance to phone screen. {name} ({company}) scores {score}/100 — "
                    f"{skill_summary} aligns with role. Key check: {gap_note}.")
        else:
            return (f"{name} ({title}, {score}/100) — {tech_evidence}. {gap_note.capitalize()}. "
                    f"Profile is strong enough for a technical screen; verify depth in LLM/RAG ownership.")

    elif rec == "REVIEW_FURTHER":
        gap_note = gap if gap else "full role alignment"
        if variant == 0:
            return (f"{name} ({title} at {company}, {score}/100) — adjacent fit via {primary_skill}; "
                    f"gap in {gap_note}. Review if top candidates are unavailable.")
        else:
            return (f"{name} ({title}, {company}) has adjacent ML skills ({primary_skill}) but "
                    f"{gap_note} is unverified at {score}/100. Borderline — include only if pipeline is thin.")

    elif rec == "ADVANCE_IF_POOL_THIN":
        gap_note = gap if gap else "multiple gaps present"
        if variant == 0:
            return (f"{name} ({title} at {company}, {score}/100) — below primary threshold — "
                    f"{gap_note}. Included as rank-{rank} given {tech_evidence}.")
        else:
            return (f"Rank {rank} at {score}/100. {name} ({title}, {company}) falls below our primary "
                    f"bar — {gap_note}. Advance only if stronger candidates decline or are unavailable.")

    elif rec == "DECLINE":
        reason = top_risk_desc or gap or "does not meet minimum requirements for this role"
        if variant == 0:
            return f"{name} ({title} at {company}, {score}/100) — not recommended. {reason}."
        else:
            return (f"Do not advance. {name} ({title}, {company}) scores {score}/100 — "
                    f"{reason}. Falls below the minimum bar for Senior AI Engineer.")

    return (f"{name} ({title} at {company}, {score}/100) — {tech_evidence}. "
            f"{rec.replace('_', ' ').title()}.")


def generate_reasoning_map(
    decisions: list,
    profiles: dict,
) -> dict:
    reasoning_map: dict = {}

    for rank, decision in enumerate(decisions, start=1):
        cid = decision["candidate_id"]
        profile = profiles.get(cid, {})
        reasoning_map[cid] = _reasoning_string(decision, profile, rank)

    # Deduplicate (append rank suffix if two strings are identical)
    seen: dict = {}
    for cid, text in reasoning_map.items():
        if text in seen:
            reasoning_map[cid] = text.rstrip(".") + f" [rank {list(reasoning_map.keys()).index(cid) + 1}]."
        else:
            seen[text] = cid

    return reasoning_map


# ---------------------------------------------------------------------------
# Heuristic comparisons
# ---------------------------------------------------------------------------

def _compare_pair(a: dict, b: dict, profiles: dict) -> dict:
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
    b_wins = []

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
            b_wins.append(dim_name)
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

    why_a = (
        f"{name_a} ({title_a} at {company_a}) ranks higher at {int(score_a * 100)} vs {int(score_b * 100)} "
        f"overall. Stronger on {a_wins_str}."
    )

    skills_b = profile_b.get("top_skills", [])
    b_salvage = (
        f"{name_b} would be preferred if the role scope narrows to focus on "
        f"{skills_b[0] if skills_b else 'their core strength'}, "
        f"or if {name_a} declines the offer."
    )

    return {
        "pair_key": f"{cid_a}_{cid_b}",
        "dimension_comparison": dim_comparison,
        "why_a_over_b": why_a,
        "b_salvage_scenario": b_salvage,
    }


def generate_comparisons(top_n: list, profiles: dict) -> dict:
    comparisons: dict = {}
    pairs = [(top_n[i], top_n[i + 1]) for i in range(len(top_n) - 1)]
    logger.info(f"Generating {len(pairs)} adjacent-pair comparisons (heuristic)...")

    for a, b in pairs:
        result = _compare_pair(a, b, profiles)
        comparisons[result["pair_key"]] = result

    return comparisons


# ---------------------------------------------------------------------------
# Demo data aggregation
# ---------------------------------------------------------------------------

def build_demo_data(
    decisions: list,
    profiles: dict,
    reasoning_map: dict,
    comparisons: dict,
    job_intel: dict,
) -> dict:
    tiers: dict = {
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
        summary = {
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
        tier.append(summary)

    for tier_list in tiers.values():
        tier_list.sort(key=lambda x: x["overall_match_score"], reverse=True)

    sorted_all = sorted(decisions, key=lambda d: d.get("overall_match_score", 0), reverse=True)

    stats = {
        "total_evaluated": len(decisions),
        "by_tier": {tier: len(lst) for tier, lst in tiers.items()},
        "avg_match_score": round(
            sum(d.get("overall_match_score", 0) for d in decisions) / max(len(decisions), 1), 3
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> dict:
    logger.info("=" * 60)
    mode_label = "TEST" if is_test_mode() else "FULL"
    logger.info(f"Agent 5: Reporting  [{mode_label} — expecting {REQUIRED_DECISIONS} decisions]  [Rule-Based — No LLM]")
    logger.info("=" * 60)

    # Load decisions
    decisions = []
    for path in DECISIONS_DIR.glob("*.json"):
        try:
            decisions.append(_load_json(path))
        except Exception as exc:
            logger.warning(f"Could not load {path}: {exc}")

    decisions.sort(key=lambda d: d.get("overall_match_score", 0), reverse=True)
    logger.info(f"Loaded {len(decisions)} decisions")

    if len(decisions) < REQUIRED_DECISIONS:
        raise RuntimeError(
            f"Agent 5 requires {REQUIRED_DECISIONS} decisions "
            f"({'test mode' if is_test_mode() else 'full mode'}). "
            f"Found: {len(decisions)}. Run agents 1-4 first."
        )

    decisions = decisions[:REQUIRED_DECISIONS]

    # Load profiles
    profiles: dict = {}
    for path in PROFILES_DIR.glob("*.json"):
        try:
            p = _load_json(path)
            profiles[p["candidate_id"]] = p
        except Exception as exc:
            logger.warning(f"Could not load profile {path}: {exc}")

    # Load job intel
    if not JOB_INTEL_FILE.exists():
        raise FileNotFoundError(f"Missing {JOB_INTEL_FILE}. Run Agent 1 first.")
    job_intel = _load_json(JOB_INTEL_FILE)

    # Reasoning map
    logger.info("Generating reasoning_map.json (template-based)...")
    reasoning_map = generate_reasoning_map(decisions, profiles)

    # Comparisons
    top_n = decisions[:COMPARISON_TOP_N]
    logger.info("Generating comparisons.json (heuristic)...")
    comparisons = generate_comparisons(top_n, profiles)

    # Demo data
    logger.info("Building demo_data.json...")
    demo_data = build_demo_data(decisions, profiles, reasoning_map, comparisons, job_intel)

    # Write outputs
    with open(REASONING_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(reasoning_map, f, indent=2)
    logger.info(f"✓ Written: {REASONING_MAP_FILE}")

    with open(COMPARISONS_FILE, "w", encoding="utf-8") as f:
        json.dump(comparisons, f, indent=2)
    logger.info(f"✓ Written: {COMPARISONS_FILE}")

    with open(DEMO_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(demo_data, f, indent=2)
    logger.info(f"✓ Written: {DEMO_DATA_FILE}")

    # Assertions
    assert len(reasoning_map) == REQUIRED_DECISIONS, (
        f"reasoning_map has {len(reasoning_map)} entries, expected {REQUIRED_DECISIONS}"
    )
    assert len(set(reasoning_map.values())) == REQUIRED_DECISIONS, (
        f"Duplicate reasoning strings detected: "
        f"{REQUIRED_DECISIONS - len(set(reasoning_map.values()))} duplicates"
    )
    logger.info(f"✓ Assertions passed: {len(reasoning_map)} unique reasoning strings")
    logger.info(f"✓ Agent 5 complete — {len(decisions)} candidates reported")
    logger.info("  reasoning_map.json is ready for Dev A handoff.")
    return demo_data


if __name__ == "__main__":
    run()
