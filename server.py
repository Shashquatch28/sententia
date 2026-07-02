"""
server.py

Lightweight API server exposing HireIQ intelligence and data to the frontend.

Run from the project root:
    .venv/Scripts/python server.py

Endpoints:
    GET  /api/health                  — liveness check
    POST /api/auth/demo               — instant demo token (no password)
    POST /api/auth/login              — email + password login
    GET  /api/decisions               — return all persisted pipeline decisions
    POST /api/decisions               — save a decision { candidate_id, status }
    DELETE /api/decisions/{cid}       — remove a decision
    GET  /api/roles                   — role/job summary from knowledge store
    POST /api/copilot                 — LLM answer for a recruiter question
    POST /api/simulate                — LLM what-if scenario for a candidate
    POST /api/outreach/{candidate_id} — LLM outreach email draft
"""

from __future__ import annotations

import json
import asyncio
import os
from pathlib import Path

import uvicorn
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from knowledge.storage import (
    initialize_database,
    get_connection,
    get_decisions,
    upsert_decision,
    delete_decision,
    get_run_stats,
    verify_user,
    ensure_demo_user,
    table_counts,
)
from knowledge.ingest import ingest_all, ingest_demo_data
from src.ai.service import AIService

# ------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------

ROOT = Path(__file__).parent
FRONTEND_DIR = ROOT / "frontend"
PRECOMPUTED_DIR = ROOT / "precomputed"


def _bootstrap_database() -> None:
    """Initialize and seed the local demo DB from committed artifacts."""
    initialize_database()

    counts = table_counts()
    if not counts.get("candidate_profiles") or not counts.get("match_scores"):
        ingest_all()

    ingest_demo_data()

    ensure_demo_user()   # seed demo@hireiq.com / demo123


_bootstrap_database()

_service = AIService()

# Load demo_data.json once so Copilot stats match what the frontend shows
_DEMO_DATA: dict = {}
_DEMO_JSON = PRECOMPUTED_DIR / "demo_data.json"
if _DEMO_JSON.exists():
    with open(_DEMO_JSON, encoding="utf-8") as _f:
        _DEMO_DATA = _f.read()
    _DEMO_DATA = json.loads(_DEMO_DATA)

# ------------------------------------------------------------------
# Auth helpers (itsdangerous token — no PyJWT dependency)
# ------------------------------------------------------------------

_SECRET = os.getenv("HIQ_SECRET_KEY", "hireiq-demo-secret-v1")
_signer = URLSafeTimedSerializer(_SECRET)
_TOKEN_MAX_AGE = 60 * 60 * 24 * 7   # 7 days


def _make_token(email: str, name: str) -> str:
    return _signer.dumps({"email": email, "name": name})


def _decode_token(token: str) -> dict | None:
    try:
        return _signer.loads(token, max_age=_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def _get_token(request: Request) -> dict | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return _decode_token(auth[7:])
    return None


# ------------------------------------------------------------------
# Copilot context helpers
# ------------------------------------------------------------------

def _top_candidate_id() -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT candidate_id FROM match_scores ORDER BY overall_match_score DESC LIMIT 1"
        ).fetchone()
    return dict(row)["candidate_id"] if row else None


def _has_match_score(candidate_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM match_scores WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
    return row is not None


def _build_run_context() -> str:
    """Build an aggregate context string for the Copilot using demo_data.json counts."""
    candidates = _DEMO_DATA.get("all_candidates", [])
    stats_raw = _DEMO_DATA.get("stats", {})
    by_tier = stats_raw.get("by_tier", {})

    total = len(candidates)
    scores = [c.get("overall_match_score", 0) for c in candidates if c.get("overall_match_score") is not None]
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    strong = sum(1 for s in scores if s >= 0.8)
    good = sum(1 for s in scores if 0.6 <= s < 0.8)
    weak = sum(1 for s in scores if s < 0.6)

    top5 = sorted(candidates, key=lambda c: c.get("overall_match_score", 0), reverse=True)[:5]
    top5_lines = "\n".join(
        f"  {i+1}. {c.get('name','?')} ({c.get('current_title','N/A')} at {c.get('current_company','N/A')}) "
        f"— score {c.get('overall_match_score',0):.3f}"
        f"{' — ' + c['recommendation'].replace('_',' ') if c.get('recommendation') else ''}"
        for i, c in enumerate(top5)
    )

    tier_summary = "  " + "  ·  ".join(
        f"{k.replace('_',' ')}: {v}"
        for k, v in by_tier.items() if v
    ) if by_tier else ""

    role = _DEMO_DATA.get("job_intelligence", {}).get("role_summary", "Recommendation Systems Engineer")[:120]

    return f"""Run Statistics — Recommendation Systems Engineer
{'—'*26}
Total candidates evaluated : {total}
Average match score         : {avg_score:.3f}
Score distribution:
  Strong (≥0.80) : {strong} candidates
  Good   (0.60–0.80): {good} candidates
  Weak   (<0.60) : {weak} candidates
Tier breakdown:
{tier_summary}

Top 5 Candidates (by match score):
{top5_lines}

Role context: {role}
"""


# ------------------------------------------------------------------
# Route handlers — Auth
# ------------------------------------------------------------------

async def auth_demo(request: Request) -> JSONResponse:
    """Return a demo token without requiring a password."""
    token = _make_token("demo@hireiq.com", "Demo Recruiter")
    return JSONResponse({"token": token, "email": "demo@hireiq.com", "name": "Demo Recruiter"})


async def auth_login(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not email or not password:
        return JSONResponse({"error": "email and password are required"}, status_code=400)

    user = verify_user(email, password)
    if not user:
        return JSONResponse({"error": "Invalid email or password"}, status_code=401)

    token = _make_token(user["email"], user["name"] or "Recruiter")
    return JSONResponse({"token": token, "email": user["email"], "name": user["name"]})


# ------------------------------------------------------------------
# Route handlers — Decisions
# ------------------------------------------------------------------

async def decisions_list(request: Request) -> JSONResponse:
    try:
        decisions = get_decisions()
        return JSONResponse({"decisions": decisions})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def decisions_save(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    candidate_id = (body.get("candidate_id") or "").strip()
    status = (body.get("status") or "").strip()

    if not candidate_id or status not in ("advanced", "setaside"):
        return JSONResponse(
            {"error": "candidate_id and status ('advanced'|'setaside') are required"},
            status_code=400,
        )

    try:
        upsert_decision(candidate_id, status)
        return JSONResponse({"ok": True, "candidate_id": candidate_id, "status": status})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def decisions_delete(request: Request) -> JSONResponse:
    candidate_id = request.path_params.get("candidate_id", "").strip()
    if not candidate_id:
        return JSONResponse({"error": "candidate_id path param required"}, status_code=400)
    try:
        delete_decision(candidate_id)
        return JSONResponse({"ok": True, "candidate_id": candidate_id})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Route handlers — Roles
# ------------------------------------------------------------------

async def roles_list(request: Request) -> JSONResponse:
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM job").fetchall()
        jobs = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
            jobs.append(d)
        return JSONResponse({"roles": jobs})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Route handlers — Copilot
# ------------------------------------------------------------------

async def health(request: Request) -> JSONResponse:
    counts = table_counts()
    return JSONResponse(
        {
            "status": "ok",
            "llm_provider": os.getenv("LLM_PROVIDER", "disabled"),
            "llm_model": os.getenv("LLM_MODEL", ""),
            "knowledge_store": counts,
        }
    )


async def copilot(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    question = (body.get("question") or "").strip()
    candidate_id = (body.get("candidate_id") or "").strip() or None

    if not question:
        return JSONResponse({"error": "question is required"}, status_code=400)

    # Build aggregate run context (answers pool-level questions)
    try:
        extra_context = _build_run_context()
    except Exception:
        extra_context = ""

    # Resolve candidate: provided id if scored, else top candidate
    if candidate_id and _has_match_score(candidate_id):
        cid = candidate_id
    else:
        cid = _top_candidate_id()

    try:
        answer = await asyncio.to_thread(
            _service.generate,
            task="copilot",
            candidate_id=cid,
            question=question,
            extra_context=extra_context,
        )
        return JSONResponse({"answer": answer, "candidate_id": cid})
    except RuntimeError as e:
        return JSONResponse(
            {"answer": f"LLM unavailable: {e}"},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Route handlers — Simulator
# ------------------------------------------------------------------

async def simulate(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    candidate_id = (body.get("candidate_id") or "").strip()
    scenario = (body.get("scenario") or "").strip()

    if not candidate_id or not scenario:
        return JSONResponse({"error": "candidate_id and scenario are required"}, status_code=400)

    try:
        result = await asyncio.to_thread(
            _service.generate,
            task="simulation",
            candidate_id=candidate_id,
            scenario=scenario,
        )
        return JSONResponse({"result": result})
    except RuntimeError as e:
        return JSONResponse(
            {"result": f"LLM unavailable: {e}"},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Route handlers — Outreach
# ------------------------------------------------------------------

_OUTREACH_SYSTEM = """You are a recruiter writing a brief, professional outreach email to a candidate.
Write a 3–4 sentence email that:
- Names the specific role (Recommendation Systems Engineer)
- References one or two specific things from their background
- Has a clear call to action (15-minute intro call)
Keep it human, not salesy. No fluff. Sign off as "The HireIQ Team"."""


async def outreach(request: Request) -> JSONResponse:
    candidate_id = request.path_params.get("candidate_id", "").strip()
    if not candidate_id:
        return JSONResponse({"error": "candidate_id path param required"}, status_code=400)

    if not _has_match_score(candidate_id):
        return JSONResponse({"error": "Candidate not found"}, status_code=404)

    try:
        with get_connection() as conn:
            cp = conn.execute(
                "SELECT name, current_title, current_company FROM candidate_profiles WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            ms = conn.execute(
                "SELECT payload FROM match_scores WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()

        if not cp:
            return JSONResponse({"error": "Candidate not found"}, status_code=404)

        match_payload = {}
        if ms:
            try:
                match_payload = json.loads(dict(ms)["payload"])
            except Exception:
                pass

        skills = ", ".join((match_payload.get("required_skills_matched") or [])[:3]) or "relevant technical background"
        prompt = f"""Candidate: {cp['name']}
Current role: {cp['current_title']} at {cp['current_company']}
Key matched skills: {skills}

Write the outreach email."""

        email_text = await asyncio.to_thread(
            _service.client.generate,
            system_prompt=_OUTREACH_SYSTEM,
            user_prompt=prompt,
        )
        return JSONResponse({"email": email_text, "candidate_id": candidate_id})
    except RuntimeError as e:
        return JSONResponse(
            {"email": f"LLM unavailable: {e}"},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Route handlers - Frontend
# ------------------------------------------------------------------

async def frontend_index(request: Request) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


async def frontend_signin(request: Request) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "signin.html")


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------

app = Starlette(
    routes=[
        Route("/",                              frontend_signin,  methods=["GET"]),
        Route("/index.html",                    frontend_index,   methods=["GET"]),
        Route("/signin.html",                   frontend_signin,  methods=["GET"]),
        Route("/api/health",                    health,           methods=["GET"]),
        Route("/api/auth/demo",                 auth_demo,        methods=["POST"]),
        Route("/api/auth/login",                auth_login,       methods=["POST"]),
        Route("/api/decisions",                 decisions_list,   methods=["GET"]),
        Route("/api/decisions",                 decisions_save,   methods=["POST"]),
        Route("/api/decisions/{candidate_id}",  decisions_delete, methods=["DELETE"]),
        Route("/api/roles",                     roles_list,       methods=["GET"]),
        Route("/api/copilot",                   copilot,          methods=["POST"]),
        Route("/api/simulate",                  simulate,         methods=["POST"]),
        Route("/api/outreach/{candidate_id}",   outreach,         methods=["POST"]),
        Mount("/precomputed", StaticFiles(directory=PRECOMPUTED_DIR), name="precomputed"),
        Mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend"),
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    print(f"HireIQ server starting on http://localhost:{port}")
    print("  GET    /                         — frontend sign in")
    print("  GET    /index.html                — frontend app")
    print("  GET    /api/health")
    print("  POST   /api/auth/demo")
    print("  POST   /api/auth/login           — { email, password }")
    print("  GET    /api/decisions")
    print("  POST   /api/decisions            — { candidate_id, status }")
    print("  DELETE /api/decisions/{cid}")
    print("  GET    /api/roles")
    print("  POST   /api/copilot              — { question, candidate_id? }")
    print("  POST   /api/simulate             — { candidate_id, scenario }")
    print("  POST   /api/outreach/{cid}")
    uvicorn.run(app, host="0.0.0.0", port=port)
