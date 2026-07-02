# HireIQ Web Frontend

The frontend binds the HireIQ design language to the real intelligence data in
`precomputed/demo_data.json`.

For the hackathon deployment, the frontend is served by `server.py` from the same
Render web service as the API. That keeps auth, decisions, Copilot, AI what-if
simulation, and outreach on one public origin.

## Run

From the project root:

```bash
python server.py
```

Then open:

```text
http://localhost:8001/
```

Opening `index.html` directly with `file://` will not work because browsers block
local `fetch()` calls. Use the Python server for the complete app.

## Files

| File | Purpose |
|---|---|
| `index.html` | App shell, sidebar, top bar, command palette, candidate rail |
| `signin.html` | Demo/login entry screen |
| `styles.css` | HireIQ design system and component styling |
| `app.js` | Data loading, API calls, all lenses, and interactions |

## Main Surfaces

- Shortlist: tier-grouped candidate cards, funnel strip, real ranks, and scores.
- Role Intelligence: role narrative, discriminator hierarchy, red-line requirements, and culture signals.
- Candidate rail: recommendation, dimensions, evidence, risks, interview focus, outreach, and AI what-if.
- Comparison: two candidates side by side with dimension deltas and ranking rationale.
- Copilot: calls `/api/copilot` first, with grounded client-side retrieval fallback.
- Simulator: instant client-side re-rank plus candidate-level AI scenario generation.
- Pipeline: persists advance/set-aside decisions through `/api/decisions`.

## Data Mapping

| UI | Source |
|---|---|
| Funnel / tier counts | `precomputed/demo_data.json` |
| Cards / ranks / scores | `all_candidates` in `demo_data.json` |
| Candidate detail | `fit_assessment`, `trust_assessment`, `hiring_risks`, `interview_focus`, `timing_assessment` |
| Role Intelligence | `job_intelligence` |
| Comparison | `comparisons` |
| Copilot / simulation / outreach | Backend API routes in `server.py` |

## Deployment

Use the root `render.yaml` for Render. The deployed service serves:

- `/` and `/signin.html` for sign in
- `/index.html` for the dashboard
- `/precomputed/demo_data.json` for browser data
- `/api/*` for backend features
