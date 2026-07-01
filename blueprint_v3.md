# HireIQ — Blueprint V3: AI Intelligence Layer
## Principal Architect Edition — Hackathon Winning Strategy

> **Status:** Implementation RFC — approved for immediate execution  
> **Author:** Principal Architect (Claude, June 2026)  
> **Constraint:** V1 and V2 are preserved unchanged. V3 is purely additive.

---

## 0. HONEST CURRENT-STATE AUDIT

Before any roadmap is credible, here is what we actually have built vs. what the previous blueprints assumed.

### What IS Implemented

| Layer | Component | Status | Notes |
|-------|-----------|--------|-------|
| V1 | Stream parser (JSONL/gzip) | ✅ Done | `src/pipeline/stream_parser.py` |
| V1 | Honeypot detector (4 rules) | ✅ Done | `src/honeypot.py` |
| V1 | Hard rules engine | ✅ Done | `src/hard_rules.py` |
| V1 | All 6 dimension scorers | ✅ Done | `src/scoring/` (title, skill, career, experience, education, availability) |
| V1 | Behavioral multiplier | ✅ Done | `src/scoring/behavioral_multiplier.py` |
| V1 | Composite scorer with weights | ✅ Done | `src/scoring/final_scorer.py`, weights tuned |
| V1 | Top-K streaming buffer | ✅ Done | `src/pipeline/top_k_buffer.py` |
| V1 | CSV writer (validate_submission.py-compliant) | ✅ Done | `src/pipeline/csv_writer.py` |
| V1 | rank.py entry point | ✅ Done | `rank.py` |
| V1 | JD requirements config | ✅ Done | `config/jd_requirements.json` |
| V2 | Agent 1: Job Intelligence | ✅ Done | Rule-based keyword/pattern extraction |
| V2 | Agent 2: Candidate Intelligence | ✅ Done | Heuristic scoring, ownership/outcome detection |
| V2 | Agent 3: Matching Intelligence | ✅ Done | Keyword overlap against discriminators |
| V2 | Agent 4: Recruiter Intelligence | ✅ Done | Decision tree → recommendation tier; template rationale |
| V2 | Agent 5: Reporting Agent | ✅ Done | Template-based reasoning strings (hash-variant rotation) |
| V2 | run_agents.py orchestrator | ✅ Done | `--test`, `--from N`, `--only N` flags |
| V2 | RecruiterDecision dataclass | ✅ Done | `src/models/recruiter_decision.py` |
| V2 | precomputed/ artifacts | ✅ Done | demo_data.json (574KB), reasoning_map.json, comparisons.json, 120 recruiter decisions |
| V2 | Streamlit dashboard (4 tabs) | ✅ Done | Role intel, Shortlist, Candidate detail, Compare |

### What is NOT Implemented (Gap vs Blueprints)

| Blueprint | Component | Gap | Winning Impact |
|-----------|-----------|-----|----------------|
| V2 | LLM recommendation_rationale in Agent 4 | Agent 4 uses f-string templates, same structure every tier | Stage 4 reasoning variation |
| V2 | CareerNarrativeDomain, OwnershipDomain extended profile | Agent 2 computes these as scores but doesn't produce the V2 extended object shape | Stage 5 architecture depth |
| V2 | TimingAssessment structured output | Partially in Agent 4 but not a proper dataclass | Minor |
| V2 | full_narrative field in RecruiterDecision | Not populated; demo_summary is template-based | Stage 4 |
| V3 | SQLite Knowledge Store (hireiq_knowledge.db) | Doesn't exist; agents write JSON only | Copilot + Simulator foundation |
| V3 | LLM Reasoning Layer (Ollama / Claude API) | Zero LLM calls anywhere in codebase | Stage 4 variation + Stage 5 wow |
| V3 | Recruiter Copilot (RAG-based Q&A) | Not started | Highest demo impact |
| V3 | Decision Simulator (weight sliders + re-rank) | Not started | Strongest "wow" feature |

### Critical Finding: `anthropic` IS installed

```
.venv/Lib/site-packages/anthropic/   ← already installed
requirements.txt                      ← does NOT list anthropic
```

The Claude SDK is available in the environment right now. We can call Claude Haiku today without installing anything. We only need to add `anthropic` to `requirements.txt` and set `ANTHROPIC_API_KEY`.

---

## 1. WHY WE CAN WIN

The hackathon is scored across 5 stages:

| Stage | What's Evaluated | Our Current Score | After V3 |
|-------|-----------------|-------------------|-----------|
| Stage 1 | Valid CSV format, sandbox URL loads | **~95%** — pipeline works | 100% |
| Stage 2 | NDCG@10 (50%), NDCG@50 (30%), MAP (15%), P@10 (5%) | **~80%** — scoring engine built | 80-85% (V3 doesn't change ranking) |
| Stage 3 | Reproduces in ≤5 min CPU, ≤16GB RAM, no network | **~95%** — pipeline confirmed fast | 100% |
| Stage 4 | Top-10 reasoning quality: specific, varied, honest, no hallucination | **~60%** — templates pass specific/honest but FAIL variation | **90%** with LLM narratives |
| Stage 5 | Architecture interview, demo quality, product thinking | **~50%** — good architecture but no AI | **95%** with Copilot + Simulator |

**V3 moves us from ~75% to ~90%+ across all stages. Stage 4 and Stage 5 are where we win.**

---

## 2. ARCHITECTURE

### 2.1 Three-Layer System

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LAYER 1: V1 RANKING PIPELINE                        ║
║                       (Untouched. Already complete.)                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  candidates.jsonl.gz (100K)                                                  ║
║        │                                                                     ║
║        ▼                                                                     ║
║  Stream → Honeypot Filter → 6 Scorers → Behavioral Mult → Top-K Buffer      ║
║        │                                                                     ║
║        ▼                                                                     ║
║  Re-rank Top-200 → Select Top-100 → CSV Writer → submission.csv             ║
║                                                                              ║
║  Reads: config/jd_requirements.json, precomputed/reasoning_map.json         ║
║  Writes: submission.csv only                                                 ║
║  Constraint: NO network, NO DB writes, ≤5 min CPU                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                         LAYER 2: V2 INTELLIGENCE AGENTS                      ║
║                       (Rule-based. Already complete.)                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Agent 1: JD Intelligence     → precomputed/job_intelligence.json           ║
║  Agent 2: Candidate Intel     → precomputed/candidate_profiles/*.json       ║
║  Agent 3: Matching Intel      → precomputed/match_scores/*.json             ║
║  Agent 4: Recruiter Intel     → precomputed/recruiter_decisions/*.json      ║
║  Agent 5: Reporting           → precomputed/reasoning_map.json              ║
║                                 precomputed/demo_data.json                  ║
║                                 precomputed/comparisons.json                ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                         LAYER 3: V3 AI INTELLIGENCE (NEW)                   ║
║                    (Additive only. All runs offline pre-compute.)           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  V2 Agent outputs                                                            ║
║        │                                                                     ║
║        ▼                                                                     ║
║  ┌─────────────────────────────────────────────┐                            ║
║  │   SQLite Knowledge Store                     │                            ║
║  │   hireiq_knowledge.db                        │                            ║
║  │                                              │                            ║
║  │   dim_scores  decisions  reasoning           │                            ║
║  │   comparisons  candidate_profiles  jobs      │                            ║
║  └───────────────────┬─────────────────────────┘                            ║
║                      │                                                       ║
║                      ▼                                                       ║
║  ┌───────────────────────────────────────────────────────┐                  ║
║  │  LLM Reasoning Layer (OFFLINE PRECOMPUTE ONLY)        │                  ║
║  │                                                       │                  ║
║  │  Primary:  Claude Haiku 4.5 API (if key available)   │                  ║
║  │  Fallback: Ollama + llama3.1:8b (local, free)        │                  ║
║  │                                                       │                  ║
║  │  Generates for top-100:                              │                  ║
║  │  · full_narrative (2-3 para recruiter memo)          │                  ║
║  │  · csv_reasoning_llm (replaces template in Agent 5)  │                  ║
║  │  · interview_guide_llm (candidate-specific questions) │                  ║
║  └───────────────────────────────────────────────────────┘                  ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                         DEMO DASHBOARD (Streamlit)                           ║
║                    (Network allowed. LLM API allowed.)                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Existing 4 tabs (V2):                                                       ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ║
║  │ Role Intel   │  │  Shortlist   │  │  Candidate   │  │   Compare    │   ║
║  │ (unchanged)  │  │ (unchanged)  │  │  (+ LLM memo)│  │ (unchanged)  │   ║
║  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   ║
║                                                                              ║
║  New V3 tabs:                                                                ║
║  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐ ║
║  │  Recruiter Copilot               │  │  Decision Simulator              │ ║
║  │                                  │  │                                  │ ║
║  │  RAG: SQLite → Claude Haiku      │  │  Sliders → re-rank from          │ ║
║  │  Q&A about rankings/decisions    │  │  stored dim_scores → live diff   │ ║
║  └──────────────────────────────────┘  └──────────────────────────────────┘ ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 2.2 Data Flow (What Goes Where)

```
rank.py (online, unchanged)
  → reads: config/jd_requirements.json
  → reads: precomputed/reasoning_map.json
  → writes: submission.csv

run_agents.py (offline, unchanged)
  Agent 1 → precomputed/job_intelligence.json
  Agent 2 → precomputed/candidate_profiles/*.json
  Agent 3 → precomputed/match_scores/*.json
  Agent 4 → precomputed/recruiter_decisions/*.json
  Agent 5 → precomputed/reasoning_map.json
           precomputed/comparisons.json
           precomputed/demo_data.json

knowledge/ingest.py  (NEW — one-time after run_agents)
  Reads all precomputed/*.json files
  Writes → hireiq_knowledge.db (all tables)

knowledge/reasoning.py  (NEW — after ingest)
  Reads SQLite decisions table
  Calls Claude Haiku API (or Ollama fallback)
  Writes → SQLite reasoning table
  Updates → precomputed/reasoning_map.json (LLM strings replace templates for top-100)

app/streamlit_app.py  (modified — add 2 new tabs)
  Reads: hireiq_knowledge.db (all views)
  Copilot: calls Claude Haiku API live for Q&A
  Simulator: re-ranks from dim_scores table in <200ms
```

---

## 3. TECH STACK

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Already in use |
| Streaming parser | `gzip` + `json` stdlib | Already working |
| Scoring | `numpy` | Already in requirements.txt |
| Embeddings (offline) | `sentence-transformers` | Already in requirements.txt |
| Knowledge store | `sqlite3` stdlib | Zero setup, single file, portable, 50K row queries <10ms |
| LLM (offline precompute) | Claude Haiku 4.5 API **primary** | Already installed in venv (`anthropic`). Cheaper than Ollama setup friction. |
| LLM (offline fallback) | Ollama + `llama3.1:8b` | If no API key; free; runs on 16GB RAM |
| LLM (demo Copilot) | Claude Haiku 4.5 API | ~$0.001/query, 500ms latency, excellent at structured data explanation |
| Dashboard | `streamlit>=1.40.0` | Already in use |
| HTTP | `requests` | For Ollama fallback calls |
| Testing | `pytest` | Add for V3 components |

**requirements.txt additions:**
```
anthropic>=0.34.0
requests>=2.32.0
```

---

## 4. NEW FILE STRUCTURE

Only new files — nothing existing is modified:

```
sententia/
│
├── knowledge/                     ← NEW PACKAGE
│   ├── __init__.py
│   ├── schema.sql                 ← SQLite schema
│   ├── storage.py                 ← read/write functions (used by all V3 components)
│   ├── ingest.py                  ← one-time import from precomputed/ JSON → SQLite
│   ├── reasoning.py               ← LLM narrative generation (offline only)
│   ├── copilot.py                 ← Recruiter Copilot (intent → retrieval → LLM)
│   └── simulator.py               ← Decision Simulator (re-rank from stored dim_scores)
│
├── precompute_v3.py               ← NEW entry point: ingest + LLM reasoning
│
├── app/
│   └── streamlit_app.py           ← MODIFIED: add Copilot tab + Simulator tab
│
└── requirements.txt               ← MODIFIED: add anthropic, requests
```

---

## 5. V3 COMPONENT SPECIFICATIONS

### 5.1 SQLite Knowledge Store

**Schema (`knowledge/schema.sql`):**

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- Per-candidate dimension scores (ingested from V1 pipeline metadata)
-- Enables Decision Simulator without touching rank.py
CREATE TABLE IF NOT EXISTS dim_scores (
    candidate_id             TEXT PRIMARY KEY,
    rank                     INTEGER,
    composite_score          REAL,
    title_role_score         REAL,
    skill_match_score        REAL,
    career_progression_score REAL,
    experience_depth_score   REAL,
    education_score          REAL,
    availability_score       REAL,
    behavioral_multiplier    REAL,
    is_honeypot              INTEGER DEFAULT 0,
    disqualifier             TEXT,
    current_title            TEXT,
    current_company          TEXT,
    years_of_experience      REAL,
    location                 TEXT,
    notice_period_days       INTEGER,
    open_to_work             INTEGER DEFAULT 0,
    response_rate            REAL
);

-- Recruiter decisions from Agent 4 (ingested from recruiter_decisions/*.json)
CREATE TABLE IF NOT EXISTS decisions (
    candidate_id             TEXT PRIMARY KEY,
    rank                     INTEGER,
    composite_score          REAL,
    recommendation           TEXT,
    recommendation_rationale TEXT,
    tech_fit_verdict         TEXT,
    product_fit_verdict      TEXT,
    growth_verdict           TEXT,
    trust_level              TEXT,
    blocking_risks           TEXT,   -- JSON array
    hiring_risks             TEXT,   -- JSON array
    strongest_evidence       TEXT,   -- JSON array
    missing_requirements     TEXT,   -- JSON array
    interview_focus          TEXT,   -- JSON array
    csv_reasoning            TEXT,
    demo_summary             TEXT,
    full_decision_json       TEXT    -- complete decision as JSON
);

-- LLM-generated narratives (written by knowledge/reasoning.py)
CREATE TABLE IF NOT EXISTS reasoning (
    candidate_id        TEXT PRIMARY KEY,
    llm_narrative       TEXT,
    llm_csv_reasoning   TEXT,
    llm_interview_guide TEXT,   -- JSON array of questions
    llm_model           TEXT,
    generation_time_ms  INTEGER
);

-- Candidate profiles from Agent 2
CREATE TABLE IF NOT EXISTS candidate_profiles (
    candidate_id       TEXT PRIMARY KEY,
    primary_domain     TEXT,
    narrative_type     TEXT,
    one_line_narrative TEXT,
    ownership_level    TEXT,
    product_mindset    TEXT,
    ai_career_fraction REAL,
    production_evidence TEXT,  -- JSON array
    gap_analysis       TEXT    -- JSON array
);

-- Comparisons from Agent 5
CREATE TABLE IF NOT EXISTS comparisons (
    pair_key        TEXT PRIMARY KEY,
    candidate_a_id  TEXT,
    candidate_b_id  TEXT,
    a_rank          INTEGER,
    b_rank          INTEGER,
    why_a_over_b    TEXT,
    comparison_json TEXT
);

-- Copilot conversation log
CREATE TABLE IF NOT EXISTS copilot_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question    TEXT,
    context_json TEXT,
    answer      TEXT,
    latency_ms  INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision Simulator cache
CREATE TABLE IF NOT EXISTS sim_cache (
    scenario_hash  TEXT PRIMARY KEY,
    weights_json   TEXT,
    top100_json    TEXT
);

CREATE INDEX IF NOT EXISTS idx_decisions_rank ON decisions (rank);
CREATE INDEX IF NOT EXISTS idx_decisions_rec  ON decisions (recommendation);
CREATE INDEX IF NOT EXISTS idx_dim_scores_rank ON dim_scores (rank);
CREATE INDEX IF NOT EXISTS idx_dim_scores_comp ON dim_scores (composite_score DESC);
```

**Why SQLite over anything else:**
- Zero setup — Python stdlib, single `.db` file
- All Copilot query patterns are structured (filter by score, recommendation, notice period, location) — not semantic
- 100-row queries complete in <2ms — fast enough for interactive demo
- Single file travels with repo (sample DB committed; full DB gitignored)

---

### 5.2 LLM Reasoning Layer

**Purpose:** Replace template-based reasoning strings with LLM-generated text for the top-100 candidates. This is the single change that most directly improves Stage 4 score.

**Where it runs:** Offline only. Never during `rank.py`. Never during the 5-minute ranking window.

**Model selection:**

```
Primary:  Claude Haiku 4.5 API
  - Already installed (anthropic in venv)
  - ~$0.001 per narrative — 100 candidates ≈ $0.10 total
  - 400ms latency offline — 100 candidates ≈ 40 seconds total
  - Quality: excellent at structured data → readable prose

Fallback: Ollama + llama3.1:8b (local)
  - Use if ANTHROPIC_API_KEY not set
  - ~3s per narrative — 100 candidates ≈ 5 minutes
  - Fits in 16GB RAM
  - Quality: good for 2-3 sentence summaries
```

**Prompt (narrative generation):**

```python
NARRATIVE_SYSTEM = """You are a senior technical recruiter writing a hiring recommendation memo.
You write in plain, direct language. No corporate jargon. No filler phrases like "passionate" or "dynamic".
You ONLY use facts from the structured data provided. You never invent information.
A typical memo is 2-3 sentences."""

NARRATIVE_USER = """JOB: {jd_summary}

CANDIDATE DATA:
Rank: #{rank}
Role: {current_title} at {current_company}
Experience: {years_of_experience} years
Location: {location} | Notice: {notice_period_days} days
Career narrative: {one_line_narrative}
Recommendation: {recommendation}
Technical fit: {tech_fit_verdict}
Strongest evidence:
{evidence_list}
Primary concern: {top_risk}
Gap: {top_gap}

Write a 2-3 sentence hiring recommendation. Tone should match rank #{rank} (rank 1-5: enthusiastic; 
rank 6-20: positive; rank 21-50: cautious; rank 51-100: honest about limitations).
Acknowledge the main concern. Use specific facts. No preamble."""
```

**What changes in the pipeline after LLM reasoning runs:**
- `precomputed/reasoning_map.json` is updated — LLM strings replace template strings for top-100
- `rank.py` reads `reasoning_map.json` unchanged — it gets LLM strings automatically
- Stage 4 judges read varied, candidate-specific reasoning instead of templates

**Batch processing with checkpointing:**

```python
# knowledge/reasoning.py
def run_batch(top_n=100, model="claude-haiku-4-5"):
    """Offline only. Checkpointed — safe to resume."""
    for candidate in get_top_n(top_n):
        cid = candidate["candidate_id"]
        if get_reasoning(cid):  # skip if already done
            continue
        narrative = generate_narrative(candidate, jd_summary, model)
        write_reasoning(cid, narrative, model)
        update_reasoning_map(cid, narrative)  # patch reasoning_map.json
```

---

### 5.3 Recruiter Copilot

**Purpose:** Allow a judge to ask questions in plain English about the rankings. The Copilot retrieves structured facts from SQLite and passes them to Claude Haiku to generate a grounded, non-hallucinated answer.

**This is the highest-ROI demo feature.** It takes ~4 hours to implement and produces the moment where a judge says "wait, it can answer questions about itself?"

**Architecture: Retrieval-Augmented Generation**

```
User types question
       │
       ▼
Intent Classifier (rule-based keyword matching — no ML needed)
       │
       ├── RANKING_EXPLANATION → get_decision(candidate_id) from SQLite
       ├── COMPARISON_QUERY   → get_comparison(id_a, id_b) from SQLite
       ├── CANDIDATE_FILTER   → query_candidates(filters) from SQLite
       ├── JOB_INTEL          → get_job_intelligence() from SQLite
       └── UNKNOWN            → redirect message (no LLM call)
       │
       ▼
Context builder (assembles retrieved rows into compact JSON)
       │
       ▼
Claude Haiku 4.5 API
  System: "Answer using ONLY the provided data. Never invent facts."
  User:   "{structured_context}\n\nQuestion: {question}"
       │
       ▼
Answer displayed in st.chat_message()
Context shown in st.expander() for transparency
```

**Intent patterns:**

```python
INTENT_PATTERNS = {
    "RANKING_EXPLANATION": [
        r"why.*rank", r"explain.*rank", r"why.*advance", r"why.*decline",
        r"how.*scored", r"what.*recommend", r"reason.*rank"
    ],
    "COMPARISON_QUERY": [
        r"compare", r"vs\.?", r"versus", r"difference between",
        r"better.*cand", r"choose between"
    ],
    "CANDIDATE_FILTER": [
        r"show.*candidate", r"find.*candidate", r"who.*has",
        r"available.*\d+.*day", r"notice.*\d+", r"strongly advance",
        r"hidden gem", r"lowest notice", r"open to work"
    ],
    "JOB_INTEL": [
        r"what.*role", r"what.*looking for", r"requirements", r"job description"
    ]
}
```

**Example interactions to demo to judges:**

```
Judge: "Why is rank #1 ranked first?"
Copilot: "Rank #1 is a [title] at [company] with 6 years of AI/ML experience. 
          Their decisive advantage is [top evidence from decisions table]. 
          Main concern: [top risk]. Response rate [X]% — contact immediately."

Judge: "Show candidates available within 30 days"
Copilot: "4 candidates have notice periods of 30 days or less (ranks 3, 7, 12, 23). 
          Rank 3 is the highest quality — ADVANCE recommendation, strong technical fit, Hyderabad."

Judge: "Why does rank 2 have a lower score than rank 1?"
Copilot: "[From pre-computed comparison] Both strong. Rank 1 edges rank 2 on [decisive_dimension] 
          — [specific evidence from comparison table]. Rank 2 wins on [b_strength]."

Judge: "What makes someone a bad fit for this role?"
Copilot: "[From job_intelligence.json] Disqualifiers: consulting-only career (TCS/Wipro), 
          AI experience <12 months, no production deployment evidence, pure research background."
```

---

### 5.4 Decision Simulator

**Purpose:** Judge adjusts scoring weights via sliders → ranking updates in real time. This demonstrates multi-dimensional scoring depth in a way no verbal explanation can match.

**Why this works technically:** The `dim_scores` table stores per-dimension scores for all top-200 candidates. Re-ranking with new weights requires only:
1. Read 200 rows (< 5ms)
2. Recompute composite in Python (< 1ms)
3. Sort (< 1ms)
4. Streamlit re-render (< 100ms)

Total: under 200ms. No LLM needed.

**Streamlit UI:**

```python
# Two-column layout
col_sliders, col_results = st.columns([1, 2])

with col_sliders:
    w_title  = st.slider("Role/Title Match",   0, 50, 15, 5)
    w_skill  = st.slider("Skill Match",        0, 50, 30, 5)
    w_career = st.slider("Career Trajectory",  0, 50, 25, 5)
    w_exp    = st.slider("Experience Depth",   0, 50, 10, 5)
    w_edu    = st.slider("Education",          0, 20,  5, 5)
    w_avail  = st.slider("Availability",       0, 50, 15, 5)
    
    # Preset scenarios — each one tells a story
    if st.button("⚡ Prioritize Availability"):   # What if we need someone NOW?
        ...
    if st.button("🧠 Technical Depth First"):     # What if skills trump everything?
        ...
    if st.button("🚀 Ignore Location"):           # What if remote is fine?
        ...

with col_results:
    results = simulate_ranking(weights)
    for r in results[:20]:
        change = r["rank_change"]
        icon = "↑" if change > 0 else "↓" if change < 0 else "─"
        # Show: rank, movement indicator, title, company, original rank
```

**The demo moment:** Click "Prioritize Availability" → candidates with 90-day notice periods drop, candidates available in 2 weeks jump up → judge says "I get it, the scoring is genuinely multi-dimensional."

---

## 6. HOW V3 IS INGESTED (precompute_v3.py)

Since V1 and V2 are already run and produce JSON files, we do NOT re-run them. V3 ingestion is a one-time step that converts existing JSON artifacts into SQLite:

```python
# precompute_v3.py
"""
One-time V3 setup. Runs AFTER run_agents.py has completed.
Does not touch rank.py or run_agents.py.

Usage:
    python precompute_v3.py                    # Full: ingest + LLM reasoning
    python precompute_v3.py --ingest-only      # Only build SQLite from JSON
    python precompute_v3.py --reason-only      # Only run LLM reasoning (needs SQLite)
    python precompute_v3.py --model haiku      # Use Claude Haiku (default)
    python precompute_v3.py --model ollama     # Use Ollama fallback
"""

def main():
    step1_init_db()           # Create schema
    step2_ingest_decisions()  # recruiter_decisions/*.json → decisions table
    step3_ingest_profiles()   # candidate_profiles/*.json → candidate_profiles table
    step4_ingest_scores()     # Reconstruct dim_scores from decisions + profiles
    step5_ingest_comparisons()# comparisons.json → comparisons table
    step6_ingest_jd()         # job_intelligence.json → jobs table
    step7_llm_reasoning()     # Generate LLM narratives → reasoning table
                               # → updates precomputed/reasoning_map.json
```

**Step 4 note:** The `dim_scores` table needs per-dimension scores to power the Simulator. These are NOT stored in recruiter_decisions JSON (Agent 4 only stores the final recommendation). Solution: we read them from `precomputed/demo_data.json` which already contains aggregated candidate data, OR we add a lightweight V1 pipeline pass that outputs per-dimension scores to a JSON file before the LLM step. The simplest approach: extract from `demo_data.json` which already has all the data we need.

---

## 7. IMPLEMENTATION ROADMAP

### Priority Framework

**Every hour spent should ask: does this improve Stage 4 score, Stage 5 demo, or both?**

| Task | Stage 4 Impact | Stage 5 Impact | Hours | Priority |
|------|---------------|----------------|-------|----------|
| SQLite schema + ingest | Low | High (enables Copilot/Simulator) | 3h | P0 |
| LLM narrative generation (top-100) | **High** | Medium | 3h | P0 |
| Update reasoning_map.json with LLM strings | **High** | Low | 0.5h | P0 |
| Recruiter Copilot (RAG + Claude Haiku) | Low | **Very High** | 4h | P1 |
| Decision Simulator (weight sliders) | Low | **Very High** | 3h | P1 |
| Copilot Streamlit tab | Low | **Very High** | 2h | P1 |
| Simulator Streamlit tab | Low | **Very High** | 2h | P1 |
| anthropic + requests in requirements.txt | Low | Low | 0.1h | P0 (now) |
| Sample SQLite DB for demo deploy | Low | High | 1h | P2 |

**Total: ~19 hours of new work. V1+V2 are already done.**

---

### Day-by-Day Execution

#### Day 1 (Hours 1-8): Foundation

**Hours 1-2: requirements.txt + SQLite schema**
- Add `anthropic>=0.34.0` and `requests>=2.32.0` to requirements.txt
- Write `knowledge/schema.sql` (exact schema from Section 5.1)
- Write `knowledge/__init__.py` and `knowledge/storage.py` with all read/write functions
- Test: `python -c "from knowledge.storage import init_db; init_db()"` — verify DB created

**Hours 3-5: Ingest pipeline**
- Write `knowledge/ingest.py` — reads all precomputed JSON, writes to SQLite tables
- Run: `python precompute_v3.py --ingest-only`
- Test: query counts — `SELECT COUNT(*) FROM decisions` should = 100

**Hours 6-8: LLM reasoning**
- Write `knowledge/reasoning.py` with narrative generation + checkpointing
- Set `ANTHROPIC_API_KEY` environment variable
- Run on top-20 candidates first; verify narrative quality manually
- If quality good: run on all 100
- Update `precomputed/reasoning_map.json` with LLM strings

**Day 1 validation:**
```bash
python precompute_v3.py --ingest-only
python -c "
from knowledge.storage import get_top_n
top5 = get_top_n(5)
print([c['candidate_id'] + ': ' + c.get('recommendation','?') for c in top5])
"
# Expected: 5 candidates, first should be STRONGLY_ADVANCE
```

---

#### Day 2 (Hours 9-17): Copilot + Simulator

**Hours 9-13: Recruiter Copilot**
- Write `knowledge/copilot.py`:
  - `classify_intent(question)` — keyword regex matching
  - `extract_candidate_id(question)` — regex for CAND_XXXXXXX
  - `extract_filters(question)` — map natural language to SQL filters
  - `build_context(intent, question)` — SQL retrieval
  - `generate_answer(context, question)` — Claude Haiku call
  - `answer_question(question)` — main entry point
- Test offline with 10 hand-crafted questions (see Section 5.3 examples)

**Hours 14-17: Decision Simulator**
- Write `knowledge/simulator.py`:
  - `simulate_ranking(weights, n=100)` — re-rank from dim_scores
  - `explain_change(original, simulated)` — plain-English summary of movers
- Test: verify `simulate_ranking(DEFAULT_WEIGHTS)` matches existing top-20

---

#### Day 3 (Hours 18-24): Streamlit Integration + Polish

**Hours 18-21: Add new tabs to streamlit_app.py**
- Tab 5: Copilot — `st.chat_input` + conversation history + context expander
- Tab 6: Simulator — weight sliders + preset scenarios + before/after rank diff
- Seed Copilot with 5 suggested questions (buttons that pre-fill input)
- Test all 6 tabs end-to-end

**Hours 22-24: Deploy + submit prep**
- Build `hireiq_knowledge_sample.db` from the 50-candidate test data (commit this)
- Full precomputed data in `.gitignore`
- Deploy updated Streamlit to HuggingFace Spaces / Streamlit Cloud
- Update `submission_metadata.yaml`
- Update README with new commands

---

## 8. DEMO SCRIPT (3-MINUTE VERSION FOR JUDGES)

**Setup:** App is open on Role Intelligence tab. Pre-loaded with 50-candidate sample.

**Minute 1 — The Problem + V1:**
- "Most recruiting systems rank Marketing Managers #1 because they have AI keywords."
- Show sample_submission.csv: rank 1 is HR Manager
- "Here's what HireIQ does differently."
- Switch to Shortlist tab: groups by recommendation tier, not rank number
- "8 candidates we'd advance this week. 12 after screening. 80 below threshold."

**Minute 2 — V2 Intelligence:**
- Click top candidate → Candidate Intelligence Panel
- "This isn't a score. It's a structured hiring recommendation."
- Point to: STRONGLY_ADVANCE, Fit Assessment bars, Strongest Evidence bullets, Hiring Risks
- "The interview questions are derived from this specific candidate's gaps and risks."
- Click Compare: show why rank 1 ranks above rank 2 with dimensional breakdown

**Minute 3 — V3 AI Features (the winning moment):**
- Switch to Recruiter Copilot tab
- Type: "Why is rank 1 ranked first?" → Copilot answers with specific facts
- Type: "Show candidates available in 30 days" → filtered list appears
- Switch to Decision Simulator tab
- Click "Technical Depth First" preset → watch ranking change live
- "The system is transparent about what it's doing and why."

**Closing line:** "This is what a recruiter's AI assistant looks like. Not a black box. A thinking colleague."

---

## 9. STAGE-SPECIFIC WINNING CRITERIA

### Stage 1 (Auto-check)
- [x] Valid CSV — already passing
- [ ] Sandbox URL must load — deploy after V3 Streamlit changes

### Stage 2 (NDCG@10, NDCG@50, MAP, P@10)
- V3 does NOT change ranking — all Stage 2 score comes from V1+V2
- Current estimate: top 10 contains genuinely qualified AI/ML candidates, not keyword stuffers
- No action needed in V3

### Stage 3 (Reproduction)
- V3 adds `precompute_v3.py` which runs offline — not part of `rank.py`
- `rank.py` must stay deterministic and network-free
- `hireiq_knowledge.db` is NOT read by `rank.py` (confirm with env var guard)
- Add to README: two-command setup: `python run_agents.py` then `python precompute_v3.py`

### Stage 4 (Reasoning Quality — 10 samples)
**Before V3:** Templates pass "specific" and "honest" but fail "variation" (same structure per tier)  
**After V3:** LLM narratives pass all 6 criteria:
- ✅ Specific facts (names, titles, skills, signal values from decisions JSON)
- ✅ JD connection (prompt includes jd_summary)
- ✅ Honest concerns (prompt requires acknowledging top risk)
- ✅ No hallucination (context contains only verified structured data)
- ✅ Variation (LLM generates unique prose per candidate)
- ✅ Rank consistency (prompt includes rank and adjusts tone)

### Stage 5 (Architecture Interview + Demo)
**Talking points in the interview:**

1. **"Walk me through your architecture."**  
   V1 = deterministic ranking (rule-based, fast, reproducible). V2 = intelligence agents (structured decisions, per-candidate). V3 = AI layer (LLM narratives offline, Copilot live, Simulator for exploration). The ranking is deterministic. The intelligence is AI-generated. Clear separation.

2. **"Why SQLite and not a proper database?"**  
   For 100 candidates and 200 simulation rows, SQLite queries complete in 2ms. PostgreSQL adds setup friction that breaks reproduction. The schema is migration-compatible — swap `sqlite3` for `psycopg2` in `storage.py`, no query changes needed.

3. **"How do you prevent the Copilot from hallucinating?"**  
   RAG pattern: retrieve structured JSON from SQLite first, pass only that to the LLM. The LLM cannot claim a candidate has 10 years experience if the retrieved context says 6. Every answer is grounded. We show the retrieved context in an expander for full transparency.

4. **"What would you add with more time?"**  
   Recruiter feedback loop (rate recommendations → RLHF data), multi-JD support (add jd_hash column, same schema), ATS integrations. The RecruiterDecision object is already the canonical API contract — wrapping it in FastAPI is a 2-hour change.

5. **"Why did you choose this tech stack?"**  
   No LLM in the ranking path — the hackathon prohibits network calls during ranking. We spent all the AI budget in offline pre-computation where there's no time limit and no network restriction. This is the right engineering call for the constraints given.

---

## 10. RISKS AND MITIGATIONS

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Claude API key not available in demo env | Medium | Ollama fallback in all components; demo still works |
| LLM narrative quality too generic | Low | Test on 10 before running full batch; fallback to templates |
| Simulator produces wrong re-ranking | Low | Unit test: `simulate_ranking(DEFAULT_WEIGHTS)` must match baseline ranks |
| Copilot hallucinates | Low | Strict system prompt: "only use provided data"; show context expander to verify |
| V3 scope creep delays V1/V2 | Low | V1 and V2 are already done — can't delay what's complete |
| Streamlit tab additions break existing tabs | Low | Add tabs as new functions, existing tab render functions unchanged |
| `hireiq_knowledge.db` too large to commit | Certain | Commit only `hireiq_knowledge_sample.db` (from 50-candidate test); full DB in `.gitignore` |

---

## 11. WHAT NOT TO BUILD

**These were in draft proposals but are excluded from V3:**

| Feature | Reason Excluded |
|---------|-----------------|
| Separate AI Orchestrator agent | `run_agents.py` + `precompute_v3.py` already orchestrate; extra class = complexity without capability |
| Career Archetype Classifier (new agent) | Agent 2 already computes `narrative_type`; new agent adds a label that already exists |
| LangChain / LlamaIndex | 50 lines of custom Python > 200 lines of LangChain configuration for the same result |
| FastAPI backend | Streamlit is the demo surface; REST API is post-hackathon |
| Docker | Adds judge setup friction; `requirements.txt` + Python version is sufficient |
| Fine-tuned models | No labeled data; pre-trained Haiku with good prompts > fine-tuned model on no data |
| pgvector / Pinecone for Copilot | Copilot queries are structured (filter by field) or exact (filter by ID); SQLite FTS5 handles the 10% semantic cases |
| Bias audit reporting | Important but earns zero points at Stage 4-5 in this hackathon context |
| Database for `rank.py` | The online ranking step must be deterministic and network-free; SQLite is offline but the guard exists via env var |

---

## 12. CHECKLISTS

### Before V3 work starts
- [ ] `python rank.py --candidates [path] --out submission.csv` completes in <5 min
- [ ] `python validate_output.py submission.csv` passes
- [ ] Streamlit app loads with precomputed data
- [ ] ANTHROPIC_API_KEY available in environment

### After each V3 day
**Day 1:**
- [ ] `python -c "from knowledge.storage import init_db; init_db()"` creates hireiq_knowledge.db
- [ ] `SELECT COUNT(*) FROM decisions` returns 100
- [ ] LLM narrative for rank #1 candidate: non-generic, mentions specific facts
- [ ] `precomputed/reasoning_map.json` updated with at least 5 LLM strings

**Day 2:**
- [ ] Copilot answers "Why is rank 1 ranked first?" with specific evidence, no hallucination
- [ ] Copilot answers "Show candidates available in 30 days" with filtered list
- [ ] Copilot says "I can only answer questions about..." for off-topic questions
- [ ] `simulate_ranking(DEFAULT_WEIGHTS)` top-5 matches existing ranking top-5

**Day 3:**
- [ ] All 6 Streamlit tabs load without error
- [ ] Copilot tab: 5 suggested question buttons work
- [ ] Simulator: "Technical Depth First" preset changes at least 3 top-20 positions
- [ ] Demo sandbox deployed and accessible via URL

### Final submission
- [ ] `rank.py` makes zero DB writes, zero network calls
- [ ] `validate_output.py submission.csv` passes
- [ ] Top-10 manual review: all AI/ML professionals, no keyword stuffers
- [ ] 10 reasoning strings manually reviewed: varied, specific, no two identical
- [ ] `requirements.txt` includes `anthropic>=0.34.0`
- [ ] `hireiq_knowledge_sample.db` committed (from 50-candidate run)
- [ ] `submission_metadata.yaml` complete
- [ ] 15+ git commits with meaningful messages

---

## 13. QUICK REFERENCE: WHAT MAPS WHERE

| Blueprint Concept | Actual File |
|-------------------|-------------|
| V1 streaming pipeline | `src/pipeline/runner.py` |
| V1 scoring dimensions | `src/scoring/` (6 files) |
| V1 honeypot | `src/honeypot.py` |
| V1 hard rules | `src/hard_rules.py` |
| V1 entry point | `rank.py` |
| V2 Agent 1 | `src/intelligence/agents/agent1_job.py` |
| V2 Agent 2 | `src/intelligence/agents/agent2_candidate.py` |
| V2 Agent 3 | `src/intelligence/agents/agent3_matching.py` |
| V2 Agent 4 | `src/intelligence/agents/agent4_recruiter.py` |
| V2 Agent 5 | `src/intelligence/agents/agent5_reporting.py` |
| V2 orchestrator | `run_agents.py` |
| V2 Streamlit (4 tabs) | `app/streamlit_app.py` |
| V3 SQLite schema | `knowledge/schema.sql` ← **CREATE** |
| V3 read/write functions | `knowledge/storage.py` ← **CREATE** |
| V3 JSON → SQLite ingest | `knowledge/ingest.py` ← **CREATE** |
| V3 LLM narrative generation | `knowledge/reasoning.py` ← **CREATE** |
| V3 Recruiter Copilot | `knowledge/copilot.py` ← **CREATE** |
| V3 Decision Simulator | `knowledge/simulator.py` ← **CREATE** |
| V3 entry point | `precompute_v3.py` ← **CREATE** |
| V3 Streamlit (6 tabs) | `app/streamlit_app.py` ← **MODIFY** (add 2 tabs) |

---

*Blueprint V3 — HireIQ Hackathon Winning Strategy*  
*Authored: June 2026*  
*V1 ranking pipeline: complete. V2 intelligence agents: complete. V3 AI layer: ready to build.*  
*Estimated remaining work: ~19 hours. Estimated score delta: +15 to +20 percentage points.*
