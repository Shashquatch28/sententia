"""
HireIQ — AI Candidate Intelligence Dashboard
Light editorial recruiter UI (Claude Design handoff: "HireIQ App").

Loads ONLY from precomputed JSON files. No computation on page load.
Navigation is sidebar-driven via st.session_state["tab"] — robust across reruns.
"""

import json
import math
from pathlib import Path
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HireIQ — AI Candidate Intelligence",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parents[1]
PRECOMPUTED = ROOT / "precomputed"

# ---------------------------------------------------------------------------
# Design tokens (from HireIQ App.dc.html)
# ---------------------------------------------------------------------------

BG        = "#F4F2EC"
SURFACE   = "#FFFFFF"
SURFACE_2 = "#FBFAF5"
INK       = "#1B1A14"
INK_2     = "#56544A"
MUTED     = "#8E8B7E"
LINE      = "#E4E1D6"
LINE_2    = "#EEEBE2"
ACCENT    = "#1F7A4D"   # forest green
AMBER     = "#9A6B12"
AMBER_BG  = "#F4ECD9"
SLATE     = "#5C5B52"
SLATE_BG  = "#EBE9E0"
SB        = "#1C1B16"   # sidebar
BLUE      = "#2E5E8C"   # compare candidate B

# tier tones: (label, fg, bg, bar-color)
TIER_TONE = {
    "STRONGLY_ADVANCE":     ("Strongly Advance", ACCENT, "#E3EFE8", ACCENT),
    "ADVANCE":              ("Advance",          AMBER,  AMBER_BG, "#B7791F"),
    "ADVANCE_IF_POOL_THIN": ("Advance If Thin",  AMBER,  AMBER_BG, "#B7791F"),
    "REVIEW_FURTHER":       ("Review Further",   SLATE,  SLATE_BG, "#8E8B7E"),
    "DECLINE":              ("Decline",          SLATE,  SLATE_BG, "#8E8B7E"),
}

NAV = [
    ("role",      "Role brief"),
    ("shortlist", "Shortlist"),
    ("detail",    "Candidate review"),
    ("compare",   "Compare"),
]

HEADS = {
    "role": dict(
        kicker="Role intelligence",
        title="Senior AI Engineer — the brief",
        sub="What the model optimizes for, and the bar a candidate must clear.",
    ),
    "shortlist": dict(
        kicker="The shortlist",
        title="Top 100 of 100,000 scanned",
        sub="Grouped by recommendation strength. Search, filter, and open any candidate to review.",
    ),
    "detail": dict(
        kicker="Candidate review",
        title="In-depth assessment",
        sub="Trust, fit, risks, and an interview plan — the evidence behind the score.",
    ),
    "compare": dict(
        kicker="Compare",
        title="Head-to-head",
        sub="Place two candidates side by side: who is stronger on what, by how much, and when each would win.",
    ),
}

DIM_KEYS  = ["technical", "product", "cultural", "growth"]
DIM_NAMES = ["Technical", "Product", "Cultural", "Growth"]

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Archivo:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Base ── */
.stApp {{ background: {BG}; color: {INK}; }}
html, body, [class*="css"] {{ font-family: 'Archivo', sans-serif; color: {INK}; }}
/* Force ink color on ALL main-area elements so Streamlit defaults never bleed through */
[data-testid="stMain"] p,
[data-testid="stMain"] div,
[data-testid="stMain"] span,
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 {{ color: {INK}; }}
#MainMenu, header[data-testid="stHeader"], footer {{ display: none !important; }}
[data-testid="stMain"] .block-container {{
    max-width: 1180px !important;
    padding: 30px 40px 80px !important;
}}
[data-testid="stMain"] {{
    background: radial-gradient(120% 70% at 100% 0%, #ECF3EE 0%, {BG} 50%);
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background: {SB} !important;
    width: 250px !important;
    min-width: 250px !important;
}}
section[data-testid="stSidebar"] > div {{ padding-top: 22px; }}
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p {{ color: #E7E4D8 !important; }}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.35rem; }}

/* sidebar nav buttons */
section[data-testid="stSidebar"] .stButton button {{
    width: 100%;
    text-align: left;
    justify-content: flex-start;
    background: transparent;
    border: none;
    color: #B6B2A6;
    font-family: 'Archivo', sans-serif;
    font-size: 14px;
    font-weight: 500;
    padding: 10px 12px;
    border-radius: 10px;
    transition: background .15s, color .15s;
}}
section[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(255,255,255,.06);
    color: #F4F2EC;
}}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
    background: rgba(255,255,255,.08);
    color: #F4F2EC;
    font-weight: 600;
    box-shadow: inset 2px 0 0 {ACCENT};
}}

/* ── Main buttons (links, pills, prev/next) + download buttons ── */
[data-testid="stMain"] [data-testid="stDownloadButton"] button {{
    background: {SURFACE};
    border: 1px solid {LINE};
    color: {INK} !important;
    font-family: 'Archivo', sans-serif;
    font-size: 13px;
    font-weight: 600;
    border-radius: 999px;
    padding: 8px 15px;
    transition: all .15s;
    box-shadow: 0 1px 2px rgba(20,20,15,.04);
}}
[data-testid="stMain"] [data-testid="stDownloadButton"] button:hover {{
    border-color: {ACCENT};
    color: {ACCENT} !important;
}}
[data-testid="stMain"] .stButton button {{
    background: {SURFACE};
    border: 1px solid {LINE};
    color: {INK_2};
    font-family: 'Archivo', sans-serif;
    font-size: 13px;
    font-weight: 600;
    border-radius: 999px;
    padding: 8px 15px;
    transition: all .15s;
    box-shadow: 0 1px 2px rgba(20,20,15,.04);
}}
[data-testid="stMain"] .stButton button:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
[data-testid="stMain"] .stButton button[kind="primary"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #fff;
}}

/* ── Inputs ── */
[data-testid="stMain"] [data-baseweb="input"],
[data-testid="stMain"] [data-baseweb="select"] > div {{
    background: {SURFACE} !important;
    border: 1px solid {LINE} !important;
    border-radius: 11px !important;
    font-family: 'Archivo', sans-serif !important;
}}
[data-testid="stMain"] input {{ color: {INK} !important; font-size: 14px !important; }}
[data-testid="stMain"] [data-baseweb="select"] * {{ color: {INK} !important; }}

/* labels */
.kick {{ font: 600 10px/1 'JetBrains Mono', monospace; letter-spacing: .18em;
         text-transform: uppercase; color: {ACCENT} !important; }}
.lbl {{ font: 600 10px/1 'JetBrains Mono', monospace; letter-spacing: .16em;
        text-transform: uppercase; color: {MUTED} !important; }}
.serif {{ font-family: 'Newsreader', serif; color: {INK}; }}
.mono {{ font-family: 'JetBrains Mono', monospace; color: {INK}; }}

@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
section[data-testid="stMain"] section {{ animation: fadeUp .35s ease both; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loaders (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_job() -> Optional[dict]:
    p = PRECOMPUTED / "job_intelligence.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def load_demo() -> Optional[dict]:
    p = PRECOMPUTED / "demo_data.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def load_comparisons() -> dict:
    p = PRECOMPUTED / "comparisons.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(s: str) -> str:
    """Fix mojibake (replacement char) from upstream evidence strings."""
    if not s:
        return ""
    return s.replace("�", "—").replace(" — ", " — ").strip()


def tone(rec: str):
    return TIER_TONE.get(rec, ("Review Further", SLATE, SLATE_BG, "#8E8B7E"))


def dims_of(cand: dict) -> list:
    fit = cand.get("fit_assessment", {})
    return [float(fit.get(k, {}).get("score", 0.5)) for k in DIM_KEYS]


def _radar_points(scores: list) -> str:
    """Map four 0-1 scores onto the diamond (TECH top, PROD right, CULT bottom, GROWTH left)."""
    ang = [-90, 0, 90, 180]
    pts = []
    for s, a in zip(scores, ang):
        r = max(0.0, min(1.0, s)) * 100
        rad = math.radians(a)
        pts.append(f"{130 + r*math.cos(rad):.1f},{130 + r*math.sin(rad):.1f}")
    return " ".join(pts)


def _radar_grid() -> str:
    return (
        f'<polygon points="130,30 230,130 130,230 30,130" fill="none" stroke="{LINE}" stroke-width="1"></polygon>'
        f'<polygon points="130,80 180,130 130,180 80,130" fill="none" stroke="{LINE_2}" stroke-width="1"></polygon>'
        f'<line x1="130" y1="30" x2="130" y2="230" stroke="{LINE_2}" stroke-width="1"></line>'
        f'<line x1="30" y1="130" x2="230" y2="130" stroke="{LINE_2}" stroke-width="1"></line>'
    )


def _radar_labels() -> str:
    return (
        f'<text x="130" y="22" text-anchor="middle" style="font:600 10px \'JetBrains Mono\';fill:{INK_2}">TECHNICAL</text>'
        f'<text x="236" y="133" text-anchor="start" style="font:600 10px \'JetBrains Mono\';fill:{INK_2}">PRODUCT</text>'
        f'<text x="130" y="248" text-anchor="middle" style="font:600 10px \'JetBrains Mono\';fill:{INK_2}">CULTURAL</text>'
        f'<text x="24" y="133" text-anchor="end" style="font:600 10px \'JetBrains Mono\';fill:{INK_2}">GROWTH</text>'
    )


def radar_single(scores: list, ideal: list) -> str:
    return (
        '<svg viewBox="0 0 260 260" style="width:100%;max-width:230px;margin-top:6px">'
        f'{_radar_grid()}'
        f'<polygon points="{_radar_points(ideal)}" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="4 4"></polygon>'
        f'<polygon points="{_radar_points(scores)}" fill="rgba(31,122,77,.16)" stroke="{ACCENT}" stroke-width="2"></polygon>'
        f'{_radar_labels()}'
        '</svg>'
    )


def radar_dual(a: list, b: list) -> str:
    return (
        '<svg viewBox="0 0 260 260" style="width:240px;height:240px">'
        f'{_radar_grid()}'
        f'<polygon points="{_radar_points(b)}" fill="rgba(46,94,140,.14)" stroke="{BLUE}" stroke-width="2"></polygon>'
        f'<polygon points="{_radar_points(a)}" fill="rgba(31,122,77,.14)" stroke="{ACCENT}" stroke-width="2"></polygon>'
        f'{_radar_labels()}'
        '</svg>'
    )


def _not_ready():
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {LINE};border-radius:16px;'
        f'padding:48px;text-align:center;color:{MUTED}">'
        f'<div style="font-size:2rem;margin-bottom:10px">⚙️</div>'
        f'<div style="font:500 20px \'Newsreader\',serif;color:{INK}">Pipeline data not found</div>'
        f'<div style="margin-top:8px;font-size:13px">Run <code>python run_agents.py</code>, then refresh.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def card_open(extra: str = "") -> str:
    return (f'<div style="background:{SURFACE};border:1px solid {LINE};border-radius:16px;'
            f'padding:24px;box-shadow:0 1px 2px rgba(20,20,15,.04);{extra}">')


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(demo: Optional[dict]):
    stats = (demo or {}).get("stats", {})
    by_tier = stats.get("by_tier", {})
    advancing = by_tier.get("STRONGLY_ADVANCE", 0) + by_tier.get("ADVANCE", 0)

    with st.sidebar:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:0 4px">'
            f'<div style="width:30px;height:30px;border-radius:8px;background:{ACCENT};display:flex;'
            f'align-items:center;justify-content:center;font:600 15px/1 \'Newsreader\',serif;color:#fff">H</div>'
            f'<div style="font:500 23px/1 \'Newsreader\',serif;color:#fff">HireIQ</div></div>'
            f'<div style="margin:13px 0 18px;padding:11px 13px;background:rgba(255,255,255,.05);'
            f'border:1px solid rgba(255,255,255,.08);border-radius:11px">'
            f'<div style="font:600 9px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:#5FA37E">Active search</div>'
            f'<div style="font-size:13.5px;font-weight:600;color:#F4F2EC;margin-top:6px">Senior AI Engineer</div>'
            f'<div style="font-size:11.5px;color:#9C988B;margin-top:2px">Early-stage AI startup · Bengaluru</div></div>'
            f'<div style="font:600 9px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;'
            f'color:#807C70;padding:0 12px 6px">Workspace</div>',
            unsafe_allow_html=True,
        )

        for tab_id, label in NAV:
            active = st.session_state.get("tab", "shortlist") == tab_id
            if st.button(label, key=f"nav_{tab_id}",
                         type="primary" if active else "secondary",
                         use_container_width=True):
                st.session_state["tab"] = tab_id
                st.rerun()

        st.markdown(
            f'<div style="margin-top:20px;padding:15px 14px;background:rgba(255,255,255,.04);'
            f'border:1px solid rgba(255,255,255,.07);border-radius:12px">'
            f'<div style="font:600 9px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;'
            f'color:#807C70;margin-bottom:11px">Pipeline</div>'
            + "".join(
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin:7px 0">'
                f'<span style="font-size:12.5px;color:#B6B2A6">{k}</span>'
                f'<span style="font:500 17px/1 \'Newsreader\',serif;color:{c}">{v}</span></div>'
                for k, v, c in [
                    ("Scanned", "100,000", "#E7E4D8"),
                    ("Shortlisted", str(stats.get("total_evaluated", 100)), "#E7E4D8"),
                    ("Advancing", str(advancing), "#5FA37E"),
                ]
            )
            + '</div>'
            f'<div style="display:flex;align-items:center;gap:10px;padding:14px 8px 0">'
            f'<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#5C5B52,#3A3933);'
            f'display:flex;align-items:center;justify-content:center;font:600 12px/1 \'Archivo\';color:#E7E4D8">RS</div>'
            f'<div><div style="font-size:12.5px;font-weight:600;color:#F4F2EC">Recruiting · Seed</div>'
            f'<div style="font-size:11px;color:#807C70">talent@startup.ai</div></div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Brief export formatter
# ---------------------------------------------------------------------------

def _format_brief(job: Optional[dict]) -> str:
    if not job:
        return "No role intelligence data available."
    lines = []
    lines.append("=" * 60)
    lines.append("HIREIQ — ROLE BRIEF")
    lines.append("Senior AI Engineer · Early-stage AI startup · Bengaluru")
    lines.append("=" * 60)

    lines.append("\nSCORING WEIGHTS")
    lines.append("-" * 40)
    for d in job.get("discriminator_hierarchy", []):
        pct = int(round(d.get("weight", 0) * 100))
        desc = _clean(d.get("description", "") or "")
        lines.append(f"  {pct:>3}%  {d.get('name','')}:")
        if desc:
            lines.append(f"        {desc}")

    lines.append("\nNON-NEGOTIABLE REQUIREMENTS")
    lines.append("-" * 40)
    for r in job.get("red_line_requirements", []):
        lines.append(f"  — {_clean(r)}")

    lines.append("\nIDEAL CANDIDATE")
    lines.append("-" * 40)
    lines.append(_clean(job.get("ideal_candidate_narrative", "")))

    lines.append("\nCULTURE SIGNALS")
    lines.append("-" * 40)
    lines.append("  " + "  ·  ".join(job.get("culture_signals", [])))

    lines.append("\nIMPLICIT REQUIREMENTS")
    lines.append("-" * 40)
    for i in job.get("implicit_requirements", []):
        lines.append(f"  • {_clean(i)}")

    lines.append("\nSENIORITY NOTE")
    lines.append("-" * 40)
    lines.append(_clean(job.get("seniority_calibration", "")))

    lines.append("\n" + "=" * 60)
    lines.append("Generated by HireIQ · AI Candidate Intelligence")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header(tab: str, job: Optional[dict] = None):
    h = HEADS[tab]

    # Header text (left) + action buttons (right) as real Streamlit widgets
    txt_col, btn_col = st.columns([3.2, 1], gap="small")
    with txt_col:
        st.markdown(
            f'<div class="kick">{h["kicker"]}</div>'
            f'<div class="serif" style="font-size:33px;font-weight:500;line-height:1.05;'
            f'letter-spacing:-.01em;margin-top:9px;color:{INK}">{h["title"]}</div>'
            f'<div style="font-size:13.5px;color:{INK_2};margin-top:7px">{h["sub"]}</div>',
            unsafe_allow_html=True,
        )
    with btn_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if tab == "role":
            bc1, bc2 = st.columns(2)
            with bc1:
                st.download_button(
                    "Export brief", _format_brief(job),
                    file_name="role_brief.txt", mime="text/plain",
                    use_container_width=True,
                )
            with bc2:
                if st.button("Edit weights", use_container_width=True, type="primary"):
                    st.toast("Weight editing is not available in demo mode.", icon="ℹ️")
        elif tab == "shortlist":
            if st.button("Add candidate", use_container_width=True, type="primary"):
                st.toast("Manual candidate entry is not available in demo mode.", icon="ℹ️")
        elif tab == "detail":
            if st.button("Share profile", use_container_width=True, type="primary"):
                st.toast("Profile sharing is not available in demo mode.", icon="ℹ️")
        elif tab == "compare":
            if st.button("Reset", use_container_width=True, type="primary"):
                st.session_state["cmp_a"] = 0
                st.session_state["cmp_b"] = 1
                st.rerun()

    st.markdown(f'<div style="border-bottom:1px solid {LINE};margin:16px 0 26px"></div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab — Role brief
# ---------------------------------------------------------------------------

def render_role(job: dict):
    left, right = st.columns([1.12, 0.92], gap="medium")

    with left:
        # weighted scoring model
        rows = ""
        for d in job.get("discriminator_hierarchy", []):
            pct = int(round(d.get("weight", 0) * 100))
            desc = _clean(d.get("description", "") or " · ".join(d.get("signals", [])[:1]))
            rows += (
                f'<div style="margin-bottom:15px">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">'
                f'<div style="font-size:13.5px;font-weight:600">{d.get("name","")}</div>'
                f'<div class="mono" style="font:600 13px/1 \'JetBrains Mono\';color:{ACCENT}">{pct}%</div></div>'
                f'<div style="height:8px;background:{LINE_2};border-radius:5px;overflow:hidden;margin-bottom:6px">'
                f'<div style="height:100%;width:{pct}%;background:{ACCENT};border-radius:5px"></div></div>'
                f'<div style="font-size:12.5px;color:{INK_2};line-height:1.4">{desc}</div></div>'
            )
        st.markdown(
            card_open() +
            f'<div class="lbl">How the model scores</div>'
            f'<div class="serif" style="font-size:23px;font-weight:500;margin:8px 0 18px">Weighted scoring model</div>'
            f'{rows}</div>',
            unsafe_allow_html=True,
        )

        # hard filters (dark)
        reqs = job.get("red_line_requirements", [])
        req_html = "".join(
            f'<div style="display:flex;gap:10px;align-items:flex-start;font-size:13.5px;color:#E7E4D8;line-height:1.4">'
            f'<span style="color:#5FA37E;font-weight:700;flex:none">—</span><span style="color:#E7E4D8">{_clean(r)}</span></div>'
            for r in reqs
        )
        st.markdown(
            f'<div style="background:{INK};color:#F4F2EC;border-radius:16px;padding:24px;margin-top:22px">'
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:#5FA37E">Hard filters</div>'
            f'<div class="serif" style="font-size:23px;font-weight:500;margin:8px 0 16px;color:#fff">Non-negotiable requirements</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:13px 24px">{req_html}</div></div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            card_open() +
            f'<div class="lbl">Target profile</div>'
            f'<div class="serif" style="font-size:24px;font-weight:500;margin:10px 0 0">The ideal candidate</div>'
            f'<p style="font-size:14.5px;line-height:1.65;color:{INK_2};margin:12px 0 0">'
            f'{_clean(job.get("ideal_candidate_narrative",""))}</p></div>',
            unsafe_allow_html=True,
        )

        tags = "".join(
            f'<div style="border:1px solid {LINE};background:{SURFACE};border-radius:999px;padding:7px 15px;'
            f'font-size:13px;font-weight:500;color:{INK};box-shadow:0 1px 2px rgba(20,20,15,.03)">{s}</div>'
            for s in job.get("culture_signals", [])
        )
        st.markdown(
            f'<div style="margin-top:22px"><div class="lbl" style="margin-bottom:12px">Culture signals</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:9px">{tags}</div></div>',
            unsafe_allow_html=True,
        )

        impl = "".join(
            f'<div style="display:flex;gap:11px;align-items:flex-start;font-size:13.5px;color:{INK_2};line-height:1.5">'
            f'<span style="width:6px;height:6px;border-radius:50%;background:{ACCENT};margin-top:7px;flex:none"></span>'
            f'<span>{_clean(i)}</span></div>'
            for i in job.get("implicit_requirements", [])
        )
        st.markdown(
            card_open("margin-top:22px") +
            f'<div class="lbl">Reads between the lines</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 16px">Implicit requirements</div>'
            f'<div style="display:flex;flex-direction:column;gap:12px">{impl}</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div style="border:1px dashed {LINE};border-left:3px solid {ACCENT};border-radius:0 12px 12px 0;'
            f'padding:16px 20px;background:#F1F6F2;margin-top:22px">'
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.14em;text-transform:uppercase;color:{ACCENT}">Seniority note</div>'
            f'<p style="font-size:13.5px;line-height:1.6;color:{INK_2};margin:9px 0 0">'
            f'{_clean(job.get("seniority_calibration",""))}</p></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab — Shortlist
# ---------------------------------------------------------------------------

def _skills_from_evidence(evidence: list, limit: int = 4) -> list:
    skills: list = []
    for e in evidence:
        e = _clean(e)
        if not e:
            continue
        if " match" in e:
            head = e.split(" match")[0]
            # take the part after a dash if present
            head = head.split("—")[-1]
            for part in head.split(","):
                part = part.strip()
                if part and len(part) <= 26 and part not in skills:
                    skills.append(part)
        elif "(" in e and ")" in e:
            inner = e[e.find("(") + 1:e.find(")")].strip()
            if inner and len(inner) <= 26 and inner not in skills:
                skills.append(inner)
        if len(skills) >= limit:
            break
    return skills[:limit]


def render_shortlist(demo: dict):
    by_tier = demo.get("stats", {}).get("by_tier", {})
    all_cands = demo.get("all_candidates", [])
    rank_of = {c["candidate_id"]: i + 1 for i, c in enumerate(all_cands)}

    # ── tier distribution card ──
    bar_defs = [
        ("STRONGLY_ADVANCE", "Strongly Advance", ACCENT),
        ("ADVANCE",          "Advance",          "#B7791F"),
        ("REVIEW_FURTHER",   "Review Further",   "#8E8B7E"),
    ]
    counts = {k: by_tier.get(k, 0) for k, _, _ in bar_defs}
    mx = max(counts.values()) or 1

    flt = st.session_state.get("shortlist_filter", "All")
    search = st.session_state.get("shortlist_search", "")

    # compute shown count for the header
    def _passes(c):
        if flt != "All" and c.get("recommendation") != flt:
            return False
        if search:
            q = search.lower()
            blob = (c.get("name", "") + c.get("current_title", "") + c.get("current_company", "")).lower()
            if q not in blob:
                return False
        return True
    shown = sum(1 for c in all_cands if _passes(c))

    bars = ""
    for k, label, clr in bar_defs:
        cnt = counts[k]
        pct = int(cnt / mx * 100)
        bars += (
            f'<div style="display:flex;align-items:center;gap:16px">'
            f'<div style="width:150px;display:flex;align-items:center;gap:9px;flex:none">'
            f'<span style="width:9px;height:9px;border-radius:3px;background:{clr}"></span>'
            f'<span style="font-size:13.5px;font-weight:500">{label}</span></div>'
            f'<div style="flex:1;height:20px;background:{LINE_2};border-radius:6px;overflow:hidden">'
            f'<div style="height:100%;width:{pct}%;background:{clr};border-radius:6px"></div></div>'
            f'<div style="width:32px;text-align:right;font:600 15px/1 \'Newsreader\',serif;flex:none">{cnt}</div></div>'
        )
    st.markdown(
        card_open("padding:22px 24px") +
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">'
        f'<div class="lbl">Candidates per tier · top 100 of 100,000</div>'
        f'<div style="font-size:12.5px;color:{MUTED}"><strong class="mono" style="color:{INK}">{shown}</strong> shown</div></div>'
        f'<div style="display:flex;flex-direction:column;gap:13px">{bars}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── search + filter pills ──
    sc, fc = st.columns([1.4, 2])
    with sc:
        new_search = st.text_input(
            "search", value=search, placeholder="🔍  Search by name, title, company, or skill…",
            label_visibility="collapsed",
        )
        if new_search != search:
            st.session_state["shortlist_search"] = new_search
            st.rerun()
    with fc:
        pills = [("All", "All", 100)] + [(k, lbl, counts[k]) for k, lbl, _ in bar_defs]
        pcols = st.columns(len(pills))
        for col, (fid, lbl, cnt) in zip(pcols, pills):
            with col:
                if st.button(f"{lbl} {cnt}", key=f"flt_{fid}",
                             type="primary" if flt == fid else "secondary",
                             use_container_width=True):
                    st.session_state["shortlist_filter"] = fid
                    st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── candidate cards ──
    cands = [c for c in all_cands if _passes(c)]
    if not cands:
        st.markdown(
            f'<div style="color:{MUTED};font-size:14px;padding:40px;text-align:center">'
            f'No candidates match your search in this tier.</div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(2)
    for i, c in enumerate(cands):
        cid = c["candidate_id"]
        rec = c.get("recommendation", "")
        label, fg, bg, _ = tone(rec)
        pct = int(round(c.get("overall_match_score", 0) * 100))
        rank = rank_of.get(cid, i + 1)

        evidence = "".join(
            f'<div style="display:flex;gap:9px;font-size:13px;color:{INK_2};line-height:1.4">'
            f'<span style="color:{ACCENT};font-weight:700;flex:none">✓</span><span>{_clean(e)}</span></div>'
            for e in c.get("top_evidence", [])[:3]
        )
        skills = "".join(
            f'<div style="border:1px solid {LINE};border-radius:6px;padding:3px 9px;'
            f'font:500 11.5px/1.4 \'JetBrains Mono\';color:{INK_2};background:{SURFACE_2}">{s}</div>'
            for s in _skills_from_evidence(c.get("top_evidence", []))
        )
        reasoning = _clean(c.get("recommendation_rationale", ""))
        timing = c.get("timing_assessment", {})
        avail = "Open to move" if timing.get("likely_available") else "Passive — will talk"
        notice = f'{timing.get("estimated_notice_weeks", 4)} wk notice'

        with cols[i % 2]:
            st.markdown(
                card_open("padding:20px;margin-bottom:4px") +
                f'<div style="display:flex;gap:14px;align-items:flex-start">'
                f'<div class="serif" style="font-size:18px;color:{MUTED};width:28px;flex:none;padding-top:4px">{rank:02d}</div>'
                f'<div style="flex:1;min-width:0">'
                f'<div class="serif" style="font-size:19px;font-weight:500;line-height:1.1">{c.get("name","")}</div>'
                f'<div style="font-size:13px;color:{INK_2};margin-top:3px">{c.get("current_title","")} · {c.get("current_company","")}</div></div>'
                f'<div style="text-align:right;flex:none">'
                f'<div class="serif" style="font-size:31px;font-weight:500;line-height:.9">{pct}<span style="font-size:15px;color:{MUTED}">%</span></div>'
                f'<div style="display:inline-block;margin-top:6px;font:600 9px/1 \'JetBrains Mono\';letter-spacing:.08em;'
                f'text-transform:uppercase;padding:4px 9px;border-radius:999px;color:{fg};background:{bg}">{label}</div></div></div>'
                f'<div style="display:flex;flex-direction:column;gap:6px;border-top:1px solid {LINE_2};padding-top:13px;margin-top:14px">{evidence}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:12px">{skills}</div>'
                f'<div style="font:italic 400 13.5px/1.5 \'Newsreader\',serif;color:{INK_2};border-left:2px solid {LINE};padding-left:12px;margin-top:12px">{reasoning}</div>'
                f'<div style="font-size:12px;color:{MUTED};margin-top:12px">{avail} · {notice}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Review →", key=f"rev_{cid}", use_container_width=True):
                st.session_state["cand_idx"] = rank - 1
                st.session_state["tab"] = "detail"
                st.rerun()
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab — Candidate review
# ---------------------------------------------------------------------------

def render_detail(demo: dict):
    all_cands = demo.get("all_candidates", [])
    if not all_cands:
        st.warning("No candidates found.")
        return

    n = len(all_cands)
    idx = min(st.session_state.get("cand_idx", 0), n - 1)

    # ── selector + prev/next ──
    sel_col, p_col, nx_col = st.columns([6, 1, 1])
    with sel_col:
        labels = [f'#{i+1} · {c.get("name","")} — {int(round(c.get("overall_match_score",0)*100))}%'
                  for i, c in enumerate(all_cands)]
        picked = st.selectbox("Reviewing", labels, index=idx, label_visibility="collapsed")
        new_idx = labels.index(picked)
        if new_idx != idx:
            st.session_state["cand_idx"] = new_idx
            st.rerun()
    with p_col:
        if st.button("‹", key="prev_cand", use_container_width=True):
            st.session_state["cand_idx"] = (idx - 1) % n
            st.rerun()
    with nx_col:
        if st.button("›", key="next_cand", use_container_width=True):
            st.session_state["cand_idx"] = (idx + 1) % n
            st.rerun()

    c = all_cands[idx]
    rec = c.get("recommendation", "")
    label, fg, bg, _ = tone(rec)
    pct = int(round(c.get("overall_match_score", 0) * 100))
    timing = c.get("timing_assessment", {})
    avail = "Open to move" if timing.get("likely_available") else "Passive — will talk"
    notice = f'{timing.get("estimated_notice_weeks", 4)} wk notice'
    years = round(timing.get("current_tenure_months", 0) / 12)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── hero ──
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {LINE};border-radius:18px;padding:28px;'
        f'display:grid;grid-template-columns:1fr auto;gap:24px;align-items:center;box-shadow:0 1px 2px rgba(20,20,15,.04)">'
        f'<div><div class="serif" style="font-size:36px;font-weight:500;letter-spacing:-.01em">{c.get("name","")}</div>'
        f'<div style="font-size:15px;color:{INK_2};margin-top:8px">{c.get("current_title","")} · {c.get("current_company","")} · {years} yrs</div>'
        f'<div style="display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap">'
        f'<div style="display:inline-flex;align-items:center;gap:8px;padding:8px 15px;border-radius:999px;background:{bg};color:{fg};font-size:13px;font-weight:600">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{fg}"></span>{label} to onsite</div>'
        f'<div style="display:inline-flex;align-items:center;gap:7px;padding:8px 14px;border:1px solid {LINE};border-radius:999px;font-size:13px;color:{INK_2}">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:{ACCENT if timing.get("likely_available") else AMBER}"></span>{avail} · {notice}</div></div></div>'
        f'<div style="text-align:center;border-left:1px solid {LINE};padding-left:28px;min-width:150px">'
        f'<div class="serif" style="font-size:68px;font-weight:500;line-height:.85">{pct}<span style="font-size:26px;color:{MUTED}">%</span></div>'
        f'<div class="lbl" style="letter-spacing:.14em;margin-top:10px">Overall match · rank {idx+1:02d}</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── trust + skills ──
    tcol, scol = st.columns([1.25, 1], gap="medium")
    with tcol:
        trust = c.get("trust_assessment", {})
        tscore = int(round(trust.get("overall_trust_score", 0.5) * 100))
        ttier = trust.get("trust_tier", "MEDIUM").title()
        sig_html = ""
        sigs = trust.get("signals", [])[:4]
        for s in sigs:
            stype = s.get("signal_type", "")
            ok = stype in ("VERIFIED", "PLAUSIBLE")
            mark, mfg = ("✓", ACCENT) if ok else ("!", AMBER)
            sig_html += (
                f'<div style="display:flex;gap:9px;align-items:flex-start;font-size:13px;color:{INK_2};line-height:1.4">'
                f'<span style="color:{mfg};font-weight:700;flex:none">{mark}</span><span>{_clean(s.get("description",""))}</span></div>'
            )
        for flag in trust.get("red_flags", [])[:2]:
            sig_html += (
                f'<div style="display:flex;gap:9px;align-items:flex-start;font-size:13px;color:{INK_2};line-height:1.4">'
                f'<span style="color:{AMBER};font-weight:700;flex:none">!</span><span>{_clean(flag)}</span></div>'
            )
        st.markdown(
            card_open("padding:22px") +
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div><div class="lbl">Verification</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin-top:8px">Trust &amp; authenticity</div></div>'
            f'<div style="text-align:right"><div class="serif" style="font-size:30px;font-weight:500;line-height:.9;color:{ACCENT}">{tscore}<span style="font-size:15px;color:{MUTED}">/100</span></div>'
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.1em;text-transform:uppercase;color:{INK_2};margin-top:5px">{ttier} confidence</div></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:9px 18px;margin-top:16px">{sig_html}</div></div>',
            unsafe_allow_html=True,
        )
    with scol:
        matched = "".join(
            f'<div style="border:1px solid #B7D4C5;background:#EAF3EE;color:{INK};border-radius:7px;'
            f'padding:5px 11px;font:500 12px/1.4 \'JetBrains Mono\'">{s}</div>'
            for s in c.get("required_skills_matched", [])
        )
        st.markdown(
            card_open("padding:22px") +
            f'<div class="lbl">Requirements</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 16px">Required skills matched</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:8px">{matched}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── fit dimensions ──
    st.markdown('<div class="lbl" style="margin-bottom:12px">Fit breakdown · candidate vs ideal</div>',
                unsafe_allow_html=True)
    rcol, dcol = st.columns([0.82, 1.7], gap="medium")
    with rcol:
        ideal = [0.9, 0.85, 0.9, 0.85]
        st.markdown(
            card_open("padding:18px;display:flex;flex-direction:column;align-items:center") +
            f'<div class="serif" style="font-size:18px;font-weight:500;align-self:flex-start">Fit dimensions</div>'
            f'{radar_single(dims_of(c), ideal)}'
            f'<div style="display:flex;gap:16px;margin-top:6px;font:500 11px/1 \'JetBrains Mono\';color:{INK_2}">'
            f'<span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:3px;background:{ACCENT};display:inline-block"></span>Candidate</span>'
            f'<span style="display:flex;align-items:center;gap:6px"><span style="width:14px;border-top:1.5px dashed {MUTED};display:inline-block"></span>Ideal</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with dcol:
        fit = c.get("fit_assessment", {})
        cells = ""
        for k, name in zip(DIM_KEYS, DIM_NAMES):
            dd = fit.get(k, {})
            score = float(dd.get("score", 0.5))
            ev = _clean(dd.get("evidence", ["—"])[0]) if dd.get("evidence") else "—"
            gaps = dd.get("gaps", [])
            gap = _clean(gaps[0]) if gaps else "None material."
            cells += (
                f'<div style="background:{SURFACE};border:1px solid {LINE};border-radius:14px;padding:16px;box-shadow:0 1px 2px rgba(20,20,15,.04)">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
                f'<div style="font-size:14px;font-weight:600">{name}</div>'
                f'<div class="serif" style="font-size:22px;font-weight:500">{score*10:.1f}</div></div>'
                f'<div style="height:6px;background:{LINE_2};border-radius:4px;overflow:hidden;margin:10px 0 12px">'
                f'<div style="height:100%;width:{int(score*100)}%;background:{ACCENT};border-radius:4px"></div></div>'
                f'<div style="font-size:12.5px;color:{INK_2};line-height:1.45;margin-bottom:8px">'
                f'<span style="font:600 9.5px \'JetBrains Mono\';letter-spacing:.08em;text-transform:uppercase;color:{ACCENT}">Evidence</span><br/>{ev}</div>'
                f'<div style="font-size:12.5px;color:{MUTED};line-height:1.45">'
                f'<span style="font:600 9.5px \'JetBrains Mono\';letter-spacing:.08em;text-transform:uppercase;color:{MUTED}">Gap</span><br/>{gap}</div></div>'
            )
        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">{cells}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── risks + interview ──
    sev_tone = {"HIGH": ("#9A1B1B", "#F4DCDC"), "MEDIUM": (AMBER, AMBER_BG), "LOW": (SLATE, SLATE_BG)}
    rk_col, iq_col = st.columns(2, gap="medium")
    with rk_col:
        risks = sorted(c.get("hiring_risks", []),
                       key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r.get("severity", "LOW"), 2))
        items = ""
        for r in risks:
            sev = r.get("severity", "LOW")
            sfg, sbg = sev_tone.get(sev, (SLATE, SLATE_BG))
            items += (
                f'<div style="border:1px solid {LINE};border-radius:11px;overflow:hidden">'
                f'<div style="display:flex;align-items:center;gap:10px;padding:13px 16px;font-size:13.5px;font-weight:600">'
                f'<span style="font:600 9px/1 \'JetBrains Mono\';letter-spacing:.06em;text-transform:uppercase;'
                f'padding:3px 7px;border-radius:5px;color:{sfg};background:{sbg}">{sev[:3]}</span>{r.get("risk_type","Risk")}</div>'
                f'<div style="padding:0 16px 14px;font-size:13px;line-height:1.55;color:{INK_2}">'
                f'<div style="margin-bottom:8px">{_clean(r.get("description",""))}</div>'
                f'<div style="font-size:12.5px"><span style="font:600 9px \'JetBrains Mono\';letter-spacing:.06em;'
                f'text-transform:uppercase;color:{ACCENT}">Mitigation</span><br/>{_clean(r.get("mitigation",""))}</div></div></div>'
            )
        st.markdown(
            card_open("padding:22px") +
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:{AMBER}">Watch for</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 16px">Hiring risks</div>'
            f'<div style="display:flex;flex-direction:column;gap:10px">{items}</div></div>',
            unsafe_allow_html=True,
        )
    with iq_col:
        qs = sorted(c.get("interview_focus", []),
                    key=lambda q: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(q.get("priority", "LOW"), 2))
        items = ""
        for q in qs:
            wtlf = _clean(q.get("what_to_listen_for", ""))
            items += (
                f'<div style="border:1px solid {LINE};border-radius:11px;overflow:hidden">'
                f'<div style="padding:13px 16px;font-size:13.5px;font-weight:600">{_clean(q.get("question",""))}</div>'
                f'<div style="padding:0 16px 14px;font-size:13px;line-height:1.55;color:{INK_2}">{wtlf}</div></div>'
            )
        st.markdown(
            card_open("padding:22px") +
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:{ACCENT}">Onsite plan</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 16px">Suggested interview questions</div>'
            f'<div style="display:flex;flex-direction:column;gap:10px">{items}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── footer stats ──
    foot = [
        ("Time to shortlist", "2.3 hrs"),
        ("Sources scanned", "14"),
        ("Availability", "Open" if timing.get("likely_available") else "Passive"),
        ("Notice period", f'{timing.get("estimated_notice_weeks", 4)} wks'),
    ]
    cells = "".join(
        f'<div style="background:{SURFACE};padding:18px 20px">'
        f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.12em;text-transform:uppercase;color:{MUTED}">{k}</div>'
        f'<div class="serif" style="font-size:24px;font-weight:500;margin-top:9px">{v}</div></div>'
        for k, v in foot
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:{LINE};'
        f'border:1px solid {LINE};border-radius:14px;overflow:hidden">{cells}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    _, a_col, b_col = st.columns([6, 1.4, 1.6])
    with a_col:
        if st.button("Add to compare", key="add_compare", use_container_width=True):
            st.session_state["cmp_a"] = idx
            st.session_state["tab"] = "compare"
            st.rerun()
    with b_col:
        advanced = c["candidate_id"] in st.session_state.get("advanced_candidates", set())
        btn_label = "✓ Advanced to onsite" if advanced else "Advance to onsite →"
        if st.button(btn_label, key="advance", type="primary", use_container_width=True, disabled=advanced):
            name = c.get("name", "Candidate")
            st.session_state.setdefault("advanced_candidates", set()).add(c["candidate_id"])
            st.toast(f"✅ {name} has been advanced to onsite interview.", icon="🎯")
            st.rerun()


# ---------------------------------------------------------------------------
# Tab — Compare
# ---------------------------------------------------------------------------

def render_compare(demo: dict):
    all_cands = demo.get("all_candidates", [])
    if len(all_cands) < 2:
        st.warning("Need at least 2 candidates.")
        return

    n = len(all_cands)
    labels = [f'#{i+1} · {c.get("name","")} — {int(round(c.get("overall_match_score",0)*100))}%'
              for i, c in enumerate(all_cands)]

    ai = min(st.session_state.get("cmp_a", 0), n - 1)
    bi = min(st.session_state.get("cmp_b", 1), n - 1)

    a_col, b_col = st.columns(2, gap="medium")
    with a_col:
        st.markdown(f'<div class="kick" style="margin-bottom:8px">Candidate A</div>', unsafe_allow_html=True)
        la = st.selectbox("A", labels, index=ai, key="sel_a", label_visibility="collapsed")
        if labels.index(la) != ai:
            st.session_state["cmp_a"] = labels.index(la); st.rerun()
    with b_col:
        st.markdown(f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.14em;'
                    f'text-transform:uppercase;color:{BLUE};margin-bottom:8px">Candidate B</div>', unsafe_allow_html=True)
        lb = st.selectbox("B", labels, index=bi, key="sel_b", label_visibility="collapsed")
        if labels.index(lb) != bi:
            st.session_state["cmp_b"] = labels.index(lb); st.rerun()

    A, B = all_cands[ai], all_cands[bi]
    pa = int(round(A.get("overall_match_score", 0) * 100))
    pb = int(round(B.get("overall_match_score", 0) * 100))

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # summary cards
    sa, sb = st.columns(2, gap="medium")
    with sa:
        st.markdown(
            f'<div style="background:#EAF3EE;border:1px solid #B7D4C5;border-radius:16px;padding:22px;'
            f'display:flex;justify-content:space-between;align-items:center">'
            f'<div><div class="serif" style="font-size:24px;font-weight:500;line-height:1.05">{A.get("name","")}</div>'
            f'<div style="font-size:13px;color:{INK_2};margin-top:4px">{A.get("current_title","")} · {A.get("current_company","")}</div></div>'
            f'<div class="serif" style="font-size:46px;font-weight:500;line-height:.85">{pa}<span style="font-size:18px;color:{MUTED}">%</span></div></div>',
            unsafe_allow_html=True,
        )
    with sb:
        st.markdown(
            f'<div style="background:#EAF0F6;border:1px solid #C9D8E6;border-radius:16px;padding:22px;'
            f'display:flex;justify-content:space-between;align-items:center">'
            f'<div><div class="serif" style="font-size:24px;font-weight:500;line-height:1.05">{B.get("name","")}</div>'
            f'<div style="font-size:13px;color:{INK_2};margin-top:4px">{B.get("current_title","")} · {B.get("current_company","")}</div></div>'
            f'<div class="serif" style="font-size:46px;font-weight:500;line-height:.85">{pb}<span style="font-size:18px;color:{MUTED}">%</span></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # radar + table
    va, vb = dims_of(A), dims_of(B)
    rows = ""
    for k, name in zip(DIM_KEYS, DIM_NAMES):
        a = float(A.get("fit_assessment", {}).get(k, {}).get("score", 0.5)) * 10
        b = float(B.get("fit_assessment", {}).get(k, {}).get("score", 0.5)) * 10
        win = "—" if abs(a - b) < 0.05 else ("A" if a > b else "B")
        wfg = ACCENT if win == "A" else (BLUE if win == "B" else MUTED)
        wbg = "#E3EFE8" if win == "A" else ("#E3ECF5" if win == "B" else "transparent")
        diff = ("+" if a >= b else "−") + f"{abs(a-b):.1f}"
        rows += (
            f'<div style="display:grid;grid-template-columns:1.4fr .7fr .9fr .7fr .8fr;padding:12px 16px;'
            f'border-bottom:1px solid {LINE_2};align-items:center;font-size:13.5px">'
            f'<div style="font-weight:600">{name}</div>'
            f'<div style="text-align:center;font-family:\'JetBrains Mono\';color:{INK if a>=b else MUTED};font-weight:600">{a:.1f}</div>'
            f'<div style="text-align:center"><span style="display:inline-block;min-width:22px;font:600 11px/1 \'JetBrains Mono\';'
            f'padding:3px 7px;border-radius:6px;color:{wfg};background:{wbg}">{win}</span></div>'
            f'<div style="text-align:center;font-family:\'JetBrains Mono\';color:{INK if b>=a else MUTED};font-weight:600">{b:.1f}</div>'
            f'<div style="text-align:right;font-family:\'JetBrains Mono\';color:{INK_2}">{diff}</div></div>'
        )

    st.markdown(
        card_open("padding:22px;display:grid;grid-template-columns:auto 1fr;gap:28px;align-items:center") +
        f'<div style="display:flex;flex-direction:column;align-items:center">{radar_dual(va, vb)}'
        f'<div style="display:flex;gap:16px;margin-top:6px;font:500 11px/1 \'JetBrains Mono\';color:{INK_2}">'
        f'<span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:3px;background:{ACCENT};display:inline-block"></span>A</span>'
        f'<span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:3px;background:{BLUE};display:inline-block"></span>B</span></div></div>'
        f'<div><div class="lbl">Head to head</div>'
        f'<div class="serif" style="font-size:23px;font-weight:500;margin:8px 0 16px">Fit dimension comparison</div>'
        f'<div style="border:1px solid {LINE};border-radius:12px;overflow:hidden">'
        f'<div style="display:grid;grid-template-columns:1.4fr .7fr .9fr .7fr .8fr;padding:9px 16px;'
        f'font:600 10px/1 \'JetBrains Mono\';letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
        f'background:{SURFACE_2};border-bottom:1px solid {LINE}">'
        f'<div>Dimension</div><div style="text-align:center">A</div><div style="text-align:center">Winner</div>'
        f'<div style="text-align:center">B</div><div style="text-align:right">Diff</div></div>'
        f'{rows}</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # recommendation / counter-case
    comps = load_comparisons()
    cid_a, cid_b = A["candidate_id"], B["candidate_id"]
    comp = comps.get(f"{cid_a}_{cid_b}") or comps.get(f"{cid_b}_{cid_a}")

    a_wins = pa >= pb
    winner, loser = (A, B) if a_wins else (B, A)
    win_letter, lose_letter = ("A", "B") if a_wins else ("B", "A")

    # widest edges
    best_w, best_wv, best_l, best_lv = DIM_NAMES[0], -99, DIM_NAMES[0], -99
    for k, name in zip(DIM_KEYS, DIM_NAMES):
        d = (winner.get("fit_assessment", {}).get(k, {}).get("score", 0.5)
             - loser.get("fit_assessment", {}).get(k, {}).get("score", 0.5)) * 10
        if d > best_wv:
            best_wv, best_w = d, name
        if -d > best_lv:
            best_lv, best_l = -d, name

    why = (comp.get("why_a_over_b") if comp else None) or (
        f'{winner.get("name","")} ranks higher overall ({max(pa,pb)}% vs {min(pa,pb)}%), with the widest '
        f'edge on {best_w} (+{best_wv:.1f}). {_clean(winner.get("recommendation_rationale",""))}'
    )
    when = (comp.get("b_salvage_scenario") if comp else None) or (
        f'{loser.get("name","")} becomes the stronger pick if {best_l} is weighted most — leading there by '
        f'{best_lv:.1f} — or if you favour their profile over {winner.get("name","").split()[0]}’s on that axis.'
    )

    rc, cc = st.columns(2, gap="medium")
    with rc:
        st.markdown(
            f'<div style="background:{INK};color:#F4F2EC;border-radius:16px;padding:24px">'
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:#5FA37E">Recommendation</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 12px;color:#fff">Why {win_letter} is stronger</div>'
            f'<p style="font-size:14px;line-height:1.6;color:#DEDBCF;margin:0">{_clean(why)}</p></div>',
            unsafe_allow_html=True,
        )
    with cc:
        st.markdown(
            card_open("padding:24px") +
            f'<div style="font:600 10px/1 \'JetBrains Mono\';letter-spacing:.16em;text-transform:uppercase;color:{BLUE}">Counter-case</div>'
            f'<div class="serif" style="font-size:22px;font-weight:500;margin:8px 0 12px">When {lose_letter} would be preferred</div>'
            f'<p style="font-size:14px;line-height:1.6;color:{INK_2};margin:0">{_clean(when)}</p></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.session_state.setdefault("tab", "shortlist")

    demo = load_demo()
    job = load_job()

    render_sidebar(demo)

    tab = st.session_state["tab"]
    render_header(tab, job=job)

    if tab == "role":
        if job:
            render_role(job)
        else:
            _not_ready()
    elif tab == "shortlist":
        if demo:
            render_shortlist(demo)
        else:
            _not_ready()
    elif tab == "detail":
        if demo:
            render_detail(demo)
        else:
            _not_ready()
    elif tab == "compare":
        if demo:
            render_compare(demo)
        else:
            _not_ready()


if __name__ == "__main__":
    main()
