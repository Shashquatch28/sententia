# HireIQ — Web Frontend

A faithful implementation of the HireIQ design language (`Design guidelines review/`),
bound to the **real** intelligence data in `precomputed/demo_data.json`.

It is a static, self-contained web app — **no backend, no API, no build step**. It reads
the precomputed JSON directly in the browser, so it changes nothing in the Python pipeline,
the agents, or the knowledge store.

## Run

Serve the repo root over HTTP (the page fetches `../precomputed/demo_data.json`):

```bash
# from the project root
python -m http.server 8000
```

Then open: **http://localhost:8000/frontend/**

> Opening `index.html` directly with `file://` will not work — browsers block `fetch()`
> of local files. It must be served over HTTP (any static server is fine).

## What's here

| File | Purpose |
|------|---------|
| `index.html` | App shell — sidebar, top bar, ⌘K palette, candidate rail |
| `styles.css` | The design system (tokens, type, components) from the design docs |
| `app.js` | Data loading + all six lenses + interactions |

## Lenses (the six data-backed surfaces from the Information Architecture)

- **Shortlist** (home) — tier-grouped candidate cards, funnel strip, real ranks & scores
- **Role Intelligence** — AI narrative, discriminator hierarchy, red-line requirements, culture signals
- **Candidate rail** — opens in place: recommendation, dimension breakdown, evidence, risks, interview focus, timing
- **Comparison** — two candidates side by side with dimension deltas and "why #1 over #2"
- **Copilot** — grounded retrieval over the loaded data (no hallucination; honest redirect for off-topic)
- **Simulator** — adjust scoring weights, instant client-side re-rank with movement deltas
- **⌘K** command palette — jump to a candidate or a lens

## Data mapping

| UI | Source in `demo_data.json` |
|----|----------------------------|
| Funnel / tier counts | `stats`, `candidates_by_tier` |
| Cards / ranks / scores | `all_candidates` (sorted by `overall_match_score`) |
| Candidate detail | `fit_assessment`, `trust_assessment`, `hiring_risks`, `interview_focus`, `timing_assessment`, `recommendation_rationale` |
| Role Intelligence | `job_intelligence` |
| Comparison | `comparisons` |

## Notes & scope

- The Copilot here is **client-side grounded retrieval** — it filters/explains real records
  and never invents facts. (The Python `src/ai` Copilot/Simulator that call Ollama are a
  separate server-side path; this static frontend deliberately needs no backend so the demo
  runs anywhere, including Streamlit/static hosting.)
- The Simulator re-ranks over the available fit dimensions (technical, product, cultural,
  growth, trust, availability). "Default" reproduces the baseline order, so presets show
  clear movement.
- Screens in the design set that have **no backend data** (Sign In, Onboarding, Role
  Creation, Pipeline, Outreach, Analytics, Audit, Settings, Admin) are intentionally not
  built — there is no auth/user/API layer to back them, and the brief was to use real data.
