"""
Agent 2 — Candidate Intelligence Agent (Rule-Based, No LLM)
Reads:   DATASET_DIR/candidates.jsonl         (full 100K dataset, default)
         DATASET_DIR/sample_candidates.json   (50-candidate test set, --test mode)
Outputs: precomputed/candidate_profiles/CAND_XXXXXXX.json  (one file per candidate)

Never imports from src/scoring/ or src/pipeline/.
Checkpoints: skips candidates whose profile file already exists.
"""

import json
import logging
import re
from pathlib import Path
from typing import Iterator

from src.intelligence.paths import (
    CANDIDATES_JSONL,
    PROFILES_DIR,
    ROOT,
    SAMPLE_CANDIDATES_JSON,
    is_test_mode,
    top_candidates,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent2-Cand] %(message)s")
logger = logging.getLogger(__name__)

FAST_SCORES_FILE = ROOT / "candidates_fast_scores.jsonl"
TOP_N = top_candidates()  # 50 in test mode, 500 in full mode

CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "hcl", "capgemini",
    "tech mahindra", "mphasis", "hexaware", "l&t infotech", "mindtree",
    "deloitte", "kpmg", "pwc", "ey", "ernst & young", "mckinsey", "bain",
    "bcg", "boston consulting", "booz allen", "ibm consulting",
}

OWNERSHIP_VERBS = {
    "led", "built", "owned", "designed", "architected", "launched", "founded",
    "created", "developed", "drove", "spearheaded", "established", "pioneered",
    "initiated", "managed", "directed", "oversee", "oversaw", "defined",
}

OUTCOME_PATTERNS = [
    r"\d+%", r"\$\d+", r"\d+x", r"increased", r"decreased", r"reduced",
    r"improved", r"grew", r"achieved", r"delivered", r"generated", r"saved",
    r"scaled", r"shipped", r"launched",
]

AI_KEYWORDS = {
    "machine learning", "deep learning", "nlp", "natural language", "llm",
    "gpt", "transformer", "neural", "pytorch", "tensorflow", "data science",
    "ml", "ai", "artificial intelligence", "computer vision", "recommendation",
}

ENGINEER_POSITIVE = {
    "ml engineer", "ai engineer", "machine learning engineer", "data scientist",
    "research engineer", "applied scientist", "applied ml", "nlp engineer",
    "senior engineer", "staff engineer", "principal engineer", "tech lead",
    "software engineer", "backend engineer", "platform engineer",
}

BAD_TITLES = {
    "marketing", "sales", "accounting", "hr manager", "recruiter",
    "admin", "customer support", "data entry",
}


# ---------------------------------------------------------------------------
# Fast scorer
# ---------------------------------------------------------------------------

def _keyword_fast_score(candidate: dict) -> float:
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])

    title = profile.get("current_title", "").lower()
    skill_names = set()
    for s in skills:
        name = s.get("name", "").lower() if isinstance(s, dict) else str(s).lower()
        skill_names.add(name)

    score = 0.0
    if any(eng in title for eng in ENGINEER_POSITIVE):
        score += 20.0
    if any(bad in title for bad in BAD_TITLES):
        score -= 25.0

    ai_count = sum(1 for s in skill_names if any(kw in s for kw in AI_KEYWORDS))
    score += min(ai_count * 5, 20)

    yoe = float(profile.get("years_of_experience", 0) or 0)
    score += min(yoe * 2, 15)
    score += min(len(career) * 2, 10)

    for job in career:
        company = (job.get("company") or "").lower()
        if not any(cons in company for cons in CONSULTING_COMPANIES):
            score += 3
        break

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

def _iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _candidate_name(candidate: dict) -> str:
    profile = candidate.get("profile", {})
    return profile.get("anonymized_name") or profile.get("name", "")


def _load_top_candidates() -> list:
    if is_test_mode():
        if not SAMPLE_CANDIDATES_JSON.exists():
            logger.error(f"Test mode active but sample file not found: {SAMPLE_CANDIDATES_JSON}")
            return []
        logger.info(f"TEST MODE — loading {SAMPLE_CANDIDATES_JSON.name}")
        with open(SAMPLE_CANDIDATES_JSON, encoding="utf-8") as f:
            candidates = json.load(f)
        if not isinstance(candidates, list):
            candidates = [candidates]
        for c in candidates:
            if "fast_score" not in c:
                c["fast_score"] = _keyword_fast_score(c)
        logger.info(f"  {len(candidates)} sample candidates loaded")
        return candidates

    if FAST_SCORES_FILE.exists():
        logger.info(f"Loading pre-scored file: {FAST_SCORES_FILE.name}")
        candidates = list(_iter_jsonl(FAST_SCORES_FILE))
        for c in candidates:
            if "fast_score" not in c:
                c["fast_score"] = _keyword_fast_score(c)
    elif CANDIDATES_JSONL.exists():
        import heapq
        mb = CANDIDATES_JSONL.stat().st_size // 1024 // 1024
        logger.info(f"Streaming {CANDIDATES_JSONL.name} ({mb} MB) — fast-scoring top-{TOP_N}...")
        heap: list = []
        total = 0
        for c in _iter_jsonl(CANDIDATES_JSONL):
            total += 1
            score = _keyword_fast_score(c)
            c["fast_score"] = score
            if len(heap) < TOP_N:
                heapq.heappush(heap, (score, c))
            elif score > heap[0][0]:
                heapq.heapreplace(heap, (score, c))
            if total % 10_000 == 0:
                logger.info(f"  Scanned {total:,} candidates...")
        candidates = [c for _, c in heap]
        logger.info(f"  Scanned {total:,} total candidates")
    else:
        logger.error(
            f"No candidate data found.\n"
            f"  Expected: {CANDIDATES_JSONL}\n"
            f"  Or run with --test to use sample_candidates.json"
        )
        return []

    candidates.sort(key=lambda c: c.get("fast_score", 0), reverse=True)
    top = candidates[:TOP_N]
    logger.info(f"Selected top {len(top)} candidates")
    return top


# ---------------------------------------------------------------------------
# Heuristic metrics
# ---------------------------------------------------------------------------

def _career_text(candidate: dict) -> str:
    return " ".join(
        (job.get("description", "") or "") for job in candidate.get("career_history", [])
    ).lower()


def _ownership_language_score(candidate: dict) -> float:
    text = _career_text(candidate)
    words = text.split()
    if not words:
        return 0.0
    hits = sum(1 for w in words if w.rstrip(".,;") in OWNERSHIP_VERBS)
    return min(hits / max(len(words) / 20, 1), 1.0)


def _outcome_language_score(candidate: dict) -> float:
    text = _career_text(candidate)
    hits = sum(1 for pat in OUTCOME_PATTERNS if re.search(pat, text))
    return min(hits / len(OUTCOME_PATTERNS), 1.0)


def _skill_duration_credible(candidate: dict) -> bool:
    total_months = sum(
        int(j.get("duration_months", 0) or 0)
        for j in candidate.get("career_history", [])
    )
    for skill in candidate.get("skills", []):
        if not isinstance(skill, dict):
            continue
        claimed_months = int(skill.get("duration_months", 0) or 0)
        if claimed_months > total_months + 24:
            return False
    return True


def _product_company_fraction(candidate: dict) -> float:
    jobs = candidate.get("career_history", [])
    if not jobs:
        return 0.0
    product_months = 0
    total_months = 0
    for job in jobs:
        months = int(job.get("duration_months", 0) or 0)
        company = (job.get("company") or "").lower()
        total_months += months
        if not any(cons in company for cons in CONSULTING_COMPANIES):
            product_months += months
    return product_months / total_months if total_months else 0.0


def _consistency_score(candidate: dict) -> float:
    score = 0.7
    profile = candidate.get("profile", {})
    title = (profile.get("current_title") or "").lower()
    skills = [
        (s.get("name") or "").lower() if isinstance(s, dict) else str(s).lower()
        for s in candidate.get("skills", [])
    ]
    career = candidate.get("career_history", [])

    eng_title = any(kw in title for kw in {"engineer", "scientist", "developer", "ml", "ai"})
    has_tech_skill = any(
        any(p in s for p in {"python", "ml", "ai", "llm", "model", "data", "engineer"})
        for s in skills
    )
    if eng_title and not has_tech_skill and skills:
        score -= 0.15

    if len(career) >= 2:
        score += 0.15

    short_tenures = sum(1 for j in career if int(j.get("duration_months", 12) or 12) < 6)
    if career and short_tenures / len(career) > 0.4:
        score -= 0.2

    return max(0.0, min(1.0, score))


def _top_skills(candidate: dict, n: int = 8) -> list:
    result = []
    for s in candidate.get("skills", []):
        name = s.get("name") or "" if isinstance(s, dict) else str(s)
        if name:
            result.append(name)
    return result[:n]


def _career_trajectory(candidate: dict) -> str:
    career = candidate.get("career_history", [])
    if len(career) < 2:
        return "unknown"
    seniority_words = {
        "junior": 1, "associate": 2, "mid": 3, "senior": 4,
        "lead": 5, "principal": 6, "staff": 6,
        "manager": 5, "director": 7, "vp": 8, "head": 7,
        "chief": 9,
    }

    def title_rank(title: str) -> int:
        t = title.lower()
        for word, rank in seniority_words.items():
            if word in t:
                return rank
        return 3

    ranks = [title_rank(j.get("title", "")) for j in career]
    diffs = [ranks[i + 1] - ranks[i] for i in range(len(ranks) - 1)]
    if not diffs:
        return "mixed"
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff > 0.3:
        return "upward"
    elif avg_diff < -0.3:
        return "downward"
    elif all(abs(d) <= 1 for d in diffs):
        return "lateral"
    return "mixed"


def _total_months(candidate: dict) -> int:
    return sum(
        int(j.get("duration_months", 0) or 0)
        for j in candidate.get("career_history", [])
    )


# ---------------------------------------------------------------------------
# Narrative type (rule-based, spec-aligned values)
# ---------------------------------------------------------------------------

def _heuristic_narrative_type(candidate: dict) -> str:
    """
    Returns one of the spec-defined types:
    DEEPENING_SPECIALIST / DOMAIN_PIVOTING / GENERALIST_BROADENING / STAGNANT / INCOHERENT
    """
    career = candidate.get("career_history", [])
    frac = _product_company_fraction(candidate)

    # Heavy consulting background = INCOHERENT (no clear product narrative)
    if frac < 0.3 and len(career) >= 2:
        return "INCOHERENT"

    profile = candidate.get("profile", {})
    title = (profile.get("current_title") or "").lower()
    skills = _top_skills(candidate, 10)
    skill_domains = {s.split()[0].lower() for s in skills if s}
    trajectory = _career_trajectory(candidate)

    # Stagnant: 3+ roles with no title progression
    if len(career) >= 3:
        titles = [j.get("title", "").lower() for j in career]
        if len(set(titles)) == 1 or trajectory == "downward":
            return "STAGNANT"

    # Domain pivot: changed domain significantly (e.g., SWE → Data Scientist → PM)
    if len(career) >= 2:
        role_domains = []
        for j in career:
            t = j.get("title", "").lower()
            if any(w in t for w in ("data", "ml", "ai", "science")):
                role_domains.append("data")
            elif any(w in t for w in ("product", "pm", "manager")):
                role_domains.append("product")
            elif any(w in t for w in ("engineer", "developer", "swe", "backend", "frontend")):
                role_domains.append("engineering")
            else:
                role_domains.append("other")
        unique_domains = set(role_domains)
        if len(unique_domains) >= 3:
            return "DOMAIN_PIVOTING"
        if len(unique_domains) == 2 and "other" not in unique_domains:
            return "DOMAIN_PIVOTING"

    # Generalist: broad skills across many areas
    if len(skill_domains) >= 6:
        return "GENERALIST_BROADENING"

    # Deepening specialist: upward/lateral in same domain
    if trajectory in ("upward", "lateral") and len(skill_domains) <= 4:
        return "DEEPENING_SPECIALIST"

    return "DEEPENING_SPECIALIST"


# ---------------------------------------------------------------------------
# Red/green flags
# ---------------------------------------------------------------------------

def _flags(candidate: dict) -> tuple:
    red, green = [], []
    career = candidate.get("career_history", [])
    redrob = candidate.get("redrob_signals", {})

    short = [j for j in career if int(j.get("duration_months", 12) or 12) < 8]
    if len(short) >= 3:
        red.append(f"{len(short)} roles shorter than 8 months — pattern of job hopping")

    frac = _product_company_fraction(candidate)
    if frac < 0.3:
        red.append("Majority career at service/consulting firms — limited product ownership")

    interview_rate = redrob.get("interview_completion_rate", 1.0) or 1.0
    if interview_rate < 0.5:
        red.append(f"Low interview completion rate ({int(interview_rate * 100)}%) — potential reliability risk")

    offer_rate = redrob.get("offer_acceptance_rate", -1)
    if offer_rate != -1 and offer_rate < 0.25:
        red.append(f"Low offer acceptance rate ({int(offer_rate * 100)}%) — may use offers as leverage")

    long_roles = [j for j in career if int(j.get("duration_months", 0) or 0) >= 24]
    if long_roles:
        green.append(f"{len(long_roles)} role(s) with 2+ years tenure — demonstrates commitment")

    github_score = redrob.get("github_activity_score", -1)
    if github_score is not None and github_score >= 50:
        green.append(f"Active GitHub contributor (score: {int(github_score)}/100) — verifiable technical output")

    if redrob.get("open_to_work_flag", False):
        notice = redrob.get("notice_period_days", 30)
        green.append(f"Actively open to work, {notice}-day notice — immediately actionable")

    skill_assessments = redrob.get("skill_assessment_scores", {})
    high_assessments = {k: v for k, v in skill_assessments.items() if v >= 75}
    if high_assessments:
        top_skill = max(high_assessments, key=high_assessments.get)
        green.append(f"Platform-verified skill score: {top_skill} {int(high_assessments[top_skill])}/100")

    product_companies = {
        "google", "meta", "apple", "amazon", "microsoft", "stripe", "airbnb",
        "netflix", "spotify", "uber", "lyft", "linkedin", "twitter", "slack",
        "figma", "notion", "databricks", "snowflake", "openai", "anthropic",
    }
    for job in career:
        company = (job.get("company") or "").lower()
        for pc in product_companies:
            if pc in company:
                green.append(f"Experience at tier-1 product company: {job.get('company')}")
                break

    return red[:3], green[:4]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> list:
    logger.info("=" * 60)
    mode_label = "TEST MODE — sample_candidates.json" if is_test_mode() else "FULL MODE — candidates.jsonl"
    logger.info(f"Agent 2: Candidate Intelligence  [{mode_label}]  [Rule-Based — No LLM]")
    logger.info("=" * 60)

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    candidates = _load_top_candidates()
    if not candidates:
        logger.error("No candidates to process.")
        return []

    processed = 0
    skipped = 0
    failed = 0

    for candidate in candidates:
        cid = candidate.get("candidate_id", "UNKNOWN")
        out_path = PROFILES_DIR / f"{cid}.json"

        if out_path.exists():
            skipped += 1
            continue

        try:
            profile = candidate.get("profile", {})
            redrob = candidate.get("redrob_signals", {})
            red, green = _flags(candidate)
            narrative_type = _heuristic_narrative_type(candidate)

            data = {
                "candidate_id": cid,
                "name": _candidate_name(candidate),
                "current_title": profile.get("current_title", ""),
                "current_company": profile.get("current_company", ""),
                "narrative_type": narrative_type,
                "consistency_score": round(_consistency_score(candidate), 3),
                "skill_duration_credible": _skill_duration_credible(candidate),
                "ownership_language_score": round(_ownership_language_score(candidate), 3),
                "outcome_language_score": round(_outcome_language_score(candidate), 3),
                "product_company_fraction": round(_product_company_fraction(candidate), 3),
                "top_skills": _top_skills(candidate),
                "career_trajectory": _career_trajectory(candidate),
                "red_flags": red,
                "green_flags": green,
                "fast_score": round(float(candidate.get("fast_score", 0)), 2),
                "years_of_experience": float(profile.get("years_of_experience", 0) or 0),
                "total_months": _total_months(candidate),
                "redrob_trust": {
                    "verified_email": redrob.get("verified_email", False),
                    "verified_phone": redrob.get("verified_phone", False),
                    "github_activity_score": redrob.get("github_activity_score", -1),
                    "profile_completeness_score": redrob.get("profile_completeness_score", 0),
                    "interview_completion_rate": redrob.get("interview_completion_rate", 1.0),
                    "offer_acceptance_rate": redrob.get("offer_acceptance_rate", -1),
                    "open_to_work_flag": redrob.get("open_to_work_flag", False),
                    "notice_period_days": redrob.get("notice_period_days", 30),
                    "skill_assessment_scores": redrob.get("skill_assessment_scores", {}),
                },
            }

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            processed += 1

        except Exception as exc:
            logger.warning(f"  x {cid}: {exc}")
            failed += 1

    logger.info(f"✓ Agent 2 complete — processed: {processed}, skipped: {skipped}, failed: {failed}")
    return [
        json.loads(open(PROFILES_DIR / f"{c.get('candidate_id')}.json").read())
        for c in candidates
        if (PROFILES_DIR / f"{c.get('candidate_id')}.json").exists()
    ]


if __name__ == "__main__":
    run()
