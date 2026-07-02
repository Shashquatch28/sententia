# Sententia

**Sententia** is a constraint-aware candidate screening, ranking, and recruiter intelligence system built for the Redrob AI hiring challenge. It processes large applicant datasets and produces structured, audit-ready hiring decisions under strict resource limits: CPU-only, no GPU, under 16 GB RAM, and under five minutes for the ranking path.

The codebase implements **HireIQ**, a two-phase architecture that separates a high-speed streaming ranker from an offline recruiter intelligence pipeline. The system answers not just who to hire, but why, what to ask in interviews, and how candidates compare.

**Repository:** [github.com/Shashquatch28/sententia](https://github.com/Shashquatch28/sententia)

---

## Summary

Sententia combines:

- A streaming ranker that scores 100K+ profiles with constant memory.
- A deterministic 5-agent intelligence pipeline that operates on the same ranked candidate set used for submission.
- Canonical dataclass models for candidate intelligence and recruiter decisions.
- A single reasoning-generation path shared by reporting and CSV output, with emergency fallback reasoning only when precomputed reasoning is unavailable.
- Deterministic semantic-score enrichment generated offline before ranking.
- Optional SQLite-backed AI copilot layer for recruiter Q&A, memos, comparisons, interview guides, and simulations.

Ranking and agent execution are deterministic. No AI API calls are made during ranking.

---

## What It Does

| Capability | Description |
|---|---|
| Streaming ranking | Scores candidates from JSON, JSONL, or JSONL.GZ without loading the whole dataset into memory. |
| Honeypot detection | Penalizes suspicious keyword-stuffed profiles and inconsistent skill claims. |
| Hard rules | Caps scores for disqualified titles or consulting-only career patterns. |
| Multi-dimensional scoring | Combines skill match, career progression, title fit, availability, experience depth, education, and behavioral signals. |
| Semantic enrichment | Adds deterministic offline semantic alignment into the skill-score path. |
| Recruiter intelligence | Generates candidate profiles, match scores, hiring decisions, interview questions, comparisons, and trust assessments. |
| Validator-compliant output | Produces top-100 `submission.csv` with unique candidate-specific reasoning. |

---

## Architecture

The current pipeline follows Blueprint v3.10 by keeping the scorer deterministic and making the ranked candidate manifest the contract between ranking and recruiter intelligence.

```text
datasets/candidates/candidates.jsonl
        |
        v
scripts/generate_semantic_scores.py
        |
        v
precomputed/semantic_scores.json
        |
        v
rank.py
        |
        +--> submission.csv
        |
        +--> precomputed/ranked_candidates.json
                  |
                  v
              run_agents.py
                  |
                  +--> Agent 1: Job Intelligence
                  +--> Agent 2: Candidate Intelligence
                  +--> Agent 3: Matching Intelligence
                  +--> Agent 4: Recruiter Decisions
                  +--> Agent 5: Reporting and Reasoning Map
                  |
                  v
precomputed/reasoning_map.json
precomputed/comparisons.json
precomputed/demo_data.json
precomputed/recruiter_decisions/*.json
```

`rank.py` writes `precomputed/ranked_candidates.json`. `run_agents.py` consumes that manifest so Agents 2-5 operate on the same ranked candidates used by the submission path.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Dashboard | Streamlit |
| Ranking | Python standard library: `json`, `gzip`, `csv`, `heapq`, `pathlib`, `argparse` |
| Job parsing | Zero-dependency DOCX extractor using `zipfile` and XML |
| Knowledge store | SQLite |
| AI copilot | Optional Ollama or OpenAI-compatible provider through `src/ai/` |
| Config | JSON in `config/jd_requirements.json` |

---

## Project Structure

```text
Sententia/
|-- app/
|   `-- streamlit_app.py
|-- config/
|   `-- jd_requirements.json
|-- datasets/
|   |-- candidates/
|   |   |-- candidates.jsonl
|   |   |-- sample_candidates.json
|   |   `-- candidate_schema.json
|   |-- docs/
|   |   |-- job_description.docx
|   |   `-- redrob_signals_doc.docx
|   `-- validation/
|       `-- validate_submission.py
|-- knowledge/
|   |-- schema.sql
|   |-- storage.py
|   `-- ingest.py
|-- precomputed/
|   |-- job_intelligence.json
|   |-- ranked_candidates.json
|   |-- semantic_scores.json
|   |-- reasoning_map.json
|   |-- comparisons.json
|   |-- demo_data.json
|   |-- candidate_profiles/
|   |-- match_scores/
|   `-- recruiter_decisions/
|-- scripts/
|   `-- generate_semantic_scores.py
|-- src/
|   |-- ai/
|   |-- intelligence/
|   |-- models/
|   |-- pipeline/
|   `-- scoring/
|-- rank.py
|-- run_agents.py
|-- precompute_v3.py
|-- validate_output.py
|-- submission.csv
`-- requirements.txt
```

Large datasets and generated local stores are intentionally ignored by Git.

---

## Installation

```bash
git clone https://github.com/Shashquatch28/sententia.git
cd sententia

python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Dataset Setup

Place the challenge data under `datasets/` using this layout:

```text
datasets/
|-- candidates/
|   |-- candidates.jsonl
|   |-- sample_candidates.json
|   `-- candidate_schema.json
|-- docs/
|   |-- job_description.docx
|   `-- redrob_signals_doc.docx
`-- validation/
    `-- validate_submission.py
```

The backend paths are centralized in `src/intelligence/paths.py`.

---

## Quick Verification

Use this flow to verify the backend locally on the full dataset:

```bash
# 1. Generate deterministic semantic scores
python scripts/generate_semantic_scores.py --out precomputed/semantic_scores.json

# 2. Create the ranked manifest and initial submission
python rank.py --candidates datasets/candidates/candidates.jsonl --out submission.csv --precomputed precomputed

# 3. Run the 5-agent intelligence pipeline on the ranked manifest
python run_agents.py

# 4. Rebuild the final submission using the generated reasoning map
python rank.py --candidates datasets/candidates/candidates.jsonl --out submission.csv --precomputed precomputed

# 5. Validate the final submission
python datasets/validation/validate_submission.py submission.csv
```

A valid run prints:

```text
Submission is valid.
```

---

## Test Mode

For a faster local smoke test:

```bash
python scripts/generate_semantic_scores.py --limit 50 --out precomputed/semantic_scores.json
python rank.py --candidates datasets/candidates/sample_candidates.json --out submission.csv --precomputed precomputed
python run_agents.py --test
python rank.py --candidates datasets/candidates/sample_candidates.json --out submission.csv --precomputed precomputed
python datasets/validation/validate_submission.py submission.csv
```

---

## Main Commands

### Generate semantic scores

```bash
python scripts/generate_semantic_scores.py --out precomputed/semantic_scores.json
```

Optional flags:

| Flag | Description |
|---|---|
| `--candidates` | Candidate file to read. Defaults to `datasets/candidates/candidates.jsonl`. |
| `--out` | Output JSON path. Defaults to `precomputed/semantic_scores.json`. |
| `--limit` | Optional candidate limit for smoke testing. |

### Rank candidates

```bash
python rank.py --candidates datasets/candidates/candidates.jsonl --out submission.csv --precomputed precomputed
```

| Flag | Description |
|---|---|
| `--candidates` | Path to `.json`, `.jsonl`, or `.jsonl.gz` candidate file. |
| `--out` | Output CSV path. |
| `--precomputed` | Directory containing semantic scores, reasoning map, and ranked manifest. |

### Run recruiter intelligence agents

```bash
python run_agents.py
```

Useful options:

| Command | Description |
|---|---|
| `python run_agents.py` | Full pipeline from the shared ranked manifest. |
| `python run_agents.py --test` | Reduced test-mode pipeline. |
| `python run_agents.py --from 3` | Resume from Agent 3. |
| `python run_agents.py --only 1` | Run only Agent 1. |

`run_agents.py` expects `precomputed/ranked_candidates.json`, which is produced by `rank.py`.

### Build knowledge store

```bash
python precompute_v3.py
```

This creates `data/hireiq.db` from the precomputed JSON artifacts.

---

## Scoring and Ranking

The final score is computed in `src/scoring/final_scorer.py` from six dimensions:

| Dimension | Weight | Purpose |
|---|---:|---|
| Skill match | 30% | Required and adjacent technical skill fit. |
| Career progression | 25% | Growth, ownership, and AI/product career trajectory. |
| Title and role fit | 15% | Fit to Senior AI Engineer style roles. |
| Availability | 15% | Location, work mode, notice period, and reachability. |
| Experience depth | 10% | Relevant experience depth against the target bracket. |
| Education | 5% | CS/ML degree and credential signals. |

The skill dimension blends keyword scoring with deterministic semantic alignment. A behavioral multiplier then adjusts for Redrob-style platform signals such as recency, responsiveness, open-to-work status, GitHub activity, interview completion, and offer acceptance history.

Before scoring, honeypot checks and hard rules cap or exclude profiles with suspicious claims, disqualified titles, or consulting-only career patterns.

---

## 5-Agent Intelligence Pipeline

All agents are deterministic and run offline.

| Agent | Output | Purpose |
|---|---|---|
| Agent 1: Job Intelligence | `precomputed/job_intelligence.json` | Extracts role requirements, discriminators, culture signals, and red-line requirements. |
| Agent 2: Candidate Intelligence | `precomputed/candidate_profiles/*.json` | Builds canonical `CandidateIntelligenceProfile` artifacts. |
| Agent 3: Matching Intelligence | `precomputed/match_scores/*.json` | Scores candidate profiles against role discriminators. |
| Agent 4: Recruiter Intelligence | `precomputed/recruiter_decisions/*.json` | Builds canonical `RecruiterDecision` artifacts with risks, recommendations, and interview questions. |
| Agent 5: Reporting | `precomputed/reasoning_map.json`, `comparisons.json`, `demo_data.json` | Generates reporting payloads, comparisons, and CSV-ready reasoning. |

Agent 5 uses the shared reasoning generator in `src/pipeline/reasoning.py`. The CSV writer uses the precomputed reasoning map when available and keeps fallback reasoning as an emergency safeguard.

---

## Streamlit Dashboard

The dashboard reads precomputed JSON files only:

```bash
streamlit run app/streamlit_app.py
```

Expected backend artifacts:

- `precomputed/demo_data.json`
- `precomputed/comparisons.json`
- `precomputed/reasoning_map.json`
- `precomputed/recruiter_decisions/*.json`
- `precomputed/candidate_profiles/*.json`
- `precomputed/match_scores/*.json`

---

## Deploy On Render

The hackathon deployment is configured as one Render web service via `render.yaml`.
The same service serves the frontend, precomputed JSON, and API backend.

Render start command:

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Required environment variables:

| Variable | Value |
|---|---|
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-1.5-flash` |
| `GEMINI_API_KEY` | Your hosted Gemini API key |
| `HIQ_SECRET_KEY` | Long random string for demo auth tokens |

After deployment, open `/api/health` and confirm it reports `"status": "ok"` and
nonzero knowledge-store counts. The full checklist is in
`RENDER_DEPLOYMENT_CHECKLIST.md`.

---

## Optional AI Layer

The AI layer is not part of ranking. It sits on top of the precomputed artifacts and SQLite knowledge store.

For deployment, use a hosted provider:

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
GEMINI_API_KEY=...
```

Local Ollama still works for development.

### Start Ollama

```bash
ollama serve
ollama pull qwen2.5:7b
```

### Confirm the provider is reachable

PowerShell:

```powershell
Invoke-RestMethod -UseBasicParsing http://localhost:11434/api/tags
```

### Build and inspect the knowledge store

```bash
python precompute_v3.py
python -c "from knowledge.storage import table_counts; print(table_counts())"
```

### Verify retrieval and AI generation

```bash
python -c "from src.ai.retrieval import get_complete_context; print(get_complete_context('CAND_0002025').keys())"
python -c "from src.ai.service import AIService; s=AIService(); print(s.generate(task='memo', candidate_id='CAND_0002025')[:500])"
python -c "from src.ai.service import AIService; s=AIService(); print(s.generate(task='interview', candidate_id='CAND_0002025')[:500])"
python -c "from src.ai.service import AIService; s=AIService(); print(s.generate(task='simulation', candidate_id='CAND_0002025', scenario='Prefer 30-day notice.')[:500])"
```

---

## Validation

Use the challenge validator:

```bash
python datasets/validation/validate_submission.py submission.csv
```

The validator checks:

- Required columns: `candidate_id`, `rank`, `score`, `reasoning`.
- Rank ordering and uniqueness.
- Score formatting.
- Candidate-specific reasoning constraints.

---

## Configuration

`config/jd_requirements.json` controls:

- Required skill groups and aliases.
- Nice-to-have skills.
- Disqualifier titles and consulting company patterns.
- Preferred locations and notice-period thresholds.
- Experience brackets and scoring weights.

Environment variables:

| Variable | Purpose |
|---|---|
| `HIREIQ_TEST=1` | Enables reduced funnel sizes for agent test mode. |
| `LLM_PROVIDER` | `gemini`, `groq`, `openai`, `openai_compatible`, `ollama`, or `disabled`. |
| `LLM_MODEL` | Hosted model name, for example `gemini-1.5-flash`. |
| `GEMINI_API_KEY` | Required when `LLM_PROVIDER=gemini`. |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq`. |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai`. |
| `LLM_API_KEY` / `LLM_API_BASE` | Required for generic OpenAI-compatible providers. |
| `HIQ_SECRET_KEY` | Token signing secret for demo auth. |
| `HIQ_DATA_DIR` | Optional SQLite data directory override for cloud/runtime testing. |

---

## Team and Constraints

| Member | Role |
|---|---|
| Shashwat Kumar | Core pipeline, scorer, streaming ranker, CSV writer |
| Rishik Sinha | Intelligence layer, recruiter outputs, UI integration |

Ranking constraints:

- CPU-only.
- No GPU.
- No network calls during ranking.
- Constant-memory top-K heap.
- Deterministic outputs.

---

## License

See repository for license details.
