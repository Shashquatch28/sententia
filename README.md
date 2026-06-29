# Sententia

**Sententia** is a constraint-aware candidate screening, ranking, and recruiter intelligence system built for the Redrob AI hiring challenge. It processes large applicant datasets (100,000+ candidates) and produces structured, audit-ready hiring decisions under strict resource limits: CPU-only, no GPU, under 16 GB RAM, and under five minutes end-to-end.

The codebase implements **HireIQ** — a two-phase architecture that separates deep offline recruiter analysis from a high-speed streaming ranker. The system answers not just *who* to hire, but *why*, *what to ask in interviews*, and *how candidates compare* to one another.

**Repository:** [github.com/Shashquatch28/sententia](https://github.com/Shashquatch28/sententia)

---

## Table of Contents

1. [Summary](#summary)
2. [What It Does](#what-it-does)
3. [How It Works](#how-it-works)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Installation](#installation)
7. [Dataset Setup](#dataset-setup)
8. [Usage Guide](#usage-guide)
9. [Scoring & Ranking Logic](#scoring--ranking-logic)
10. [The 5-Agent Intelligence Pipeline](#the-5-agent-intelligence-pipeline)
11. [Streamlit Dashboard](#streamlit-dashboard)
12. [Knowledge Store & AI Layer (Optional)](#knowledge-store--ai-layer-optional)
13. [Validation](#validation)
14. [Configuration](#configuration)
15. [Team & Constraints](#team--constraints)

---

## Summary

Sententia is a deterministic, rule-based hiring intelligence platform for ranking Senior AI Engineer candidates at Redrob AI. It combines:

- A **streaming ranker** that scores 100K+ profiles in seconds with constant memory
- A **5-agent offline pipeline** that builds recruiter-ready profiles, match scores, decisions, and reasoning
- A **Streamlit dashboard** for exploring role intelligence, shortlists, candidate deep-dives, and pairwise comparisons
- Optional **SQLite knowledge store** and **LLM copilot** layer for interactive recruiter Q&A (not used during ranking)

All ranking and agent logic is fully deterministic — no AI API calls are made during the ranking step, and the pipeline makes zero network calls at inference time.

---

## What It Does

Naive screening tools often fail in two ways:

1. **Keyword stuffing** — candidates game the system by packing profiles with relevant terms without real experience.
2. **Score-only outputs** — a sorted list with no context on *why* someone ranks where they do, what to probe in interviews, or how adjacent candidates differ.

Sententia addresses both:

| Capability | Description |
|---|---|
| Honeypot detection | Heuristic filters penalize keyword stuffers and inconsistent profiles |
| Hard rules | Disqualifiers cap scores for wrong titles or consulting-only careers |
| Multi-dimensional scoring | Six weighted fit dimensions plus a behavioral reachability multiplier |
| Recommendation tiers | `STRONGLY_ADVANCE`, `ADVANCE`, `REVIEW_FURTHER`, `ADVANCE_IF_POOL_THIN`, `DECLINE` |
| Pairwise reasoning | Explains why Candidate A ranks above adjacent Candidate B |
| Interview questions | Tailored question sets per recommendation tier |
| Validator-compliant CSV | Top-100 `submission.csv` with unique, candidate-specific reasoning strings |

---

## How It Works

The system splits work into an **offline pre-computation phase** (Dev B) and an **online streaming phase** (Dev A):

```text
┌─────────────────────────────────────────────────────────┐
│                    OFFLINE PHASE                        │
│     (Batch analysis of JD + top candidates)             │
│                                                         │
│   Job Desc (DOCX/MD) ──► Agent 1: Job Intelligence      │
│   Candidates (JSONL) ──► Agent 2: Candidate Intel       │
│   Profiles (JSON)    ──► Agent 3: Matching Intel        │
│   Match Scores       ──► Agent 4: Recruiter Intel       │
│   Decisions (JSON)   ──► Agent 5: Reporting             │
│                                 │                       │
└─────────────────────────────────┼───────────────────────┘
                                  ▼
                    precomputed/reasoning_map.json
                                  │
┌─────────────────────────────────┼───────────────────────┐
│                    ONLINE PHASE                         │
│        (High-speed streaming & heap-based ranking)      │
│                                                         │
│   100K Candidates ──► Stream Parser ──► Final Scorer    │
│                             │                  ▲        │
│                             ▼                  │        │
│                         Honeypots &        Reasoning    │
│                         Hard Rules         Map (JSON)   │
│                             │                           │
│                             ▼                           │
│                        Top-200 Heap ──► submission.csv    │
└─────────────────────────────────────────────────────────┘
```

**Offline phase** (`run_agents.py`) analyzes the job description and progressively narrows the candidate pool (500 → 200 → 100 in full mode), producing JSON artifacts under `precomputed/`.

**Online phase** (`rank.py`) streams every candidate from disk, scores them through the weighted scorer, maintains only a top-200 min-heap in memory, and writes the top 100 to CSV. Reasoning strings come from the precomputed map when available, with a deterministic fallback generator otherwise.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Dashboard | [Streamlit](https://streamlit.io/) 1.58 |
| Core ranking | Standard library (`json`, `gzip`, `csv`, `heapq`, `pathlib`, `argparse`) |
| Job description parsing | Zero-dependency DOCX extractor (`zipfile` + XML) |
| Knowledge store | SQLite (`knowledge/storage.py`) |
| AI copilot (optional) | Pluggable LLM client (Ollama / OpenAI-compatible) via `src/ai/` |
| Config | JSON (`config/jd_requirements.json`) |

**Design constraints met:**

- No GPU required
- No external databases during ranking (PostgreSQL, Redis, etc.)
- No network calls during ranking
- Constant-memory streaming via `heapq` top-K buffer
- Core scorer uses no Pandas; Streamlit installs Pandas/NumPy as transitive UI dependencies

---

## Project Structure

```text
Sententia/
├── app/
│   └── streamlit_app.py          # Recruiter dashboard (reads precomputed JSON only)
├── config/
│   └── jd_requirements.json      # Role requirements, skill aliases, disqualifiers, weights
├── datasets/                     # Input data (not committed — see Dataset Setup)
│   ├── candidates.jsonl          # Full 100K candidate pool
│   ├── sample_candidates.json    # 50-candidate test set
│   ├── job_description.docx      # Primary JD source
│   └── candidate_schema.json     # Candidate record schema
├── knowledge/
│   ├── schema.sql                # SQLite schema for knowledge store
│   ├── storage.py                # DB connection & initialization
│   └── ingest.py                 # Import precomputed JSON into SQLite
├── precomputed/                  # Generated artifacts (partially committed for demo)
│   ├── job_intelligence.json
│   ├── candidate_profiles/       # One JSON per candidate (Agent 2)
│   ├── match_scores/             # One JSON per candidate (Agent 3)
│   ├── recruiter_decisions/      # One JSON per candidate (Agent 4)
│   ├── reasoning_map.json        # 100 candidate-specific reasoning strings (Agent 5)
│   ├── comparisons.json          # Adjacent pairwise comparisons (Agent 5)
│   └── demo_data.json            # Aggregated UI payload (Agent 5)
├── src/
│   ├── pipeline/                 # Streaming ranker (Dev A)
│   │   ├── runner.py             # Main ranking orchestration
│   │   ├── stream_parser.py      # JSON / JSONL / JSONL.GZ streaming
│   │   ├── top_k_buffer.py       # Constant-memory min-heap top-K
│   │   ├── csv_writer.py         # Submission CSV writer
│   │   └── reasoning.py          # Fallback reasoning generator
│   ├── scoring/                  # Six-dimension scorer + behavioral multiplier
│   │   ├── final_scorer.py       # Weighted score aggregation
│   │   ├── title_role_score.py
│   │   ├── skill_match_score.py
│   │   ├── career_progression_score.py
│   │   ├── experience_depth_score.py
│   │   ├── education_score.py
│   │   ├── availability_score.py
│   │   └── behavioral_multiplier.py
│   ├── intelligence/             # 5-agent offline pipeline (Dev B)
│   │   ├── agents/               # agent1_job … agent5_reporting
│   │   ├── paths.py              # Shared path constants & test-mode config
│   │   └── docx_reader.py        # Zero-dependency DOCX text extractor
│   ├── ai/                       # Optional LLM copilot layer (V3.10)
│   │   ├── service.py            # Unified AI entrypoint
│   │   ├── retrieval.py          # SQLite-backed context retrieval
│   │   ├── client.py             # Ollama / OpenAI-compatible provider
│   │   ├── copilot.py            # Recruiter Q&A wrapper
│   │   └── simulator.py          # Decision scenario simulator
│   ├── models/                   # Data classes (feature vectors, decisions)
│   ├── hard_rules.py             # Disqualifiers and score caps
│   └── honeypot.py                 # Keyword-stuffing detection
├── rank.py                       # Entry point: online ranking pipeline
├── run_agents.py                 # Entry point: offline 5-agent pipeline
├── precompute_v3.py              # Build SQLite knowledge store from JSON artifacts
├── validate_output.py            # Validate submission.csv against spec
├── job_description.md            # Markdown fallback for JD parsing
├── submission.csv                # Example ranked output (top 100)
├── submission_metadata.yaml      # Hackathon submission metadata
└── requirements.txt
```

---

## Installation

### Prerequisites

- Python 3.11+ (tested on Windows; works on macOS/Linux)
- Git
- ~16 GB RAM recommended for full 100K run
- No GPU required

### Steps

```bash
git clone https://github.com/Shashquatch28/sententia.git
cd sententia

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Dataset Setup

Large dataset files are **not committed** to the repository (see `.gitignore`). Place the hackathon data under `datasets/` with this layout:

```text
datasets/
├── candidates.jsonl              # Full candidate pool (~100K records)
├── sample_candidates.json        # 50-candidate smoke-test set
├── job_description.docx          # Job description document
├── candidate_schema.json         # Candidate record schema
└── redrob_signals_doc.docx       # Redrob platform signals reference (optional)
```

If your download uses a nested folder structure (e.g. `datasets/candidates/candidates.jsonl`), copy or symlink files to the flat paths above. Agent 2 and the ranker read from the paths defined in `src/intelligence/paths.py`.

A markdown fallback (`job_description.md` at the project root) is used automatically if the DOCX is missing or empty.

---

## Usage Guide

### Quick start (test mode)

Run the full pipeline on 50 sample candidates in seconds:

```bash
# Step 1: Offline intelligence (Agents 1–5)
python run_agents.py --test

# Step 2: Rank candidates and write submission CSV
python rank.py --candidates datasets/sample_candidates.json --out submission.csv

# Step 3: Launch the dashboard
streamlit run app/streamlit_app.py
```

### Full production run (100K candidates)

```bash
# Step 1: Pre-compute intelligence (~10 minutes)
python run_agents.py

# Step 2: Stream-rank all candidates
python rank.py --candidates datasets/candidates.jsonl --out submission.csv --precomputed precomputed

# Step 3: Validate output
python validate_output.py submission.csv

# Step 4: Explore results in the dashboard
streamlit run app/streamlit_app.py
```

### `run_agents.py` options

```bash
python run_agents.py              # Full run: 500 → 200 → 100 → report
python run_agents.py --test       # Test run: 50 → 50 → 20 → report
python run_agents.py --from 3       # Resume from Agent 3
python run_agents.py --only 1       # Run only Agent 1
python run_agents.py --test --from 2  # Test mode, resume from Agent 2
```

Agents checkpoint their outputs — re-running skips already-written files.

### `rank.py` options

```bash
python rank.py \
  --candidates datasets/candidates.jsonl \
  --out submission.csv \
  --precomputed precomputed
```

| Flag | Description |
|---|---|
| `--candidates` | Path to `.json`, `.jsonl`, or `.jsonl.gz` candidate file (required) |
| `--out` | Output CSV path (required) |
| `--precomputed` | Directory containing `reasoning_map.json` (default: `precomputed`) |

Progress is logged to stderr every 10,000 candidates. The ranker maintains a top-200 heap and writes the top 100 to CSV.

### Reproduce command (hackathon)

```bash
python rank.py --candidates <path_to_candidates.jsonl> --out submission.csv --precomputed precomputed
```

---

## Scoring & Ranking Logic

Every candidate is evaluated across **six weighted dimensions** in `src/scoring/final_scorer.py`:

| Dimension | Weight | Module | What it measures |
|---|---|---|---|
| Skill match | 30% | `skill_match_score.py` | Required skills vs. claimed skills, proficiency, endorsements, duration |
| Career progression | 25% | `career_progression_score.py` | Upward mobility, AI/product career fractions, production evidence |
| Title & role fit | 15% | `title_role_score.py` | Current and past titles vs. target Senior AI Engineer role |
| Availability | 15% | `availability_score.py` | Location, notice period, work mode preferences |
| Experience depth | 10% | `experience_depth_score.py` | Relevant years of experience vs. 5–9 year target bracket |
| Education | 5% | `education_score.py` | CS/ML degrees and tier credentials |

After the weighted base score is computed, a **behavioral multiplier** (0.20–1.20) adjusts for Redrob platform signals: recency, recruiter response rate, open-to-work flag, GitHub activity, interview completion rate, and offer acceptance history.

**Guards applied before scoring:**

- **Honeypots** (`src/honeypot.py`) — profiles with suspicious skill claims (expert proficiency with <6 months, zero-endorsement experts, title/skill mismatches) receive a score of 0 and are excluded from the heap.
- **Hard rules** (`src/hard_rules.py`) — disqualified titles cap at 0.05; consulting-only careers (>95% at IT services firms) cap at 0.10.

Requirements and disqualifiers are driven by `config/jd_requirements.json`.

---

## The 5-Agent Intelligence Pipeline

Located in `src/intelligence/agents/`, the offline pipeline runs as a sequence of deterministic, rule-based agents with no LLM calls:

### Agent 1 — Job Intelligence (`agent1_job.py`)

Reads the job description (DOCX or markdown fallback) and extracts role summary, implicit requirements, culture signals, discriminator hierarchy, evaluation weights, and red-line disqualifiers.

**Output:** `precomputed/job_intelligence.json`

### Agent 2 — Candidate Intelligence (`agent2_candidate.py`)

Profiles the top-N candidates (500 full / 50 test) with career narrative typing, momentum analysis, trust metrics, product-sense fractions, and a fast keyword score for funnel narrowing.

**Output:** `precomputed/candidate_profiles/CAND_*.json`

### Agent 3 — Matching Intelligence (`agent3_matching.py`)

Scores profiles against JD discriminators (LLM/RAG engineering, MLOps/deployment, product sense, ownership) using keyword overlap and Agent 2 metrics.

**Output:** `precomputed/match_scores/CAND_*.json`

### Agent 4 — Recruiter Intelligence (`agent4_recruiter.py`)

Applies a decision tree to assign recommendation tiers, trust assessments, hiring risks, fit dimensions (technical/product/cultural/growth), and tailored interview questions.

**Output:** `precomputed/recruiter_decisions/CAND_*.json`

### Agent 5 — Reporting (`agent5_reporting.py`)

Consolidates all decisions into:

- `reasoning_map.json` — exactly 100 unique, candidate-specific reasoning strings for CSV injection
- `comparisons.json` — pairwise comparisons for adjacent top-50 candidates
- `demo_data.json` — aggregated payload for the Streamlit dashboard

---

## Streamlit Dashboard

The dashboard (`app/streamlit_app.py`) is the recruiter command center. It reads **only** from precomputed JSON files — no computation on page load, sub-second response times.

**Four views:**

| Tab | Purpose |
|---|---|
| Role brief | Discriminator hierarchies, culture signals, red-line requirements |
| Shortlist | Candidates grouped by recommendation tier with match percentages and top evidence |
| Candidate review | Fit dimensions, trust assessment, hiring risks, tailored interview questions |
| Compare | Side-by-side pairwise comparison with dimension-by-dimension score deltas |

Launch:

```bash
streamlit run app/streamlit_app.py
```

Requires `precomputed/demo_data.json` and related artifacts (produced by Agent 5).

---

## Knowledge Store & AI Layer (Optional)

The V3.10 knowledge layer adds SQLite-backed retrieval and an optional LLM copilot. **This is not used during ranking.**

### Build the knowledge store

After running the 5-agent pipeline:

```bash
python precompute_v3.py
```

This initializes `data/hireiq.db` and imports all precomputed JSON artifacts via `knowledge/ingest.py`.

### AI copilot features

The `src/ai/` module provides (when an LLM provider is configured):

- **Recruiter copilot** — answer questions about a specific candidate using retrieved context
- **Decision simulator** — explore hypothetical hiring scenarios
- **Candidate memos, interview guides, comparisons** — generated via `AIService`

Configure the provider through environment variables (see `src/ai/client.py` for Ollama and OpenAI-compatible endpoints). The ranking pipeline and agents do not depend on this layer.

---

## Validation

Validate that `submission.csv` meets the hackathon schema:

```bash
python validate_output.py submission.csv
```

A successful run prints:

```text
Submission is valid.
```

The validator checks column schema (`candidate_id`, `rank`, `score`, `reasoning`), rank ordering, score formatting, and reasoning uniqueness constraints defined in `datasets/validation/validate_submission.py`.

---

## Configuration

### Job requirements (`config/jd_requirements.json`)

Central configuration for the online scorer:

- Required skill groups and aliases (`llm_rag`, `python_ml_stack`, `vector_databases`, etc.)
- Nice-to-have skills
- Disqualifier titles and consulting companies
- Preferred locations and notice period thresholds
- Experience year brackets and scoring weights

### Test mode

Set `HIREIQ_TEST=1` or pass `--test` to `run_agents.py` to use the 50-candidate sample set and reduced funnel sizes:

| Stage | Full mode | Test mode |
|---|---|---|
| Agent 2 profiles | 500 | 50 |
| Agent 3 matches | 200 | 50 |
| Agent 4 decisions | 100 | 20 |
| Agent 5 reasoning map | 100 | 20 |

### Environment variables

| Variable | Purpose |
|---|---|
| `HIREIQ_TEST=1` | Enable test-mode funnel sizes |
| LLM provider vars | See `src/ai/client.py` (optional copilot only) |

---

## Team & Constraints

**Team:** Sententia

| Member | Role |
|---|---|
| Shashwat Kumar | Core Pipeline Engineer (Dev A) — scoring pipeline, streaming ranker, CSV writer |
| Rishik Sinha | Intelligence Layer Engineer (Dev B) — 5-agent offline pipeline, Streamlit UI |

**Compute profile (ranking step):**

- Platform: Local CPU (8 cores, 16 GB RAM)
- Python 3.11, Windows
- No GPU, no network during ranking
- Pre-computation required (~10 minutes offline)
- Processes 100K candidates in under 30 seconds with <1 GB RAM for the heap

**Methodology:** Streaming rule-based ranker with honeypot detection, hard caps for disqualified titles or consulting-only careers, six weighted fit dimensions, and a behavioral reachability multiplier. Maintains a top-200 heap during streaming, writes a validator-compliant top-100 CSV with Dev B precomputed reasoning or candidate-specific fallback reasoning.

---

## License

See repository for license details.
