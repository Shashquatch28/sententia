"""
Agent 1 — Job Intelligence Agent (Rule-Based, No LLM)
Reads:   DATASET_DIR/job_description.docx   (primary)
         job_description.md                 (fallback)
Outputs: precomputed/job_intelligence.json

Checkpoints: skips if output already exists.
Never imports from src/scoring/ or src/pipeline/.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from src.intelligence.docx_reader import read_docx_safe
from src.intelligence.paths import (
    JD_DOCX,
    JD_MD_FALLBACK,
    JOB_INTEL_FILE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent1-Job] %(message)s")
logger = logging.getLogger(__name__)


def _load_jd_text() -> str:
    if JD_DOCX.exists():
        text = read_docx_safe(JD_DOCX)
        if text.strip():
            logger.info(f"  JD source : {JD_DOCX.name} ({len(text):,} chars)")
            return text
        logger.warning(f"  {JD_DOCX.name} extracted empty — falling back to markdown")
    if JD_MD_FALLBACK.exists():
        text = JD_MD_FALLBACK.read_text(encoding="utf-8")
        logger.info(f"  JD source : {JD_MD_FALLBACK.name} ({len(text):,} chars)")
        return text
    logger.error(f"No job description found. Expected:\n  {JD_DOCX}\n  {JD_MD_FALLBACK}")
    sys.exit(1)


def _extract_culture_signals(text_lower: str) -> list:
    patterns = [
        ("founding", "Founding-team environment — early hire shaping technical culture from the ground up"),
        ("fast", "Fast-paced execution bias — values shipping over perfecting"),
        ("ownership", "High ownership expected — autonomous end-to-end responsibility"),
        ("series a", "Series A stage — scrappy, high-upside environment with limited process overhead"),
        ("product", "Product-minded engineers preferred — user impact matters as much as code quality"),
        ("collaborat", "Collaborative cross-functional culture — close work with PM, design, and business"),
        ("impact", "Impact-driven — quantified outcomes expected, not activity metrics"),
        ("ai-native", "AI-native company — AI tooling is the default, not an add-on"),
        ("talent", "Talent-intelligence domain — builds tools that directly shape hiring decisions"),
        ("startup", "Startup mindset — initiative and adaptability valued over process adherence"),
        ("scale", "Scale ambitions — building for growth from day one"),
        ("autonomy", "High autonomy — engineers own decisions without waiting for approval"),
    ]
    signals = []
    for keyword, signal in patterns:
        if keyword in text_lower:
            signals.append(signal)
    if len(signals) < 5:
        signals += [
            "Technical depth expected — senior IC role with lead-level scope and accountability",
            "Bias towards proven product builders who have shipped ML systems to real users",
        ]
    return signals[:10]


def _extract_role_summary(lines: list) -> str:
    body = [l for l in lines[:20] if len(l) > 40 and not l.startswith("#")]
    if body:
        return " ".join(body[:2])
    return (
        "Senior AI Engineer at Redrob AI (Series A, AI-native talent intelligence platform). "
        "Builds LLM/RAG pipelines powering AI-driven recruitment products. "
        "Founding-team hire responsible for end-to-end AI feature development."
    )


def _analyze_rule_based(jd_text: str) -> dict:
    text_lower = jd_text.lower()
    lines = [l.strip() for l in jd_text.split("\n") if l.strip()]

    return {
        "role_summary": _extract_role_summary(lines),
        "implicit_requirements": [
            "Comfort with ambiguity — founding-team scope will evolve rapidly without clear specs",
            "Self-directed learning — AI field changes fast, must stay current independently",
            "Async communication skills — distributed/remote-friendly work style implied",
            "Context-switching tolerance — early-stage means wearing multiple hats",
            "Production ML experience — notebook/research background alone is insufficient",
            "Rapid iteration mindset — MVP ships first, polish follows signal",
            "Ability to translate business needs into technical requirements without heavy PM support",
        ],
        "culture_signals": _extract_culture_signals(text_lower),
        "ideal_candidate_narrative": (
            "The ideal hire is a senior ML engineer with 5-8 years experience who has built LLM or RAG "
            "pipelines at a product company and shipped them to real users at scale. They have worked at "
            "a startup or early-stage team, own work end-to-end, and speak in outcomes (latency reduced "
            "40%, recall improved to 87%). They are Python-native with hands-on vector DB and model "
            "deployment experience, and excited to join a founding team where their architecture decisions "
            "shape the product roadmap."
        ),
        "discriminator_hierarchy": [
            {
                "rank": 1,
                "name": "LLM & RAG Engineering",
                "weight": 0.35,
                "description": "Core capability — building production LLM/RAG pipelines is the primary function at Redrob AI",
                "signals": [
                    "skills[].name contains: LLM, RAG, embedding, transformer, GPT, OpenAI, Anthropic, LangChain, LlamaIndex, BERT",
                    "skills[].name contains: NLP, natural language processing, semantic search, vector database",
                    "career_history[].description mentions building/fine-tuning/deploying language models in production",
                    "github_activity_score >= 50 — verifiable AI/ML open-source contributions",
                    "skill_assessment_scores contains ML/AI skill with score >= 70",
                ],
            },
            {
                "rank": 2,
                "name": "Product-Sense & User-Facing AI",
                "weight": 0.25,
                "description": "Must build AI features real users interact with — not just internal tooling or research prototypes",
                "signals": [
                    "career_history[].company is a product company (not consulting/services firm)",
                    "career_history[].description mentions A/B tests, user metrics, or feature launches",
                    "outcome_language_score > 0.4 — quantified user/business impact in role descriptions",
                    "current_title contains: Applied, Platform, Product AI Engineer at product company",
                    "product_company_fraction > 0.6",
                ],
            },
            {
                "rank": 3,
                "name": "Founding-Team Ownership",
                "weight": 0.20,
                "description": "Early-stage hire must own deliverables end-to-end — architecture to deployment without hand-holding",
                "signals": [
                    "career_history includes startup (pre-Series B) or founding/early-stage role",
                    "ownership_language_score > 0.5 — 'led', 'built', 'architected', 'launched' language",
                    "narrative_type is DEEPENING_SPECIALIST or DOMAIN_PIVOTING (not STAGNANT or INCOHERENT)",
                    "career_trajectory is upward",
                    "career_history shows IC to senior-scope progression over time",
                ],
            },
            {
                "rank": 4,
                "name": "Python & MLOps Stack",
                "weight": 0.12,
                "description": "Must deploy and maintain ML models in production — cloud, containers, monitoring",
                "signals": [
                    "skills[].name contains: Python, FastAPI, Flask, Docker, Kubernetes",
                    "skills[].name contains: AWS, GCP, Azure — cloud deployment experience",
                    "skills[].name contains: Pinecone, Weaviate, Chroma, pgvector, Qdrant (vector DBs)",
                    "skills[].name contains: MLflow, Weights & Biases, model monitoring tooling",
                    "career_history[].description mentions CI/CD, model serving, or production deployment",
                ],
            },
            {
                "rank": 5,
                "name": "Communication & Cross-Functional Fit",
                "weight": 0.08,
                "description": "Senior IC must translate technical concepts clearly for non-technical stakeholders",
                "signals": [
                    "years_of_experience >= 5 — baseline communication and seniority maturity",
                    "career_history[].description mentions collaboration with PM, design, or business teams",
                    "evidence of technical writing, documentation, or presenting",
                    "current_title contains 'Senior', 'Lead', 'Staff', or 'Principal'",
                ],
            },
        ],
        "red_line_requirements": [
            "years_of_experience >= 5",
            "skills must include at least one of: LLM, RAG, ML, deep learning, NLP, transformer",
            "Must have shipped production ML/AI features (research-only background is disqualifying)",
            "Python proficiency required",
            "product_company_fraction > 0.3 — some product company exposure required",
        ],
        "company_stage_signals": (
            "Series A AI-native startup (~15-40 person team). Post-PMF but pre-scale. "
            "Candidate must be comfortable in ambiguous, fast-moving environments with limited process. "
            "Equity is part of the compensation — prefer candidates who have joined early-stage companies before. "
            "Culture fit is critical: Redrob AI needs builders, not order-takers."
        ),
        "seniority_calibration": (
            "Senior IC (L5-equivalent): years_of_experience in range 5-9. "
            "Title keywords: Senior Engineer, Staff Engineer, Tech Lead, Principal Engineer. "
            "Must show progression from IC to senior/lead-scope over career history. "
            "Founding-team hire implies readiness to grow into tech lead within 12-18 months."
        ),
    }


def run() -> dict:
    logger.info("=" * 60)
    logger.info("Agent 1: Job Intelligence  [Rule-Based — No LLM]")
    logger.info("=" * 60)

    if JOB_INTEL_FILE.exists():
        logger.info(f"Checkpoint hit — {JOB_INTEL_FILE.name} exists. Skipping.")
        with open(JOB_INTEL_FILE, encoding="utf-8") as f:
            return json.load(f)

    logger.info("Loading JD...")
    jd_text = _load_jd_text()

    JOB_INTEL_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Parsing JD with rule-based analyser...")
    intelligence = _analyze_rule_based(jd_text)
    intelligence["generated_at"] = datetime.now(timezone.utc).isoformat()
    intelligence["jd_source"] = str(JD_DOCX if JD_DOCX.exists() else JD_MD_FALLBACK)

    with open(JOB_INTEL_FILE, "w", encoding="utf-8") as f:
        json.dump(intelligence, f, indent=2)

    logger.info(f"✓ Written: {JOB_INTEL_FILE}")
    logger.info(f"  Discriminators : {len(intelligence.get('discriminator_hierarchy', []))}")
    logger.info(f"  Culture signals: {len(intelligence.get('culture_signals', []))}")
    logger.info(f"  Implicit reqs  : {len(intelligence.get('implicit_requirements', []))}")
    return intelligence


if __name__ == "__main__":
    run()
