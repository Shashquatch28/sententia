# HireIQ — Candidate Ranking & Recruiter Intelligence System

HireIQ is a high-performance, constraint-aware candidate screening, ranking, and recruiter intelligence system. It is designed to process massive applicant datasets (e.g., 100,000+ candidates) and generate structured, audit-ready hiring decisions under extreme resource constraints (no GPU, <16GB RAM, <5 minutes execution time).

---

## 📖 Table of Contents
1. [Overview](#-overview)
2. [Tech Stack](#-tech-stack)
3. [Key Challenges Solved](#-key-challenges-solved)
4. [System Architecture](#-system-architecture)
5. [The 5-Agent Intelligence Pipeline](#-the-5-agent-intelligence-pipeline)
6. [Scoring & Ranking Logic](#-scoring--ranking-logic)
7. [Streamlit UI Dashboard](#-streamlit-ui-dashboard)
8. [Project Structure](#-project-structure)
9. [Installation & Setup](#-installation--setup)
10. [How to Use](#-how-to-use)
11. [Verification & Validation](#-verification--validation)

---

## 🎯 Overview

Naive candidate screening tools often suffer from two major flaws:
1. **Keyword Stuffing Exploitation:** Candidates gaming the system by packing their profiles with relevant terms without actual experience.
2. **"Score-Only" Outputs:** Providing a simple sorted list of scores without context on *why* they are ranked this way, *what* to ask them, or *how* they compare to other candidates.

**HireIQ** addresses these challenges using a **two-phase architecture** that decouples deep, batch-oriented recruiter analysis from high-speed streaming ranking. It answers not just *who* to hire, but *why*, *what to ask them*, and *how they compare* to the next best candidate.

---

## 💻 Tech Stack

- **Language:** Python 3.8+
- **Frontend / Dashboard:** [Streamlit](https://streamlit.io/)
- **Data Processing:** Native Python (`json`, `gzip`, `pathlib`) for zero-dependency, ultra-fast file streaming.
- **Memory Management:** `heapq` for maintaining a constant-memory Top-K buffer.
- **Logging & CLI:** Standard Python `logging` and `argparse`.

*Note: The system operates entirely without external databases (like PostgreSQL or Redis) or heavy data manipulation libraries (like Pandas), ensuring strict compliance with resource and latency constraints.*

---

## 🛡️ Key Challenges Solved

- **Honeypot & Fraud Detection:** Heuristic-based filters penalize keyword stuffers and profiles with inconsistent histories (e.g., claiming advanced skills with zero duration or no supporting career history).
- **Resource Constraints:** Processes 100,000 candidates in under 30 seconds with constant memory overhead (<1GB RAM).
- **Recommendation & Structured Decisions:** Sorts shortlisted candidates into actionable hiring tiers (`STRONGLY_ADVANCE`, `ADVANCE`, `REVIEW_FURTHER`, `ADVANCE_IF_POOL_THIN`, `DECLINE`).
- **Pairwise Comparative Reasoning:** Explains exactly why Candidate A ranks above adjacent Candidate B, providing real-world salvage scenarios.

---

## 🏗️ System Architecture

HireIQ splits compute tasks into offline and online phases to maximize efficiency:

```text
┌─────────────────────────────────────────────────────────┐
│                      OFFLINE PHASE                      │
│  (Batch processing of Job Description & Top Candidates)  │
│                                                         │
│   Job Desc (DOCX/MD) ──► Agent 1: Job Intelligence      │
│   Candidates (JSONL) ──► Agent 2: Candidate Intel      │
│   Profiles (JSON)    ──► Agent 3: Matching Intel       │
│   Scores (JSON)      ──► Agent 4: Recruiter Intel      │
│   Decisions (JSON)   ──► Agent 5: Reporting            │
│                                 │                       │
└─────────────────────────────────┼───────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────┐
│                      ONLINE PHASE                       │
│      (High-Speed Streaming & Heap-Based Ranking)        │
│                                                         │
│   100K Candidates ──► Stream Parser ──► Final Scorer     │
│                             │                  ▲        │
│                             ▼                  │        │
│                         Honeypots &        Reasoning    │
│                         Hard Rules         Map (JSON)   │
│                             │                           │
│                             ▼                           │
│                        Top-K Heap ──► submission.csv    │
└─────────────────────────────────────────────────────────┘
```

---

## 🤖 The 5-Agent Intelligence Pipeline

Located in `src/intelligence/agents/`, the offline pipeline runs as a sequence of deterministic, rule-based agents:

1. **Agent 1: Job Intelligence (`agent1_job.py`)**  
   Analyzes the Job Description to extract implicit/explicit requirements, red lines (disqualifiers), culture fit signals, and sets the evaluation weights.
2. **Agent 2: Candidate Intelligence (`agent2_candidate.py`)**  
   Profiles candidates to identify career narrative types (e.g., Deepening Specialist, Domain Pivoter), career momentum, and red/green flags. Extracts trust metrics and product-sense fractions.
3. **Agent 3: Matching Intelligence (`agent3_matching.py`)**  
   Scores profiles against JD discriminators (e.g., LLM/RAG Engineering, Product-Sense, Ownership) and extracts matched skills and identified gaps.
4. **Agent 4: Recruiter Intelligence (`agent4_recruiter.py`)**  
   Applies a decision tree to categorize candidates into recommendation tiers, establishes trust tiers, determines hiring risks, and generates tailored interview questions based on the candidate's specific profile.
5. **Agent 5: Reporting Agent (`agent5_reporting.py`)**  
   Consolidates profiles, generates pairwise comparisons for adjacent top-50 candidates (explaining why one ranks above another), and outputs the final reasoning map injected into the CSV.

---

## 🧮 Scoring & Ranking Logic

The online streaming pipeline evaluates every candidate across 6 primary dimensions using the `src/scoring/` modules:

1. **Title & Role Fit:** Analyzes current and past job titles for relevance to the target role (e.g., Senior AI Engineer vs. Marketing Manager).
2. **Skill Match:** Cross-references claimed skills with required skills, factoring in proficiency levels and duration.
3. **Career Progression:** Evaluates upward mobility and trajectory (e.g., Engineer -> Senior -> Staff).
4. **Experience Depth:** Measures total relevant years of experience against the role's target bracket.
5. **Education & Certifications:** Checks for foundational degrees in CS/ML and relevant tier credentials.
6. **Availability & Behavioral Multipliers:** Applies penalties or boosts based on notice periods, recruiter response rates, and "open to work" flags.

**Hard Rules:** Candidates lacking critical requirements or possessing severe disqualifiers are capped via `hard_rules.py`.

---

## 📊 Streamlit UI Dashboard

The interactive dashboard (`app/streamlit_app.py`) serves as the recruiter's command center. It reads purely from the precomputed JSON files, ensuring sub-second load times. 

It features 4 main tabs:
- **🏢 Role Intelligence:** Displays discriminator hierarchies, culture signals, and red-line requirements.
- **📋 Shortlist:** Groups candidates into actionable tiers (`STRONGLY_ADVANCE`, etc.) with quick-glance match percentages and top evidence.
- **👤 Candidate Detail:** Deep-dive into a candidate's fit dimensions, trust assessment, hiring risks, and tailored interview questions.
- **⚖️ Compare:** Side-by-side pairwise comparison of two candidates, highlighting dimension-by-dimension score deltas and explaining why one is preferred over the other.

---

## 📁 Project Structure

```text
Sententia/
├── app/
│   └── streamlit_app.py        # Interactive UI dashboard
├── datasets/                   # Input data (candidates.jsonl, JDs, schemas)
├── docs/                       # Architectural blueprints (V1 & V2)
├── precomputed/                # Output artifacts from the 5-Agent pipeline
├── src/                        # Core application logic
│   ├── intelligence/           # The 5 offline rule-based agents
│   ├── pipeline/               # High-speed streaming, parsing, and buffering
│   ├── scoring/                # Multidimensional scoring modules
│   ├── hard_rules.py           # Disqualifiers and score caps
│   └── honeypot.py             # Keyword-stuffing detection
├── rank.py                     # Entry point for the online ranking pipeline
├── run_agents.py               # Entry point for the offline pre-computation pipeline
├── validate_output.py          # Validation script for submission.csv
└── requirements.txt            # Python dependencies
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Setup Workspace
Clone the repository and enter the directory:
```bash
git clone <repository-url>
cd Sententia
```

### 3. Create a Virtual Environment
Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 How to Use

### Step 1: Pre-compute Intelligence (Offline Phase)
Run the batch pre-computation script to analyze the job description and candidate profiles. This populates the `precomputed/` directory.
```bash
python run_agents.py
```
*For a quick dry-run with a smaller pool of 50 candidates, run with the `--test` flag:*
```bash
python run_agents.py --test
```

### Step 2: Run the Ranking Pipeline (Online Phase)
Scan the candidate dataset to calculate final scores, filter out honeypots, inject precomputed reasoning, and produce the final CSV:
```bash
python rank.py --candidates datasets/candidates.jsonl --out submission.csv
```

### Step 3: Run the Streamlit UI Dashboard
Launch the dashboard to interactively visualize the role, shortlisted tiers, and side-by-side candidate comparisons:
```bash
streamlit run app/streamlit_app.py
```

---

## 🧪 Verification & Validation

To ensure the output CSV meets the hackathon constraints and contains the correct schema format, run the validator:
```bash
python validate_output.py submission.csv
```
A successful validation will print:
```text
Submission is valid.
```
