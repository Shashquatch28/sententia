"""
HireIQ — AI Candidate Intelligence Dashboard (v2)
Dark-theme professional recruiter UI.
Loads ONLY from precomputed JSON files. No computation on page load.
"""

import json
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HireIQ — AI Candidate Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parents[1]
PRECOMPUTED = ROOT / "precomputed"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER_COLORS = {
    "STRONGLY_ADVANCE":     "#22c55e",
    "ADVANCE":              "#3b82f6",
    "REVIEW_FURTHER":       "#f59e0b",
    "ADVANCE_IF_POOL_THIN": "#8b5cf6",
    "DECLINE":              "#ef4444",
}
TIER_LABELS = {
    "STRONGLY_ADVANCE":     "Strongly Advance",
    "ADVANCE":              "Advance",
    "REVIEW_FURTHER":       "Review Further",
    "ADVANCE_IF_POOL_THIN": "Advance If Pool Thin",
    "DECLINE":              "Decline",
}
TIER_ICONS = {
    "STRONGLY_ADVANCE":     "🟢",
    "ADVANCE":              "🔵",
    "REVIEW_FURTHER":       "🟡",
    "ADVANCE_IF_POOL_THIN": "🟣",
    "DECLINE":              "🔴",
}

BG_PAGE    = "#0f172a"
BG_CARD    = "#1e293b"
BG_BORDER  = "#334155"
TXT_PRI    = "#f1f5f9"
TXT_MUT    = "#94a3b8"

PLOTLY_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color=TXT_PRI),
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(f"""
<style>
/* ── Base ── */
.stApp {{ background-color: {BG_PAGE}; }}
section[data-testid="stSidebar"] {{ display: none; }}
.block-container {{ padding-top: 2.5rem !important; padding-bottom: 2rem; max-width: 100% !important; }}
div[data-testid="stAppViewBlockContainer"] {{ padding-top: 2rem !important; }}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 12px;
    padding: 4px 6px;
    gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent;
    color: {TXT_MUT};
    border-radius: 8px;
    padding: 8px 22px;
    font-weight: 600;
    font-size: 0.875rem;
    border: none;
}}
.stTabs [aria-selected="true"] {{
    background: #1e3a5f !important;
    color: #60a5fa !important;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 12px;
    padding: 16px 20px !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TXT_MUT} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}}
[data-testid="stMetricValue"] {{
    color: {TXT_PRI} !important;
    font-size: 1.7rem !important;
    font-weight: 800 !important;
}}

/* ── Cards ── */
.cand-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    transition: transform 0.15s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}}
.cand-card:hover {{
    border-color: #3b82f6;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}}

/* ── Hover polish on detail/compare cards ── */
.hover-lift {{
    transition: transform 0.15s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}}
.hover-lift:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}}

/* ── Typography helpers ── */
.section-title {{
    font-size: 0.72rem;
    font-weight: 700;
    color: {TXT_MUT};
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #3b82f633;
}}
.tier-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}
.culture-pill {{
    display: inline-block;
    background: #1e3a5f;
    border: 1px solid #3b82f6;
    color: #93c5fd;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    margin: 3px 4px 3px 0;
}}

/* ── Signal tags ── */
.sig-verified   {{ color: #4ade80; font-weight: 700; font-size: 0.72rem; }}
.sig-plausible  {{ color: #60a5fa; font-weight: 700; font-size: 0.72rem; }}
.sig-suspicious {{ color: #f87171; font-weight: 700; font-size: 0.72rem; }}

/* ── Callout boxes ── */
.callout-blue {{
    background: #0f2744;
    border-left: 4px solid #3b82f6;
    padding: 14px 18px;
    border-radius: 0 10px 10px 0;
    color: #bfdbfe;
    font-style: italic;
    margin: 8px 0;
    line-height: 1.6;
}}
.callout-amber {{
    background: #1c1200;
    border-left: 4px solid #f59e0b;
    padding: 14px 18px;
    border-radius: 0 10px 10px 0;
    color: #fef3c7;
    margin: 8px 0;
    line-height: 1.6;
}}
.callout-listen {{
    background: #0d1f38;
    border-left: 3px solid #3b82f6;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    color: #93c5fd;
    font-size: 0.83rem;
    margin-top: 10px;
    line-height: 1.5;
}}

/* ── Compare winner badges ── */
.winner-a {{ background:#14532d; color:#4ade80; padding:2px 8px; border-radius:10px; font-size:0.68rem; font-weight:700; }}
.winner-b {{ background:#1c2a4a; color:#60a5fa; padding:2px 8px; border-radius:10px; font-size:0.68rem; font-weight:700; }}
.winner-tie {{ background:{BG_CARD}; color:#64748b; padding:2px 8px; border-radius:10px; font-size:0.68rem; }}

/* ── Misc ── */
.no-data {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 12px;
    padding: 48px;
    text-align: center;
    color: {TXT_MUT};
}}
hr.divider {{
    border: none;
    border-top: 1px solid {BG_BORDER};
    margin: 22px 0;
}}

/* ── Header gradient accent ── */
.accent-bar {{
    height: 3px;
    width: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, #22c55e, #3b82f6, #8b5cf6);
    margin: 4px 0 18px 0;
}}
.brand-title {{
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #60a5fa, #34d399);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}

/* ── Skill pills ── */
.skill-pill {{
    display: inline-block;
    background: #1e3a5f;
    border: 1px solid #3b82f655;
    color: #93c5fd;
    padding: 2px 9px;
    border-radius: 12px;
    font-size: 0.68rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
}}
.skill-pill-green {{
    display: inline-block;
    background: #14331f;
    border: 1px solid #22c55e66;
    color: #6ee7a8;
    padding: 3px 11px;
    border-radius: 12px;
    font-size: 0.74rem;
    font-weight: 600;
    margin: 3px 5px 3px 0;
}}
.rank-badge {{
    display: inline-block;
    background: #0f172a;
    border: 1px solid {BG_BORDER};
    color: {TXT_MUT};
    padding: 1px 8px;
    border-radius: 8px;
    font-size: 0.68rem;
    font-weight: 700;
    margin-bottom: 6px;
}}

/* ── HTML progress bars ── */
.pbar-track {{
    width: 100%;
    height: 8px;
    background: #0f172a;
    border-radius: 6px;
    overflow: hidden;
    margin: 6px 0;
}}
.pbar-fill {{
    height: 100%;
    border-radius: 6px;
}}

/* ── Ghost buttons (View Details) ── */
div[data-testid="stButton"] > button {{
    background: transparent !important;
    border: 1px solid #3b82f6 !important;
    color: #60a5fa !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: all 0.18s ease !important;
}}
div[data-testid="stButton"] > button:hover {{
    background: #1e3a5f !important;
    border-color: #60a5fa !important;
    color: #bfdbfe !important;
    transform: translateY(-1px);
}}

/* ── Expanders ── */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {{
    background: #162032 !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 6px !important;
}}
[data-testid="stExpander"] details {{
    background: transparent !important;
    border: 1px solid {BG_BORDER} !important;
    border-radius: 8px !important;
}}

/* ── Discriminator table ── */
.disc-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
    margin-top: 6px;
}}
.disc-table th {{
    text-align: left;
    color: {TXT_MUT};
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 8px 10px;
    border-bottom: 1px solid {BG_BORDER};
}}
.disc-table td {{
    padding: 9px 10px;
    color: #cbd5e1;
    border-bottom: 1px solid #1e293b;
    vertical-align: top;
}}
.disc-table tr:hover td {{ background: #162032; }}

/* ── Shimmer animation on ideal-candidate border ── */
@keyframes shimmer {{
    0%   {{ border-left-color: #3b82f6; }}
    50%  {{ border-left-color: #34d399; }}
    100% {{ border-left-color: #3b82f6; }}
}}
.ideal-box {{
    background: #162032;
    border-left: 4px solid #3b82f6;
    padding: 16px 18px;
    border-radius: 0 10px 10px 0;
    color: #cbd5e1;
    font-style: italic;
    line-height: 1.75;
    font-size: 0.875rem;
    animation: shimmer 3s ease-in-out infinite;
}}

/* ── Score circle glow ── */
.score-circle {{
    border-radius: 18px;
    padding: 26px 16px;
    text-align: center;
    margin-top: 4px;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: #0f172a; }}
::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: #3b82f6; }}
</style>
""", unsafe_allow_html=True)


def _pbar(score: float, color: str) -> str:
    """Return an HTML progress bar string filled to score (0-1) with the given color."""
    pct = max(0, min(100, int(score * 100)))
    return (f'<div class="pbar-track"><div class="pbar-fill" '
            f'style="width:{pct}%;background:{color};"></div></div>')


def _extract_skills(evidence: list, limit: int = 3) -> list:
    """Pull short skill phrases out of top_evidence strings for compact pills."""
    skills: list = []
    for e in evidence:
        if not e:
            continue
        # Prefer the phrase before " match" (e.g. "Qdrant, Weights & Biases match LLM...")
        if " match" in e:
            head = e.split(" match")[0]
            for part in head.split(","):
                part = part.strip()
                if part and len(part) <= 28 and part not in skills:
                    skills.append(part)
        # Otherwise pull text inside parentheses
        elif "(" in e and ")" in e:
            inner = e[e.find("(") + 1:e.find(")")].strip()
            if inner and len(inner) <= 28 and inner not in skills:
                skills.append(inner)
        if len(skills) >= limit:
            break
    return skills[:limit]


# ---------------------------------------------------------------------------
# Data loaders (all cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_job_intelligence() -> Optional[dict]:
    p = PRECOMPUTED / "job_intelligence.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def load_demo_data() -> Optional[dict]:
    p = PRECOMPUTED / "demo_data.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def load_decision(cid: str) -> Optional[dict]:
    p = PRECOMPUTED / "recruiter_decisions" / f"{cid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def load_comparisons() -> dict:
    p = PRECOMPUTED / "comparisons.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tier_badge(tier: str) -> str:
    c = TIER_COLORS.get(tier, "#64748b")
    l = TIER_LABELS.get(tier, tier)
    return f'<span class="tier-badge" style="background:{c}22;border:1px solid {c};color:{c};">{l}</span>'


def clean_reasoning(text: str, name: str) -> str:
    """Remove the duplicate name/company prefix that appears in some reasoning strings."""
    if not text or not name:
        return text
    first_name = name.split()[0]
    parts = text.split(" — ", 1)
    if len(parts) == 2 and first_name in parts[1]:
        inner = parts[1].split(" — ", 1)
        if len(inner) == 2 and first_name in inner[0]:
            return parts[0] + " — " + inner[1]
    return text


def _not_ready():
    st.markdown("""
<div class="no-data">
    <div style="font-size:2rem; margin-bottom:12px;">⚙️</div>
    <div style="font-size:1.1rem; font-weight:700; color:#f1f5f9; margin-bottom:8px;">Pipeline data not found</div>
    <div style="font-size:0.85rem;">Run <code>python run_agents.py</code> then refresh.</div>
</div>""", unsafe_allow_html=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def radar_fig(categories: list, values: list, name: str, color: str, height: int = 280) -> go.Figure:
    cats = categories + [categories[0]]
    vals = values + [values[0]]
    fig = go.Figure(go.Scatterpolar(
        r=vals, theta=cats, fill="toself", name=name,
        line=dict(color=color, width=2),
        fillcolor=_hex_to_rgba(color, 0.15),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        height=height,
        showlegend=False,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=9), gridcolor=BG_BORDER),
            angularaxis=dict(tickfont=dict(size=11), gridcolor=BG_BORDER),
        ),
        margin=dict(l=40, r=40, t=20, b=20),
    )
    return fig


def dual_radar_fig(categories: list, va: list, vb: list, na: str, nb: str,
                   radial_max: float = 1.0) -> go.Figure:
    cats = categories + [categories[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=va + [va[0]], theta=cats, fill="toself", name=na,
                                   line=dict(color="#3b82f6", width=2), fillcolor="rgba(59,130,246,0.15)"))
    fig.add_trace(go.Scatterpolar(r=vb + [vb[0]], theta=cats, fill="toself", name=nb,
                                   line=dict(color="#f59e0b", width=2), fillcolor="rgba(245,158,11,0.15)"))
    fig.update_layout(
        **PLOTLY_BASE,
        height=320,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5,
                    font=dict(size=11, color=TXT_MUT)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, radial_max], tickfont=dict(size=9), gridcolor=BG_BORDER),
            angularaxis=dict(tickfont=dict(size=11), gridcolor=BG_BORDER),
        ),
        margin=dict(l=40, r=40, t=20, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header():
    demo = load_demo_data()
    stats = demo.get("stats", {}) if demo else {}
    by_tier = stats.get("by_tier", {})
    advancing = by_tier.get("STRONGLY_ADVANCE", 0) + by_tier.get("ADVANCE", 0)
    avg = stats.get("avg_match_score", 0)

    st.markdown(
        f'<div style="display:flex;align-items:baseline;margin-bottom:6px;">'
        f'<span style="font-size:2.1rem;margin-right:8px;">🎯</span>'
        f'<span class="brand-title">HireIQ</span>'
        f'<span style="color:{TXT_MUT};font-size:0.88rem;margin-left:14px;">'
        f'AI Candidate Intelligence &nbsp;·&nbsp; Senior AI Engineer @ Redrob AI</span>'
        f'</div>'
        f'<div class="accent-bar"></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates Scanned", "100,000")
    c2.metric("Decisions Made", stats.get("total_evaluated", 100))
    c3.metric("Advancing", advancing)
    c4.metric("Avg Match Score", f"{avg:.1%}")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab 1 — Role Intelligence
# ---------------------------------------------------------------------------

def render_role_intelligence():
    job = load_job_intelligence()
    if not job:
        _not_ready()
        return

    left, right = st.columns([1, 1.2], gap="large")

    with left:
        st.markdown('<div class="section-title">Scoring Weight Distribution</div>', unsafe_allow_html=True)
        discs = job.get("discriminator_hierarchy", [])
        labels  = [d["name"] for d in discs]
        weights = [d["weight"] for d in discs]
        colors  = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#06b6d4"]

        fig = go.Figure(go.Pie(
            labels=labels, values=weights, hole=0.58,
            marker=dict(colors=colors, line=dict(color=BG_PAGE, width=2)),
            textinfo="percent", textfont=dict(size=12, color=TXT_PRI),
            hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>",
        ))
        fig.update_layout(
            **PLOTLY_BASE, height=320,
            showlegend=True,
            legend=dict(x=1.02, y=0.5, font=dict(size=10.5, color=TXT_MUT)),
            annotations=[dict(text="Scoring<br>Weights", x=0.5, y=0.5,
                              font=dict(size=12, color=TXT_MUT), showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)

        # Discriminator detail table — show all signals in full (no truncation)
        rows = ""
        for d in discs:
            sigs = d.get("signals", [])
            sig_html = "".join(
                f'<div style="margin:2px 0;line-height:1.45;">• {s}</div>' for s in sigs
            )
            rows += (
                f'<tr><td style="color:#60a5fa;font-weight:700;">{d.get("rank","")}</td>'
                f'<td style="color:#f1f5f9;font-weight:600;">{d.get("name","")}</td>'
                f'<td style="color:#34d399;font-weight:700;">{int(d.get("weight",0)*100)}%</td>'
                f'<td style="color:#94a3b8;font-size:0.72rem;">{sig_html}</td></tr>'
            )
        st.markdown(
            '<table class="disc-table"><thead><tr>'
            '<th>#</th><th>Discriminator</th><th>Weight</th><th>Key Signals</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top:20px;">Red-Line Requirements</div>',
                    unsafe_allow_html=True)
        for req in job.get("red_line_requirements", []):
            st.markdown(
                f'<div style="background:#2d0a0a;border:1px solid #ef4444;border-radius:8px;'
                f'padding:10px 14px;color:#fca5a5;font-size:0.82rem;margin-bottom:6px;">⛔ {req}</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<div class="section-title">Ideal Candidate</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ideal-box">{job.get("ideal_candidate_narrative", "")}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top:22px;">Culture Signals</div>',
                    unsafe_allow_html=True)
        badges = " ".join(f'<span class="culture-pill">{s}</span>'
                          for s in job.get("culture_signals", []))
        st.markdown(badges, unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:22px;">Implicit Requirements</div>',
                    unsafe_allow_html=True)
        for req in job.get("implicit_requirements", []):
            st.markdown(
                f'<div style="color:{TXT_MUT};font-size:0.82rem;margin:5px 0;padding-left:12px;'
                f'border-left:2px solid {BG_BORDER};">→ {req}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-title" style="margin-top:22px;">Seniority Calibration</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#1e2d1e;border:1px solid #22c55e33;border-radius:8px;'
            f'padding:12px 16px;color:#86efac;font-size:0.82rem;line-height:1.6;">'
            f'{job.get("seniority_calibration", "")}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 2 — Shortlist
# ---------------------------------------------------------------------------

def render_shortlist():
    demo = load_demo_data()
    if not demo:
        _not_ready()
        return

    tiers_data = demo.get("candidates_by_tier", {})
    by_tier    = demo.get("stats", {}).get("by_tier", {})

    # Tier bar chart — ordered so Strongly Advance sits at the TOP
    # (plotly horizontal bars render the first list item at the bottom, so reverse)
    tier_keys   = ["REVIEW_FURTHER", "ADVANCE", "STRONGLY_ADVANCE"]
    tier_names  = ["Review Further", "Advance", "Strongly Advance"]
    tier_clrs   = ["#f59e0b", "#3b82f6", "#22c55e"]
    tier_counts = [by_tier.get(k, 0) for k in tier_keys]

    fig = go.Figure(go.Bar(
        x=tier_counts, y=tier_names, orientation="h",
        marker=dict(color=tier_clrs),
        text=[str(c) for c in tier_counts],
        textposition="inside",
        textfont=dict(size=13, color="#0f172a"),
        hovertemplate="%{y}: %{x} candidates<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_BASE, height=130,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color=TXT_MUT)),
        bargap=0.38,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Search
    search = st.text_input(
        "search", placeholder="🔍  Search by name, title or company...",
        label_visibility="collapsed",
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Build a global rank lookup from the full sorted list
    rank_lookup = {c["candidate_id"]: i + 1
                   for i, c in enumerate(demo.get("all_candidates", []))}

    # Eligibility sub-tabs — one per tier that has candidates
    tier_order = ["STRONGLY_ADVANCE", "ADVANCE", "REVIEW_FURTHER", "ADVANCE_IF_POOL_THIN", "DECLINE"]
    present = [t for t in tier_order if tiers_data.get(t)]
    if not present:
        st.info("No candidates to display.")
        return

    sub_labels = [
        f"{TIER_ICONS.get(t, '⚪')}  {TIER_LABELS.get(t, t)} ({len(tiers_data.get(t, []))})"
        for t in present
    ]
    sub_tabs = st.tabs(sub_labels)

    for sub_tab, tier in zip(sub_tabs, present):
        with sub_tab:
            _render_tier_cards(tiers_data.get(tier, []), tier, rank_lookup, search)


def _render_tier_cards(candidates: list, tier: str, rank_lookup: dict, search: str):
    """Render the 2-column candidate card grid for a single eligibility tier."""
    if search:
        q = search.lower()
        candidates = [c for c in candidates
                      if q in c.get("name", "").lower()
                      or q in c.get("current_title", "").lower()
                      or q in c.get("current_company", "").lower()]

    if not candidates:
        st.markdown(
            f'<div style="color:{TXT_MUT};font-size:0.85rem;padding:24px;text-align:center;">'
            f'No candidates match your search in this tier.</div>',
            unsafe_allow_html=True,
        )
        return

    color = TIER_COLORS.get(tier, "#64748b")

    cols = st.columns(2)
    for i, cand in enumerate(candidates):
        cid       = cand["candidate_id"]
        name      = cand.get("name", cid)
        title     = cand.get("current_title", "")
        company   = cand.get("current_company", "")
        pct       = int(cand.get("overall_match_score", 0) * 100)
        evidence  = cand.get("top_evidence", [])[:2]
        reasoning = clean_reasoning(cand.get("reasoning", ""), name)
        rank      = rank_lookup.get(cid)

        ev_html = "".join(
            f'<div style="color:{TXT_MUT};font-size:0.79rem;margin:3px 0;">• {e}</div>'
            for e in evidence
        )

        skills = _extract_skills(cand.get("top_evidence", []))
        skill_html = ""
        if skills:
            skill_html = ('<div style="margin-top:10px;">'
                          + "".join(f'<span class="skill-pill">{s}</span>' for s in skills)
                          + '</div>')

        rank_html = f'<span class="rank-badge">#{rank}</span>' if rank else ""

        with cols[i % 2]:
            st.markdown(f"""
<div class="cand-card" style="border-left:4px solid {color};">
  {rank_html}
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
    <div style="flex:1;min-width:0;">
      <div style="font-weight:700;color:{TXT_PRI};font-size:0.97rem;white-space:nowrap;
                  overflow:hidden;text-overflow:ellipsis;">{name}</div>
      <div style="color:{TXT_MUT};font-size:0.79rem;margin-top:2px;">{title} · {company}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:12px;">
      {tier_badge(tier)}
      <div style="color:{color};font-weight:800;font-size:1.5rem;line-height:1.2;margin-top:4px;">{pct}%</div>
    </div>
  </div>
  {ev_html}
  {skill_html}
  <div style="font-size:0.76rem;color:#64748b;font-style:italic;margin-top:10px;
              border-top:1px solid {BG_BORDER};padding-top:8px;line-height:1.5;">
    "{reasoning}"
  </div>
</div>""", unsafe_allow_html=True)

            if st.button("View Details →", key=f"view_{cid}_{tier}", use_container_width=True):
                st.session_state["selected_candidate"] = cid
                st.session_state["switch_to_detail"] = True
                st.rerun()


# ---------------------------------------------------------------------------
# Tab 3 — Candidate Detail
# ---------------------------------------------------------------------------

def render_candidate_detail():
    demo = load_demo_data()
    if not demo:
        _not_ready()
        return

    all_cands = demo.get("all_candidates", [])
    if not all_cands:
        st.warning("No candidates found.")
        return

    options = {
        f"{c.get('name', c['candidate_id'])} — {c.get('current_title','')} @ {c.get('current_company','')}": c["candidate_id"]
        for c in all_cands
    }
    keys = list(options.keys())

    pre = st.session_state.get("selected_candidate")
    default = 0
    if pre:
        for i, cid in enumerate(options.values()):
            if cid == pre:
                default = i
                break

    selected_label = st.selectbox("Candidate", keys, index=default, label_visibility="collapsed")
    cid = options[selected_label]
    dec = load_decision(cid)

    if dec is None:
        st.error(f"No decision file found for {cid}.")
        return

    name      = dec.get("name", cid)
    title     = dec.get("current_title", "")
    company   = dec.get("current_company", "")
    rec       = dec.get("recommendation", "")
    rationale = dec.get("recommendation_rationale", "")
    pct       = int(dec.get("overall_match_score", 0) * 100)
    color     = TIER_COLORS.get(rec, "#64748b")

    # ── Header ──────────────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(
            f'<div style="font-size:1.65rem;font-weight:800;color:{TXT_PRI};margin-bottom:4px;">{name}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="color:{TXT_MUT};font-size:0.88rem;margin-bottom:10px;">📍 {title} at {company}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(tier_badge(rec), unsafe_allow_html=True)
        st.markdown(
            f'<div style="margin-top:14px;color:#94a3b8;font-style:italic;font-size:0.875rem;'
            f'line-height:1.65;background:#162032;border-left:3px solid {color};'
            f'padding:12px 16px;border-radius:0 8px 8px 0;">{rationale}</div>',
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f'<div class="score-circle" style="background:{color}18;border:2px solid {color};'
            f'box-shadow:0 0 20px {color}55, 0 0 40px {color}22;">'
            f'<div style="font-size:3rem;font-weight:800;color:{color};line-height:1;">{pct}%</div>'
            f'<div style="color:{color};font-size:0.70rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-top:10px;">{TIER_LABELS.get(rec, rec)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Trust Assessment ────────────────────────────────────────────────
    st.markdown('<div class="section-title">Trust Assessment</div>', unsafe_allow_html=True)
    trust       = dec.get("trust_assessment", {})
    trust_score = trust.get("overall_trust_score", 0.5)
    trust_tier  = trust.get("trust_tier", "MEDIUM")
    tc          = {"HIGH": "#22c55e", "MEDIUM": "#f59e0b", "LOW": "#ef4444"}.get(trust_tier, "#64748b")

    tl, tr = st.columns([1, 3])
    with tl:
        st.markdown(
            f'<div style="background:{tc}18;border:1px solid {tc};border-radius:12px;'
            f'padding:18px 14px;text-align:center;">'
            f'<div style="font-size:1.9rem;font-weight:800;color:{tc};">{int(trust_score * 100)}%</div>'
            f'<div style="color:{tc};font-size:0.68rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.06em;margin-top:5px;margin-bottom:8px;">Trust — {trust_tier}</div>'
            f'{_pbar(trust_score, tc)}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with tr:
        for sig in trust.get("signals", [])[:5]:
            sig_type = sig.get("signal_type", "")
            cls = {"VERIFIED": "sig-verified", "PLAUSIBLE": "sig-plausible",
                   "SUSPICIOUS": "sig-suspicious"}.get(sig_type, "sig-plausible")
            st.markdown(
                f'<div style="margin:7px 0;">'
                f'<span class="{cls}">[{sig_type}]</span> '
                f'<span style="color:#cbd5e1;font-size:0.84rem;">{sig.get("description","")}</span></div>',
                unsafe_allow_html=True,
            )
        for flag in trust.get("red_flags", []):
            st.warning(f"⚠ {flag}")

    # Required skills matched
    matched_skills = dec.get("required_skills_matched", [])
    if matched_skills:
        st.markdown('<div class="section-title" style="margin-top:18px;">Required Skills Matched</div>',
                    unsafe_allow_html=True)
        st.markdown(
            "".join(f'<span class="skill-pill-green">✓ {s}</span>' for s in matched_skills),
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Fit Dimensions ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Fit Dimensions</div>', unsafe_allow_html=True)
    fit       = dec.get("fit_assessment", {})
    dim_keys  = ["technical", "product", "cultural", "growth"]
    dim_names = ["Technical", "Product", "Cultural", "Growth"]
    dim_vals  = [fit.get(k, {}).get("score", 0.5) for k in dim_keys]

    rc, bc = st.columns([1, 1.4])
    with rc:
        st.plotly_chart(radar_fig(dim_names, dim_vals, name, color, height=320),
                        use_container_width=True)
    with bc:
        dc1, dc2 = st.columns(2)
        for idx, (dk, dn) in enumerate(zip(dim_keys, dim_names)):
            dd  = fit.get(dk, {})
            ds  = dd.get("score", 0.5)
            dc  = "#22c55e" if ds >= 0.7 else ("#f59e0b" if ds >= 0.45 else "#ef4444")
            col = dc1 if idx % 2 == 0 else dc2

            ev_html = "".join(
                f'<div style="color:#4ade80;font-size:0.75rem;margin-top:4px;">✓ {ev}</div>'
                for ev in dd.get("evidence", [])[:2]
            )
            gap_html = "".join(
                f'<div style="color:#f87171;font-size:0.75rem;margin-top:3px;">✗ {gap}</div>'
                for gap in dd.get("gaps", [])[:1]
            )
            with col:
                st.markdown(
                    f'<div class="hover-lift" style="background:#162032;border:1px solid {BG_BORDER};'
                    f'border-radius:10px;padding:14px;margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                    f'<span style="font-size:0.75rem;font-weight:700;color:{TXT_MUT};text-transform:uppercase;'
                    f'letter-spacing:0.06em;">{dn}</span>'
                    f'<span style="font-size:1.3rem;font-weight:800;color:{dc};">{int(ds * 100)}%</span>'
                    f'</div>'
                    f'{_pbar(ds, dc)}'
                    f'{ev_html}{gap_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Risks + Interview Questions ────────────────────────────────────
    risk_col, q_col = st.columns(2)

    with risk_col:
        st.markdown('<div class="section-title">Hiring Risks</div>', unsafe_allow_html=True)
        risks = sorted(dec.get("hiring_risks", []),
                       key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r.get("severity", "LOW"), 2))
        for risk in risks:
            sev = risk.get("severity", "LOW")
            sc  = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}.get(sev, "#64748b")
            with st.expander(f"[{sev}] {risk.get('risk_type','Risk')}", expanded=(sev == "HIGH")):
                st.markdown(f'<span style="color:{sc};font-size:0.83rem;">{risk.get("description","")}</span>',
                            unsafe_allow_html=True)
                st.markdown(f"**Mitigation:** {risk.get('mitigation','')}")
                if risk.get("is_blocking"):
                    st.error("⛔ Blocking — Do not advance")

    with q_col:
        st.markdown('<div class="section-title">Interview Focus</div>', unsafe_allow_html=True)
        questions = sorted(dec.get("interview_focus", []),
                           key=lambda q: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(q.get("priority","LOW"), 2))
        pri_dot = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        for q in questions:
            pri = q.get("priority", "LOW")
            dim = q.get("dimension", "")
            txt = q.get("question", "")
            dot = pri_dot.get(pri, "🟢")
            with st.expander(f"{dot} {dim} — {txt[:55]}...", expanded=(pri == "HIGH")):
                st.markdown(f"**{txt}**")
                wtlf = q.get("what_to_listen_for", "")
                if wtlf:
                    st.markdown(f'<div class="callout-listen">👂 {wtlf}</div>', unsafe_allow_html=True)

    # ── Timing ────────────────────────────────────────────────────────
    timing = dec.get("timing_assessment")
    if timing:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Timing & Availability</div>', unsafe_allow_html=True)
        tm1, tm2, tm3 = st.columns(3)
        tm1.metric("Current Tenure",  f"{timing.get('current_tenure_months', 0)} months")
        tm2.metric("Available",       "Yes ✓" if timing.get("likely_available") else "Unclear")
        tm3.metric("Notice Period",   f"{timing.get('estimated_notice_weeks', 4)} weeks")
        if timing.get("urgency_signal"):
            st.markdown(
                f'<div style="color:{TXT_MUT};font-size:0.82rem;font-style:italic;margin-top:10px;">'
                f'💡 {timing["urgency_signal"]}</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tab 4 — Compare
# ---------------------------------------------------------------------------

def render_compare():
    demo = load_demo_data()
    if not demo:
        _not_ready()
        return

    all_cands = demo.get("all_candidates", [])
    if len(all_cands) < 2:
        st.warning("Need at least 2 candidates.")
        return

    options = {
        f"#{i+1} — {c.get('name', c['candidate_id'])} ({c.get('current_title','')})": c["candidate_id"]
        for i, c in enumerate(all_cands[:50])
    }
    keys = list(options.keys())

    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f'<div style="color:#3b82f6;font-weight:700;margin-bottom:4px;font-size:0.82rem;">CANDIDATE A</div>',
                    unsafe_allow_html=True)
        la = st.selectbox("A", keys, index=0, key="cmp_a", label_visibility="collapsed")
    with s2:
        st.markdown(f'<div style="color:#f59e0b;font-weight:700;margin-bottom:4px;font-size:0.82rem;">CANDIDATE B</div>',
                    unsafe_allow_html=True)
        lb = st.selectbox("B", keys, index=1, key="cmp_b", label_visibility="collapsed")

    cid_a, cid_b = options[la], options[lb]
    if cid_a == cid_b:
        st.warning("Select two different candidates.")
        return

    da = load_decision(cid_a)
    db = load_decision(cid_b)
    if not da or not db:
        st.error("Decision file missing for one or both candidates.")
        return

    na = da.get("name", cid_a)
    nb = db.get("name", cid_b)
    ra, rb   = da.get("recommendation",""), db.get("recommendation","")
    ca, cb   = TIER_COLORS.get(ra,"#64748b"), TIER_COLORS.get(rb,"#64748b")
    pct_a    = int(da.get("overall_match_score",0) * 100)
    pct_b    = int(db.get("overall_match_score",0) * 100)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Candidate header cards
    ha, hb = st.columns(2)
    for col, dec_, n_, c_, pct_, label_ in [(ha, da, na, ca, pct_a, "A"), (hb, db, nb, cb, pct_b, "B")]:
        border = "#3b82f6" if label_ == "A" else "#f59e0b"
        with col:
            st.markdown(
                f'<div style="background:{BG_CARD};border:2px solid {border};border-radius:12px;padding:18px;">'
                f'<div style="font-size:0.70rem;font-weight:700;color:{border};text-transform:uppercase;'
                f'letter-spacing:0.08em;margin-bottom:6px;">CANDIDATE {label_}</div>'
                f'<div style="font-size:1.05rem;font-weight:700;color:{TXT_PRI};">{n_}</div>'
                f'<div style="color:{TXT_MUT};font-size:0.80rem;margin-top:2px;">'
                f'{dec_.get("current_title","")} · {dec_.get("current_company","")}</div>'
                f'<div style="display:flex;align-items:center;gap:10px;margin-top:10px;">'
                f'{tier_badge(dec_.get("recommendation",""))}'
                f'<span style="color:{border};font-weight:800;font-size:1.2rem;">{pct_}%</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Overall score bars (A = blue, B = amber)
    sb1, sb2 = st.columns(2)
    with sb1:
        st.markdown(
            f'<div style="margin-top:14px;"><span style="color:#3b82f6;font-size:0.72rem;'
            f'font-weight:700;">OVERALL {pct_a}%</span>{_pbar(pct_a / 100, "#3b82f6")}</div>',
            unsafe_allow_html=True,
        )
    with sb2:
        st.markdown(
            f'<div style="margin-top:14px;"><span style="color:#f59e0b;font-size:0.72rem;'
            f'font-weight:700;">OVERALL {pct_b}%</span>{_pbar(pct_b / 100, "#f59e0b")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Radar + dimension table
    fit_a = da.get("fit_assessment", {})
    fit_b = db.get("fit_assessment", {})
    dkeys = ["technical", "product", "cultural", "growth"]
    dnames = ["Technical", "Product", "Cultural", "Growth"]
    va = [fit_a.get(k, {}).get("score", 0.5) for k in dkeys]
    vb = [fit_b.get(k, {}).get("score", 0.5) for k in dkeys]

    rc, tc = st.columns([1, 1.2])
    with rc:
        st.markdown('<div class="section-title">Fit Comparison</div>', unsafe_allow_html=True)

        # Zoom controls — smaller radial max = zoomed in (shapes appear larger)
        zoom_levels = [1.0, 0.75, 0.5, 0.35, 0.25]
        zi = st.session_state.get("radar_zoom_idx", 0)

        zc1, zc2, zc3 = st.columns([1, 1, 2])
        with zc1:
            if st.button("➖ Zoom out", key="radar_zoom_out", use_container_width=True):
                zi = max(0, zi - 1)
                st.session_state["radar_zoom_idx"] = zi
        with zc2:
            if st.button("➕ Zoom in", key="radar_zoom_in", use_container_width=True):
                zi = min(len(zoom_levels) - 1, zi + 1)
                st.session_state["radar_zoom_idx"] = zi
        with zc3:
            st.markdown(
                f'<div style="text-align:center;color:{TXT_MUT};font-size:0.78rem;'
                f'padding-top:8px;">Zoom: {int(1 / zoom_levels[zi])}×</div>',
                unsafe_allow_html=True,
            )

        st.plotly_chart(
            dual_radar_fig(dnames, va, vb, na, nb, radial_max=zoom_levels[zi]),
            use_container_width=True,
        )

    with tc:
        st.markdown('<div class="section-title">Dimension Breakdown</div>', unsafe_allow_html=True)
        for dk, dn in zip(dkeys, dnames):
            sa = fit_a.get(dk, {}).get("score", 0.5)
            sb = fit_b.get(dk, {}).get("score", 0.5)
            delta = round((sa - sb) * 100)
            if sa > sb + 0.05:
                w = '<span class="winner-a">A WINS</span>'
            elif sb > sa + 0.05:
                w = '<span class="winner-b">B WINS</span>'
            else:
                w = '<span class="winner-tie">TIE</span>'
            dc = "#4ade80" if delta > 0 else ("#f87171" if delta < 0 else TXT_MUT)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;'
                f'background:{BG_CARD};border:1px solid {BG_BORDER};border-radius:8px;margin-bottom:6px;">'
                f'<span style="width:70px;font-size:0.80rem;font-weight:600;color:{TXT_MUT};">{dn}</span>'
                f'<span style="width:42px;text-align:right;font-weight:700;color:#3b82f6;">{int(sa*100)}%</span>'
                f'<span style="flex:1;text-align:center;">{w}</span>'
                f'<span style="width:42px;font-weight:700;color:#f59e0b;">{int(sb*100)}%</span>'
                f'<span style="width:54px;text-align:right;font-weight:800;color:{dc};font-size:0.95rem;">'
                f'{"+" if delta > 0 else ""}{delta}pp</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Why A / When B
    comparisons = load_comparisons()
    comp = comparisons.get(f"{cid_a}_{cid_b}") or comparisons.get(f"{cid_b}_{cid_a}")
    why     = comp.get("why_a_over_b", "") if comp else \
              f"{na} ({pct_a}%) ranks ahead of {nb} ({pct_b}%) on overall weighted fit."
    salvage = comp.get("b_salvage_scenario", "") if comp else \
              f"{nb} may be preferred if role scope or priorities shift."

    wc, sc = st.columns(2)
    with wc:
        st.markdown(
            f'<div class="callout-blue" style="font-style:normal;font-size:0.92rem;">'
            f'<div style="font-weight:700;color:#60a5fa;margin-bottom:6px;font-size:0.82rem;'
            f'text-transform:uppercase;letter-spacing:0.06em;">💡 Why A over B?</div>{why}</div>',
            unsafe_allow_html=True,
        )
    with sc:
        st.markdown(
            f'<div class="callout-amber" style="font-size:0.92rem;">'
            f'<div style="font-weight:700;color:#fbbf24;margin-bottom:6px;font-size:0.82rem;'
            f'text-transform:uppercase;letter-spacing:0.06em;">⚡ When would B win?</div>{salvage}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    render_header()

    # Persistent top-level tab state.
    # st.tabs loses its active tab whenever the script reruns (st.rerun, widget
    # changes, etc.), bouncing the user back to the first tab. This JS layer
    # remembers the active top-level tab in sessionStorage and restores it on
    # every rerun. If "View Details" was just clicked, it forces Candidate Detail.
    import streamlit.components.v1 as components
    force_detail = "true" if st.session_state.pop("switch_to_detail", False) else "false"
    components.html(f"""
<script>
(function() {{
    var TOP = ['Role Intelligence', 'Shortlist', 'Candidate Detail', 'Compare'];
    var FORCE_DETAIL = {force_detail};
    var doc = window.parent.document;

    function topTabs() {{
        var all = doc.querySelectorAll('button[data-baseweb="tab"]');
        var out = [];
        for (var i = 0; i < all.length; i++) {{
            var t = all[i].innerText || "";
            for (var j = 0; j < TOP.length; j++) {{
                if (t.indexOf(TOP[j]) !== -1) {{ out.push(all[i]); break; }}
            }}
        }}
        return out;
    }}
    function labelOf(btn) {{
        var t = btn.innerText || "";
        for (var j = 0; j < TOP.length; j++) {{
            if (t.indexOf(TOP[j]) !== -1) return TOP[j];
        }}
        return null;
    }}
    function attach() {{
        var tabs = topTabs();
        for (var i = 0; i < tabs.length; i++) {{
            if (!tabs[i].dataset.hqBound) {{
                tabs[i].dataset.hqBound = '1';
                tabs[i].addEventListener('click', (function(b) {{
                    return function() {{
                        try {{ window.parent.sessionStorage.setItem('hireiq_tab', labelOf(b)); }} catch(e) {{}}
                    }};
                }})(tabs[i]));
            }}
        }}
    }}
    function restore() {{
        var want = null;
        if (FORCE_DETAIL) {{
            want = 'Candidate Detail';
            try {{ window.parent.sessionStorage.setItem('hireiq_tab', want); }} catch(e) {{}}
        }} else {{
            try {{ want = window.parent.sessionStorage.getItem('hireiq_tab'); }} catch(e) {{}}
        }}
        if (!want) return;
        var tabs = topTabs();
        for (var i = 0; i < tabs.length; i++) {{
            if ((tabs[i].innerText || "").indexOf(want) !== -1) {{
                if (tabs[i].getAttribute('aria-selected') !== 'true') {{ tabs[i].click(); }}
                return;
            }}
        }}
    }}

    var n = 0;
    var iv = setInterval(function() {{
        attach();
        restore();
        n++;
        if (n > 15) clearInterval(iv);
    }}, 100);
}})();
</script>
""", height=0)

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢  Role Intelligence",
        "📋  Shortlist",
        "👤  Candidate Detail",
        "⚖️  Compare",
    ])

    with tab1:
        render_role_intelligence()
    with tab2:
        render_shortlist()
    with tab3:
        render_candidate_detail()
    with tab4:
        render_compare()


if __name__ == "__main__":
    main()
