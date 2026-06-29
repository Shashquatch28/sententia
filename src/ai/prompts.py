"""
src/ai/prompts.py

Centralized prompt templates for the HireIQ AI layer.

Responsibilities
----------------
- Store all prompt templates.
- Keep prompts separate from application logic.
- Provide a single place for prompt versioning.

No API calls.
No retrieval.
No business logic.
"""

# ---------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------

SYSTEM_PROMPT = """
You are HireIQ, an AI recruiter assistant.

Rules:
- Use ONLY the provided context.
- Never invent candidate information.
- Never fabricate experience, skills, companies or scores.
- If the requested information is unavailable, explicitly state that.
- Keep responses factual, concise and recruiter-oriented.
"""

# ---------------------------------------------------------------------
# Recruiter Copilot
# ---------------------------------------------------------------------

COPILOT_SYSTEM_PROMPT = """
You assist recruiters in understanding candidate rankings,
match scores, recruiter decisions and job requirements.

Use only retrieved SQLite context.

Do not hallucinate.

Explain your reasoning clearly.
"""

# ---------------------------------------------------------------------
# Candidate Memo
# ---------------------------------------------------------------------

CANDIDATE_MEMO_PROMPT = """
Write a recruiter memo for this candidate.

Include:

- Overall hiring recommendation
- Technical strengths
- Risks
- Missing skills
- Interview focus
- Final recommendation

Use only supplied context.
Do not invent placeholders, signatures, dates, or metadata.
Return only the recruiter memo, unless memo unavilable.
"""

# ---------------------------------------------------------------------
# Candidate Comparison
# ---------------------------------------------------------------------

COMPARISON_PROMPT = """
Compare Candidate A and Candidate B.

Explain:

- Technical differences
- Match score differences
- Recruiter recommendation differences
- Hiring risks
- Which candidate is stronger
- Why

Use only supplied context.
Start with a comparison table.

| Category | Candidate A | Candidate B |
"""

# ---------------------------------------------------------------------
# Interview Guide
# ---------------------------------------------------------------------

INTERVIEW_GUIDE_PROMPT = """
Generate recruiter interview guidance.

Include:

- Technical questions
- Product questions
- Ownership questions
- Risk validation questions

Base every question on retrieved evidence only.
Generate questions that validate the evidence rather than repeating it.
"""

# ---------------------------------------------------------------------
# Decision Explanation
# ---------------------------------------------------------------------

DECISION_EXPLANATION_PROMPT = """
Explain why this hiring recommendation was made.

Reference:

- Candidate profile
- Match score
- Recruiter decision
- Job intelligence

Do not introduce any new facts.
"""

# ---------------------------------------------------------------------
# Prompt Version
# ---------------------------------------------------------------------

PROMPT_VERSION = "v1.1"