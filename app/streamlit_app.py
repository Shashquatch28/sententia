"""
HireIQ — Streamlit Demo UI
4-tab interface. Loads ONLY from precomputed JSON files. No computation on page load.
"""

import json
from pathlib import Path
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HireIQ — Candidate Ranking",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parents[1]
PRECOMPUTED = ROOT / "precomputed"

TIER_COLORS = {
    "STRONGLY_ADVANCE": "#1a7f4b",
    "ADVANCE": "#2563eb",
    "REVIEW_FURTHER": "#d97706",
    "ADVANCE_IF_POOL_THIN": "#7c3aed",
    "DECLINE": "#dc2626",
}

TIER_LABELS = {
    "STRONGLY_ADVANCE": "Strongly Advance",
    "ADVANCE": "Advance",
    "REVIEW_FURTHER": "Review Further",
    "ADVANCE_IF_POOL_THIN": "Advance If Pool Thin",
    "DECLINE": "Decline",
}

SEVERITY_COLORS = {
    "HIGH": "#dc2626",
    "MEDIUM": "#d97706",
    "LOW": "#16a34a",
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
.candidate-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.candidate-card:hover {
    border-color: #3b82f6;
}
.tier-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.culture-badge {
    display: inline-block;
    background: #1e3a5f;
    border: 1px solid #3b82f6;
    color: #93c5fd;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.80rem;
    margin: 3px;
}
.evidence-bullet {
    color: #94a3b8;
    font-size: 0.85rem;
    margin: 2px 0;
}
.dim-label {
    font-size: 0.80rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.winner-badge {
    display: inline-block;
    background: #14532d;
    color: #4ade80;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.70rem;
    font-weight: 700;
}
.loser-badge {
    display: inline-block;
    background: #1e293b;
    color: #64748b;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.70rem;
}
.why-box {
    background: #0f2744;
    border-left: 4px solid #3b82f6;
    padding: 14px 18px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    font-style: italic;
    color: #bfdbfe;
}
.salvage-box {
    background: #1c1917;
    border-left: 4px solid #f59e0b;
    padding: 14px 18px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    color: #fef3c7;
}
.risk-high { color: #f87171; font-weight: 700; }
.risk-medium { color: #fbbf24; font-weight: 700; }
.risk-low { color: #4ade80; font-weight: 700; }
.discriminator-item {
    background: #1e293b;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
}
.no-data-warning {
    background: #292524;
    border: 1px solid #57534e;
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    color: #d6d3d1;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_job_intelligence() -> Optional[dict]:
    path = PRECOMPUTED / "job_intelligence.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_demo_data() -> Optional[dict]:
    path = PRECOMPUTED / "demo_data.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_decision(candidate_id: str) -> Optional[dict]:
    path = PRECOMPUTED / "recruiter_decisions" / f"{candidate_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_comparison(cid_a: str, cid_b: str) -> Optional[dict]:
    path = PRECOMPUTED / "comparisons.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        comparisons = json.load(f)
    key = f"{cid_a}_{cid_b}"
    alt_key = f"{cid_b}_{cid_a}"
    return comparisons.get(key) or comparisons.get(alt_key)


@st.cache_data
def load_reasoning_map() -> dict:
    path = PRECOMPUTED / "reasoning_map.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tier_badge_html(tier: str) -> str:
    color = TIER_COLORS.get(tier, "#64748b")
    label = TIER_LABELS.get(tier, tier)
    return (
        f'<span class="tier-badge" style="background:{color}22; '
        f'border: 1px solid {color}; color:{color};">{label}</span>'
    )


def score_bar(label: str, score: float, color: str = "#3b82f6"):
    pct = int(score * 100)
    st.markdown(f'<div class="dim-label">{label} — {pct}%</div>', unsafe_allow_html=True)
    st.progress(score)


def _not_ready():
    st.markdown("""
<div class="no-data-warning">
    <h3>⚙️ Precomputed data not found</h3>
    <p>Run the intelligence pipeline first:</p>
    <pre style="background:#1c1917; padding:10px; border-radius:6px; text-align:left; display:inline-block;">
python run_agents.py</pre>
    <p style="color:#78716c; font-size:0.85rem;">Then refresh this page.</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab 1 — Role Intelligence
# ---------------------------------------------------------------------------

def render_role_intelligence():
    job = load_job_intelligence()
    if job is None:
        _not_ready()
        return

    st.subheader("Role Summary")
    st.markdown(f"*{job.get('role_summary', 'No summary available.')}*")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Discriminator Hierarchy")
        st.caption("Ranked signals used to evaluate every candidate")
        discriminators = job.get("discriminator_hierarchy", [])
        for d in discriminators:
            rank = d.get("rank", "?")
            name = d.get("name", "")
            weight = d.get("weight", 0)
            desc = d.get("description", "")
            signals = d.get("signals", [])
            pct = int(weight * 100)
            st.markdown(f"""
<div class="discriminator-item">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="font-weight:700; color:#f1f5f9;">{rank}. {name}</span>
    <span style="color:#3b82f6; font-weight:700;">{pct}%</span>
  </div>
  <div style="color:#94a3b8; font-size:0.82rem; margin-top:4px;">{desc}</div>
</div>""", unsafe_allow_html=True)

        col1b, col2b = st.columns([1, 3])
        with col2b:
            if discriminators:
                import_weights = [d.get("weight", 0) for d in discriminators]
                disc_names = [d.get("name", "") for d in discriminators]

    with col2:
        st.markdown("### Ideal Candidate Narrative")
        st.markdown(
            f"<p style='font-style:italic; color:#cbd5e1; line-height:1.7;'>"
            f"{job.get('ideal_candidate_narrative', '')}</p>",
            unsafe_allow_html=True,
        )

        st.markdown("### Culture Signals")
        culture_signals = job.get("culture_signals", [])
        badge_html = " ".join(
            f'<span class="culture-badge">{s}</span>' for s in culture_signals
        )
        st.markdown(badge_html, unsafe_allow_html=True)

        st.markdown("### Implicit Requirements")
        for req in job.get("implicit_requirements", []):
            st.markdown(f"- {req}")

        st.markdown("### Seniority Calibration")
        st.info(job.get("seniority_calibration", "Not specified"))

        if job.get("red_line_requirements"):
            st.markdown("### Red-Line Requirements")
            st.error("\n".join(f"• {r}" for r in job["red_line_requirements"]))


# ---------------------------------------------------------------------------
# Tab 2 — Shortlist
# ---------------------------------------------------------------------------

def render_shortlist():
    demo = load_demo_data()
    if demo is None:
        _not_ready()
        return

    tiers_data = demo.get("candidates_by_tier", {})
    stats = demo.get("stats", {})

    # Summary stats row
    col_sa, col_sb, col_sc, col_sd = st.columns(4)
    col_sa.metric("Total Evaluated", stats.get("total_evaluated", 0))
    col_sb.metric("Advancing", sum(
        len(tiers_data.get(t, []))
        for t in ["STRONGLY_ADVANCE", "ADVANCE"]
    ))
    col_sc.metric("Needs Review", len(tiers_data.get("REVIEW_FURTHER", [])))
    col_sd.metric("Avg Match Score", f"{stats.get('avg_match_score', 0):.1%}")

    st.divider()

    tier_order = ["STRONGLY_ADVANCE", "ADVANCE", "REVIEW_FURTHER", "ADVANCE_IF_POOL_THIN"]
    for tier in tier_order:
        candidates = tiers_data.get(tier, [])
        if not candidates:
            continue

        color = TIER_COLORS.get(tier, "#64748b")
        label = TIER_LABELS.get(tier, tier)
        st.markdown(
            f"<h3 style='color:{color};'>{label} <span style='color:#64748b; font-size:0.9rem;'>({len(candidates)})</span></h3>",
            unsafe_allow_html=True,
        )

        cols = st.columns(2)
        for i, cand in enumerate(candidates):
            col = cols[i % 2]
            with col:
                cid = cand["candidate_id"]
                name = cand.get("name", cid)
                title = cand.get("current_title", "")
                company = cand.get("current_company", "")
                match_pct = int(cand.get("overall_match_score", 0) * 100)
                evidence = cand.get("top_evidence", [])[:2]

                evidence_html = "".join(
                    f'<div class="evidence-bullet">• {e}</div>'
                    for e in evidence
                )

                st.markdown(f"""
<div class="candidate-card">
  <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:8px;">
    <div>
      <span style="font-weight:700; color:#f1f5f9; font-size:1rem;">{name}</span><br>
      <span style="color:#94a3b8; font-size:0.82rem;">{title} · {company}</span>
    </div>
    <div style="text-align:right;">
      {tier_badge_html(tier)}
      <div style="color:#3b82f6; font-weight:700; font-size:1.1rem; margin-top:4px;">{match_pct}%</div>
    </div>
  </div>
  {evidence_html}
</div>""", unsafe_allow_html=True)

                if st.button("View Details", key=f"view_{cid}_{tier}"):
                    st.session_state["selected_candidate"] = cid
                    st.session_state["active_tab_hint"] = "detail"
                    st.info(f"Switched to Candidate Detail — select '{name}' in the dropdown above.")


# ---------------------------------------------------------------------------
# Tab 3 — Candidate Detail
# ---------------------------------------------------------------------------

def render_candidate_detail():
    demo = load_demo_data()
    if demo is None:
        _not_ready()
        return

    all_candidates = demo.get("all_candidates", [])
    if not all_candidates:
        st.warning("No candidate decisions found. Run the pipeline first.")
        return

    # Build selection list
    options = {
        f"{c.get('name', c['candidate_id'])} — {c.get('current_title', '')} @ {c.get('current_company', '')}": c["candidate_id"]
        for c in all_candidates
    }
    option_keys = list(options.keys())

    # Pre-select from session state if user clicked "View Details" in Tab 2
    preselected_cid = st.session_state.get("selected_candidate")
    default_index = 0
    if preselected_cid:
        for i, (_, cid) in enumerate(options.items()):
            if cid == preselected_cid:
                default_index = i
                break

    selected_label = st.selectbox(
        "Select Candidate",
        option_keys,
        index=default_index,
    )
    selected_cid = options[selected_label]

    decision = load_decision(selected_cid)
    if decision is None:
        st.error(f"Decision file not found for {selected_cid}.")
        return

    name = decision.get("name", selected_cid)
    title = decision.get("current_title", "")
    company = decision.get("current_company", "")
    rec = decision.get("recommendation", "")
    rationale = decision.get("recommendation_rationale", "")
    match_pct = int(decision.get("overall_match_score", 0) * 100)

    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"## {name}")
        st.markdown(f"**{title}** at **{company}**")
        st.markdown(f"*{rationale}*")
    with col_h2:
        color = TIER_COLORS.get(rec, "#64748b")
        st.markdown(
            f"<div style='text-align:center; padding:16px; background:{color}22; "
            f"border:2px solid {color}; border-radius:10px;'>"
            f"<div style='font-size:2rem; font-weight:800; color:{color};'>{match_pct}%</div>"
            f"<div style='color:{color}; font-size:0.75rem; font-weight:600; text-transform:uppercase;'>{TIER_LABELS.get(rec, rec)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Trust Assessment
    st.markdown("### Trust Assessment")
    trust = decision.get("trust_assessment", {})
    trust_tier = trust.get("trust_tier", "MEDIUM")
    trust_score = trust.get("overall_trust_score", 0.5)
    trust_color = {"HIGH": "#16a34a", "MEDIUM": "#d97706", "LOW": "#dc2626"}.get(trust_tier, "#64748b")

    col_t1, col_t2 = st.columns([1, 3])
    with col_t1:
        st.markdown(
            f"<div style='text-align:center; padding:12px; background:{trust_color}22; "
            f"border:1px solid {trust_color}; border-radius:8px;'>"
            f"<div style='font-size:1.5rem; font-weight:800; color:{trust_color};'>{int(trust_score * 100)}%</div>"
            f"<div style='color:{trust_color}; font-size:0.70rem; font-weight:700;'>TRUST — {trust_tier}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_t2:
        for signal in trust.get("signals", [])[:4]:
            sig_type = signal.get("signal_type", "")
            sig_color = {
                "VERIFIED": "#4ade80", "PLAUSIBLE": "#60a5fa",
                "SUSPICIOUS": "#f87171", "UNVERIFIABLE": "#fbbf24",
            }.get(sig_type, "#94a3b8")
            st.markdown(
                f"<span style='color:{sig_color}; font-size:0.75rem; font-weight:700;'>[{sig_type}]</span> "
                f"<span style='color:#cbd5e1; font-size:0.85rem;'>{signal.get('description', '')}</span>",
                unsafe_allow_html=True,
            )

        if trust.get("red_flags"):
            for flag in trust["red_flags"]:
                st.warning(f"⚠ {flag}")

    st.divider()

    # 4 Fit Dimensions
    st.markdown("### Fit Dimensions")
    fit = decision.get("fit_assessment", {})
    dim_cols = st.columns(4)
    for col, (dim_key, dim_label) in zip(
        dim_cols,
        [("technical", "Technical"), ("product", "Product"), ("cultural", "Cultural"), ("growth", "Growth")]
    ):
        with col:
            dim_data = fit.get(dim_key, {})
            dim_score = dim_data.get("score", 0.5)
            dim_color = "#3b82f6" if dim_score >= 0.7 else ("#d97706" if dim_score >= 0.45 else "#dc2626")
            st.markdown(
                f"<div style='font-weight:700; color:{dim_color}; font-size:0.85rem; text-transform:uppercase; margin-bottom:4px;'>"
                f"{dim_label}</div>",
                unsafe_allow_html=True,
            )
            st.progress(dim_score)
            st.caption(f"{int(dim_score * 100)}%")
            for ev in dim_data.get("evidence", [])[:2]:
                st.markdown(f"<div style='color:#94a3b8; font-size:0.78rem;'>✓ {ev}</div>", unsafe_allow_html=True)
            for gap in dim_data.get("gaps", [])[:1]:
                st.markdown(f"<div style='color:#f87171; font-size:0.78rem;'>✗ {gap}</div>", unsafe_allow_html=True)

    st.divider()

    # Hiring Risks + Interview Questions (side by side)
    col_r, col_q = st.columns([1, 1])

    with col_r:
        st.markdown("### Hiring Risks")
        risks = decision.get("hiring_risks", [])
        if not risks:
            st.caption("No significant risks identified.")
        for risk in risks:
            sev = risk.get("severity", "LOW")
            sev_class = f"risk-{sev.lower()}"
            with st.expander(
                f"[{sev}] {risk.get('risk_type', 'Risk')}",
                expanded=(sev == "HIGH"),
            ):
                st.markdown(risk.get("description", ""))
                st.markdown(f"**Mitigation:** {risk.get('mitigation', '')}")
                if risk.get("is_blocking"):
                    st.error("⛔ Blocking risk")

    with col_q:
        st.markdown("### Interview Focus")
        questions = decision.get("interview_focus", [])
        if not questions:
            st.caption("No interview questions generated.")
        for q in questions:
            priority = q.get("priority", "LOW")
            dim = q.get("dimension", "")
            priority_color = {"HIGH": "#f87171", "MEDIUM": "#fbbf24", "LOW": "#4ade80"}.get(priority, "#94a3b8")
            with st.expander(
                f"[{priority}] {dim}: {q.get('question', '')[:80]}...",
                expanded=(priority == "HIGH"),
            ):
                st.markdown(f"**Q:** {q.get('question', '')}")
                wtlf = q.get("what_to_listen_for", "")
                if wtlf:
                    st.markdown(
                        f"<div style='background:#0f172a; border-left:3px solid #3b82f6; "
                        f"padding:8px 12px; border-radius:0 6px 6px 0; color:#93c5fd; font-size:0.85rem;'>"
                        f"👂 {wtlf}</div>",
                        unsafe_allow_html=True,
                    )

    # Timing
    timing = decision.get("timing_assessment")
    if timing:
        st.divider()
        st.markdown("### Timing Assessment")
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Current Tenure", f"{timing.get('current_tenure_months', 0)} mo")
        avail = timing.get("likely_available", True)
        t_col2.metric("Likely Available", "Yes" if avail else "No")
        t_col3.metric("Est. Notice", f"{timing.get('estimated_notice_weeks', 4)} wks")
        if timing.get("urgency_signal"):
            st.caption(timing["urgency_signal"])


# ---------------------------------------------------------------------------
# Tab 4 — Compare
# ---------------------------------------------------------------------------

def render_compare():
    demo = load_demo_data()
    if demo is None:
        _not_ready()
        return

    all_candidates = demo.get("all_candidates", [])
    if len(all_candidates) < 2:
        st.warning("Need at least 2 candidates to compare.")
        return

    options = {
        f"#{i + 1} — {c.get('name', c['candidate_id'])} ({c.get('current_title', '')})": c["candidate_id"]
        for i, c in enumerate(all_candidates[:50])
    }
    option_keys = list(options.keys())

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        st.markdown("**Candidate A**")
        label_a = st.selectbox("Select Candidate A", option_keys, index=0, key="cmp_a")
    with col_sel2:
        st.markdown("**Candidate B**")
        label_b = st.selectbox("Select Candidate B", option_keys, index=1, key="cmp_b")

    cid_a = options[label_a]
    cid_b = options[label_b]

    if cid_a == cid_b:
        st.warning("Select two different candidates to compare.")
        return

    decision_a = load_decision(cid_a)
    decision_b = load_decision(cid_b)

    if decision_a is None or decision_b is None:
        st.error("Decision file missing for one or both candidates. Run agents 1–4 first.")
        return

    name_a = decision_a.get("name", cid_a)
    name_b = decision_b.get("name", cid_b)

    st.divider()

    # Candidate header cards
    hdr_a, hdr_b = st.columns(2)
    with hdr_a:
        rec_a = decision_a.get("recommendation", "")
        color_a = TIER_COLORS.get(rec_a, "#64748b")
        score_a = int(decision_a.get("overall_match_score", 0) * 100)
        st.markdown(
            f"<div style='background:#1e293b; border:2px solid {color_a}; border-radius:10px; padding:16px;'>"
            f"<div style='font-size:1.1rem; font-weight:700; color:#f1f5f9;'>A: {name_a}</div>"
            f"<div style='color:#94a3b8; font-size:0.82rem;'>{decision_a.get('current_title', '')} · {decision_a.get('current_company', '')}</div>"
            f"<div style='margin-top:8px;'>{tier_badge_html(rec_a)} "
            f"<span style='color:{color_a}; font-weight:700; font-size:1.2rem; margin-left:8px;'>{score_a}%</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with hdr_b:
        rec_b = decision_b.get("recommendation", "")
        color_b = TIER_COLORS.get(rec_b, "#64748b")
        score_b = int(decision_b.get("overall_match_score", 0) * 100)
        st.markdown(
            f"<div style='background:#1e293b; border:2px solid {color_b}; border-radius:10px; padding:16px;'>"
            f"<div style='font-size:1.1rem; font-weight:700; color:#f1f5f9;'>B: {name_b}</div>"
            f"<div style='color:#94a3b8; font-size:0.82rem;'>{decision_b.get('current_title', '')} · {decision_b.get('current_company', '')}</div>"
            f"<div style='margin-top:8px;'>{tier_badge_html(rec_b)} "
            f"<span style='color:{color_b}; font-weight:700; font-size:1.2rem; margin-left:8px;'>{score_b}%</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Try precomputed comparison first, then on-demand
    comparison = load_comparison(cid_a, cid_b)
    if comparison is None:
        st.info("This pair wasn't pre-computed. Generating on-demand comparison from fit scores...")
        fit_a = decision_a.get("fit_assessment", {})
        fit_b = decision_b.get("fit_assessment", {})
        dims = ["technical", "product", "cultural", "growth"]
        comparison = {
            "dimension_comparison": {
                d.capitalize(): {
                    "winner": "A" if fit_a.get(d, {}).get("score", 0.5) > fit_b.get(d, {}).get("score", 0.5) + 0.05
                    else ("B" if fit_b.get(d, {}).get("score", 0.5) > fit_a.get(d, {}).get("score", 0.5) + 0.05 else "TIE"),
                    "a_score": fit_a.get(d, {}).get("score", 0.5),
                    "b_score": fit_b.get(d, {}).get("score", 0.5),
                    "rationale": "",
                }
                for d in dims
            },
            "why_a_over_b": f"{name_a} ({score_a}% match) ranks ahead of {name_b} ({score_b}% match) based on overall weighted fit.",
            "b_salvage_scenario": f"{name_b} may be preferred for a role with different prioritization of fit dimensions.",
        }

    # Dimension comparison table
    st.markdown("### Dimension-by-Dimension Comparison")
    dim_cmp = comparison.get("dimension_comparison", {})

    header_cols = st.columns([2, 2, 1, 2, 1])
    header_cols[0].markdown(f"**{name_a[:20]}**")
    header_cols[1].markdown("**Dimension**")
    header_cols[2].markdown("**Winner**")
    header_cols[3].markdown(f"**{name_b[:20]}**")
    header_cols[4].markdown("**Score Δ**")

    dimensions_display = [
        ("Technical", "⚙️"),
        ("Product", "📦"),
        ("Cultural", "🤝"),
        ("Growth", "📈"),
    ]

    for dim_label, icon in dimensions_display:
        d = dim_cmp.get(dim_label, {})
        sa = d.get("a_score", 0.5)
        sb = d.get("b_score", 0.5)
        winner = d.get("winner", "TIE")
        delta = round((sa - sb) * 100)

        row_cols = st.columns([2, 2, 1, 2, 1])
        # Score A
        a_bar_color = "#16a34a" if winner == "A" else "#334155"
        row_cols[0].markdown(
            f"<div style='background:{a_bar_color}33; border-radius:4px; padding:4px 8px;'>"
            f"<span style='font-weight:700; color:#f1f5f9;'>{int(sa * 100)}%</span></div>",
            unsafe_allow_html=True,
        )
        row_cols[1].markdown(f"{icon} **{dim_label}**")
        # Winner badge
        if winner == "A":
            row_cols[2].markdown(
                f"<span class='winner-badge'>A ▶</span>", unsafe_allow_html=True
            )
        elif winner == "B":
            row_cols[2].markdown(
                f"<span class='winner-badge' style='background:#14532d; color:#4ade80;'>◀ B</span>",
                unsafe_allow_html=True,
            )
        else:
            row_cols[2].caption("TIE")
        # Score B
        b_bar_color = "#16a34a" if winner == "B" else "#334155"
        row_cols[3].markdown(
            f"<div style='background:{b_bar_color}33; border-radius:4px; padding:4px 8px;'>"
            f"<span style='font-weight:700; color:#f1f5f9;'>{int(sb * 100)}%</span></div>",
            unsafe_allow_html=True,
        )
        delta_color = "#4ade80" if delta > 0 else ("#f87171" if delta < 0 else "#94a3b8")
        row_cols[4].markdown(
            f"<span style='color:{delta_color}; font-weight:700;'>{'+' if delta > 0 else ''}{delta}pp</span>",
            unsafe_allow_html=True,
        )

        if d.get("rationale"):
            st.caption(f"  ↳ {d['rationale']}")

    st.divider()

    # Why A over B
    why = comparison.get("why_a_over_b", "")
    if why:
        st.markdown("### Why A over B?")
        st.markdown(f'<div class="why-box">{why}</div>', unsafe_allow_html=True)

    # B salvage scenario
    salvage = comparison.get("b_salvage_scenario", "")
    if salvage:
        st.markdown("### When would B win?")
        st.markdown(f'<div class="salvage-box">💡 {salvage}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.markdown(
        "<h1 style='margin-bottom:4px;'>🎯 HireIQ</h1>"
        "<p style='color:#64748b; margin-top:0;'>AI-Powered Candidate Intelligence</p>",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 Role Intelligence",
        "📋 Shortlist",
        "👤 Candidate Detail",
        "⚖️ Compare",
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
