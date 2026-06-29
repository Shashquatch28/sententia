"""
Agent 3 — Matching Intelligence Agent (Rule-Based, No LLM)
Reads:   precomputed/candidate_profiles/*.json  (top-200 full / top-50 test)
         precomputed/job_intelligence.json
Outputs: precomputed/match_scores/CAND_XXXXXXX.json  (one per candidate)

Scores candidates against the job discriminator hierarchy using keyword overlap
and profile metrics computed by Agent 2. No API calls required.

Never imports from src/scoring/ or src/pipeline/.
Checkpoints: skips candidates whose match score file already exists.
"""

import json
import logging
from pathlib import Path

from src.intelligence.paths import (
    JOB_INTEL_FILE,
    MATCH_DIR,
    PROFILES_DIR,
    is_test_mode,
    top_profiles,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent3-Match] %(message)s")
logger = logging.getLogger(__name__)

TOP_N = top_profiles()   # 50 in test mode, 200 in full mode

# Keyword sets for each discriminator (matched against candidate skills)
_LLM_RAG_KEYWORDS = {
    "llm", "rag", "embedding", "transformer", "gpt", "openai", "anthropic",
    "langchain", "llamaindex", "bert", "nlp", "natural language", "fine-tuning",
    "fine tuning", "language model", "semantic search", "vector", "retrieval",
    "machine learning", "deep learning", "neural", "pytorch", "tensorflow",
    "huggingface", "hugging face", "diffusion", "generative ai", "stable diffusion",
    "text generation", "information retrieval",
}

_MLOPS_KEYWORDS = {
    "python", "fastapi", "flask", "docker", "kubernetes", "k8s",
    "aws", "gcp", "azure", "cloud", "pinecone", "weaviate", "chroma",
    "pgvector", "qdrant", "milvus", "mlflow", "wandb", "weights & biases",
    "ci/cd", "terraform", "redis", "kafka", "airflow", "spark", "celery",
    "model serving", "triton", "torchserve", "bento", "ray",
}

_ENGINEER_TITLE_BOOST = {
    "applied", "platform", "ml engineer", "ai engineer",
    "machine learning engineer", "data scientist", "research engineer",
}


def _load_job_intelligence() -> dict:
    if not JOB_INTEL_FILE.exists():
        raise FileNotFoundError(f"Missing {JOB_INTEL_FILE}. Run Agent 1 first.")
    with open(JOB_INTEL_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_top_profiles(n: int = TOP_N) -> list:
    profiles = []
    for path in PROFILES_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                profiles.append(json.load(f))
        except Exception as exc:
            logger.warning(f"Could not load {path}: {exc}")
    profiles.sort(key=lambda p: p.get("fast_score", 0), reverse=True)
    top = profiles[:n]
    logger.info(f"Loaded {len(top)} profiles (pool: {len(profiles)})")
    return top


def _load_profiles_for_ids(candidate_ids: list[str]) -> list[dict]:
    if not candidate_ids:
        return []

    wanted = list(dict.fromkeys(candidate_ids))
    by_id: dict[str, dict] = {}

    for cid in wanted:
        path = PROFILES_DIR / f"{cid}.json"
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                by_id[cid] = json.load(f)
        except Exception as exc:
            logger.warning(f"Could not load {path}: {exc}")

    missing = [cid for cid in wanted if cid not in by_id]
    if missing:
        logger.warning("Missing %d profile(s) from shared ranking manifest", len(missing))

    return [by_id[cid] for cid in wanted if cid in by_id]


def _skill_hit(skills_lower: set, keywords: set) -> int:
    """Count how many keywords appear in the candidate's skill set."""
    return sum(1 for s in skills_lower if any(kw in s for kw in keywords))


def _score_candidate(profile: dict, discriminators: list) -> dict:
    """Heuristic scoring against all 5 discriminators."""
    skills_lower = {s.lower() for s in profile.get("top_skills", [])}
    title = profile.get("current_title", "").lower()
    yoe = float(profile.get("years_of_experience", 0) or 0)
    ownership_score = profile.get("ownership_language_score", 0)
    outcome_score = profile.get("outcome_language_score", 0)
    product_frac = profile.get("product_company_fraction", 0)
    narrative_type = profile.get("narrative_type", "")
    trajectory = profile.get("career_trajectory", "mixed")
    redrob = profile.get("redrob_trust", {})

    # --- Discriminator 1: LLM & RAG Engineering (weight 0.35) ---
    llm_hits = _skill_hit(skills_lower, _LLM_RAG_KEYWORDS)
    github = redrob.get("github_activity_score", -1) or -1
    assessments = redrob.get("skill_assessment_scores", {}) or {}

    llm_score = min(llm_hits / 4, 0.80)
    if github >= 70:
        llm_score = min(llm_score + 0.15, 1.0)
    elif github >= 50:
        llm_score = min(llm_score + 0.08, 1.0)
    if any(v >= 75 for v in assessments.values()):
        llm_score = min(llm_score + 0.10, 1.0)

    # --- Discriminator 2: Product-Sense & User-Facing AI (weight 0.25) ---
    product_score = 0.25
    product_score += product_frac * 0.45
    product_score += outcome_score * 0.20
    if any(kw in title for kw in _ENGINEER_TITLE_BOOST):
        product_score += 0.10
    product_score = min(product_score, 1.0)

    # --- Discriminator 3: Founding-Team Ownership (weight 0.20) ---
    ownership_disc = 0.25
    ownership_disc += ownership_score * 0.35
    if trajectory == "upward":
        ownership_disc += 0.20
    elif trajectory == "lateral":
        ownership_disc += 0.10
    if narrative_type in ("DEEPENING_SPECIALIST", "DOMAIN_PIVOTING"):
        ownership_disc += 0.15
    ownership_disc = min(ownership_disc, 1.0)

    # --- Discriminator 4: Python & MLOps Stack (weight 0.12) ---
    mlops_hits = _skill_hit(skills_lower, _MLOPS_KEYWORDS)
    mlops_score = min(mlops_hits / 3, 1.0)

    # --- Discriminator 5: Communication & Cross-Functional Fit (weight 0.08) ---
    comm_score = 0.45
    if yoe >= 7:
        comm_score += 0.25
    elif yoe >= 5:
        comm_score += 0.15
    elif yoe >= 3:
        comm_score += 0.05
    if any(kw in title for kw in ("senior", "lead", "staff", "principal", "head")):
        comm_score += 0.15
    comm_score += outcome_score * 0.10
    comm_score = min(comm_score, 1.0)

    # Build discriminator score map aligned to job_intel discriminator names
    disc_name_map = {
        "LLM & RAG Engineering": llm_score,
        "Product-Sense & User-Facing AI": product_score,
        "Founding-Team Ownership": ownership_disc,
        "Python & MLOps Stack": mlops_score,
        "Communication & Cross-Functional Fit": comm_score,
    }

    # Use actual names + weights from job_intel discriminators
    weights_used = {}
    disc_scores_out = {}
    for disc in discriminators:
        name = disc["name"]
        weight = disc.get("weight", 0.1)
        # Find matching score by name (partial match for flexibility)
        matched_score = 0.5
        for key, val in disc_name_map.items():
            if key.lower().startswith(name.lower()[:6]) or name.lower()[:6] in key.lower():
                matched_score = val
                break
        disc_scores_out[name] = round(matched_score, 3)
        weights_used[name] = weight

    # Weighted overall score
    total_weight = sum(weights_used.values()) or 1.0
    overall = sum(
        disc_scores_out.get(name, 0.5) * w
        for name, w in weights_used.items()
    ) / total_weight

    # Matched skills
    matched = [
        s for s in profile.get("top_skills", [])
        if any(kw in s.lower() for kw in _LLM_RAG_KEYWORDS | _MLOPS_KEYWORDS)
    ][:5]

    # Gaps
    gaps = []
    if llm_score < 0.30:
        gaps.append("Limited LLM/RAG engineering skills — core requirement not met")
    if product_score < 0.35:
        gaps.append("Limited product company or user-facing AI experience")
    if mlops_score < 0.30:
        gaps.append("MLOps/deployment stack not evident in skill profile")
    if yoe < 5:
        gaps.append(f"Under-qualified: {yoe:.0f} yrs experience vs 5+ required")
    if product_frac < 0.3:
        gaps.append("Majority career at consulting/service firms — limited product ownership")

    # Evidence strings
    name = profile.get("name", "Candidate")
    title_str = profile.get("current_title", "")
    company_str = profile.get("current_company", "")
    evidence = []
    if matched:
        evidence.append(
            f"{name} ({title_str} at {company_str}) — {', '.join(matched[:2])} "
            f"match LLM/RAG core requirements"
        )
    if product_frac > 0.6:
        evidence.append(f"{int(product_frac * 100)}% of career at product companies — strong user-facing context")
    elif product_frac > 0.3:
        evidence.append(f"{int(product_frac * 100)}% product company exposure")
    if ownership_score > 0.4:
        evidence.append("Ownership language in career history signals initiative and scope")
    if trajectory == "upward":
        evidence.append("Upward career trajectory — progressive responsibility growth")
    if not evidence:
        skills_preview = profile.get("top_skills", [])
        if skills_preview:
            evidence.append(f"{name} brings {', '.join(skills_preview[:3])} to the role")

    return {
        "discriminator_scores": disc_scores_out,
        "required_skills_matched": matched,
        "identified_gaps": gaps[:4],
        "overall_match_score": round(overall, 3),
        "match_evidence": evidence[:3],
    }


def run(candidate_ids: list[str] | None = None) -> list:
    logger.info("=" * 60)
    mode_label = "TEST" if is_test_mode() else "FULL"
    logger.info(f"Agent 3: Matching Intelligence  [{mode_label} — top-{TOP_N}]  [Rule-Based — No LLM]")
    logger.info("=" * 60)

    MATCH_DIR.mkdir(parents=True, exist_ok=True)

    job_intel = _load_job_intelligence()
    discriminators = job_intel.get("discriminator_hierarchy", [])
    logger.info(f"Role: {job_intel.get('role_summary', '')[:80]}...")

    if candidate_ids:
        logger.info(f"Using shared ranked candidate set ({len(candidate_ids)} candidates)")
        profiles = _load_profiles_for_ids(candidate_ids)
    else:
        profiles = _load_top_profiles(TOP_N)

    pending = [
        p for p in profiles
        if not (MATCH_DIR / f"{p['candidate_id']}.json").exists()
    ]
    logger.info(f"Pending: {len(pending)} | Already scored: {len(profiles) - len(pending)}")

    processed = 0
    failed = 0

    for i, profile in enumerate(pending):
        cid = profile["candidate_id"]
        if (i + 1) % 25 == 0 or i == 0:
            logger.info(f"  [{i + 1}/{len(pending)}] scoring {cid}...")

        try:
            score = _score_candidate(profile, discriminators)
            score["candidate_id"] = cid

            out_path = MATCH_DIR / f"{cid}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(score, f, indent=2)
            processed += 1

        except Exception as exc:
            logger.warning(f"  x {cid}: {exc}")
            fallback = {
                "candidate_id": cid,
                "discriminator_scores": {},
                "required_skills_matched": [],
                "identified_gaps": ["Scoring failed"],
                "overall_match_score": profile.get("fast_score", 0) / 100.0,
                "match_evidence": [],
            }
            out_path = MATCH_DIR / f"{cid}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(fallback, f, indent=2)
            failed += 1

    logger.info(f"✓ Agent 3 complete — processed: {processed}, failed: {failed}")

    all_scores = []
    for p in profiles:
        path = MATCH_DIR / f"{p['candidate_id']}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                all_scores.append(json.load(f))
    return all_scores


if __name__ == "__main__":
    run()
