/* ============================================================
   HireIQ frontend — binds the design to real precomputed data.
   Render-ready full stack: reads precomputed data and calls same-origin API routes.
   ============================================================ */

const DATA_PATHS = [
  "../precomputed/demo_data.json",
  "/precomputed/demo_data.json",
  "precomputed/demo_data.json",
];

const TIER_META = {
  STRONGLY_ADVANCE: { name:"Strongly advance", sub:"Talk to these this week.", cls:"STRONGLY_ADVANCE", dot:"var(--success)", pill:"t1" },
  ADVANCE:          { name:"Advance after screen", sub:"Screen first, then decide. Worth the call.", cls:"ADVANCE", dot:"var(--accent)", pill:"t2" },
  REVIEW_FURTHER:   { name:"Review if pool thin", sub:"Borderline fits. Open only if upper tiers are exhausted.", cls:"REVIEW", dot:"var(--ink-400)", pill:"t3" },
  ADVANCE_IF_POOL_THIN:{ name:"Reserve pool", sub:"Kept for completeness, not priority.", cls:"REVIEW", dot:"var(--ink-400)", pill:"t3" },
  DECLINE:          { name:"Set aside", sub:"Below the bar for this role.", cls:"REVIEW", dot:"var(--ink-400)", pill:"t3" },
};
const TIER_ORDER = ["STRONGLY_ADVANCE","ADVANCE","REVIEW_FURTHER","ADVANCE_IF_POOL_THIN","DECLINE"];

const State = {
  data:null, byId:{}, ranked:[], lens:"shortlist",
  expanded:{}, currentCandidate:null, copilotThread:[],
  simWeights:null, explorerFilter:"ALL", explorerSort:"score",
  decisions:{},   // candidate_id → "advanced" | "setaside"
  token: localStorage.getItem("hiq_token") || null,
  notifications:[
    {title:"Run v3 complete — 100 candidates ranked", meta:"Today · Rec. Systems Engineer", color:"var(--success)", read:false},
    {title:"7 in Strongly Advance — ready for outreach", meta:"Today · Talk to these this week", color:"var(--accent)", read:false},
    {title:"47 honeypot signals flagged and excluded", meta:"Today · Trust & integrity filter", color:"var(--warning)", read:false},
  ],
};

/* ── notifications ── */
function pushNotification(title, color="var(--accent)", meta=null){
  const now = new Date();
  const hh = now.getHours().toString().padStart(2,"0");
  const mm = now.getMinutes().toString().padStart(2,"0");
  State.notifications.unshift({
    title, color, read:false,
    meta: meta || `Just now · ${hh}:${mm}`,
  });
  renderNotifPanel();
  updateBellDot();
}
function renderNotifPanel(){
  const list = $("#notif-list");
  if(!list) return;
  const unread = State.notifications.filter(n=>!n.read).length;
  const head = $("#notif-count");
  if(head) head.textContent = unread ? `${unread} new` : "all read";
  list.innerHTML = State.notifications.map(n=>`
    <div class="notif-item${n.read?" notif-read":""}">
      <span class="notif-dot" style="background:${n.color}"></span>
      <div class="notif-body">
        <div class="notif-title">${esc(n.title)}</div>
        <div class="notif-meta">${esc(n.meta)}</div>
      </div>
    </div>`).join("");
}
function updateBellDot(){
  const dot = $(".bell-dot");
  if(!dot) return;
  const unread = State.notifications.filter(n=>!n.read).length;
  dot.style.display = unread ? "block" : "none";
}
function markNotificationsRead(){
  State.notifications.forEach(n=>n.read=true);
  updateBellDot();
  renderNotifPanel();
}

function authHeaders(){
  return State.token ? {"Authorization": `Bearer ${State.token}`} : {};
}

async function persistDecision(cid, status){
  try{
    await fetch(`${API_BASE}/api/decisions`,{
      method:"POST",
      headers:{"Content-Type":"application/json",...authHeaders()},
      body:JSON.stringify({candidate_id:cid, status}),
    });
  }catch(_){}
}

async function removeDecision(cid){
  try{
    await fetch(`${API_BASE}/api/decisions/${encodeURIComponent(cid)}`,{
      method:"DELETE",
      headers:authHeaders(),
    });
  }catch(_){}
}

/* API server: same-origin by default, override with window.HIREIQ_API_BASE if split-hosting. */
const API_BASE = (window.HIREIQ_API_BASE || "").replace(/\/$/, "");

/* ── utilities ── */
const $ = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));
const esc = s => String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtScore = n => (n==null?"—":Number(n).toFixed(3));
const pct = n => Math.round((Number(n)||0)*100);

function noticeDays(c){ const w=c?.timing_assessment?.estimated_notice_weeks; return (w==null)?null:Math.round(w*7); }
function noticeLabel(c){ const d=noticeDays(c); if(d==null) return ""; return d<=7?"Immediate":`${d}d notice`; }
function noticeColor(c){ const d=noticeDays(c); return (d!=null && d>30)?"var(--warning)":"var(--ink-400)"; }
function metaLine(c){ return [c.current_title, c.current_company].filter(Boolean).join(" · "); }

/* availability score derived from notice period (shorter = higher) */
function availabilityScore(c){
  const d=noticeDays(c); if(d==null) return 0.6;
  if(d<=7)return 1.0; if(d<=30)return 0.85; if(d<=45)return 0.65; if(d<=60)return 0.5; if(d<=90)return 0.35; return 0.2;
}
function dims(c){
  const f=c.fit_assessment||{};
  return {
    technical:f.technical?.score??0, product:f.product?.score??0,
    cultural:f.cultural?.score??0, growth:f.growth?.score??0,
    trust:c.trust_assessment?.overall_trust_score??0, availability:availabilityScore(c),
  };
}

/* ============================================================ */
/*  BOOTSTRAP                                                   */
/* ============================================================ */
async function boot(){
  let data=null, err=null;
  for(const p of DATA_PATHS){
    try{ const r=await fetch(p); if(r.ok){ data=await r.json(); break; } }
    catch(e){ err=e; }
  }
  if(!data){
    $("#lens-root").innerHTML =
      `<div class="loading-screen"><p style="max-width:420px;text-align:center">Couldn't load <code>precomputed/demo_data.json</code>.<br><br>
      Check that the deployment includes <code style="font-family:var(--font-mono);font-size:12px">precomputed/demo_data.json</code>.</p></div>`;
    return;
  }
  State.data = data;
  // rank all candidates by match score desc
  State.ranked = [...(data.all_candidates||[])]
    .sort((a,b)=>(b.overall_match_score||0)-(a.overall_match_score||0));
  State.ranked.forEach((c,i)=>{ c._rank=i+1; State.byId[c.candidate_id]=c; });
  State.simWeights = defaultWeights();
  // baseline simulator order (under default weights) so deltas read against "Default"
  simulate(defaultWeights()).forEach(r=>{ r.c._simBase=r.now; });

  // Restore persisted pipeline decisions from API (silent if server not running)
  try{
    const dr=await fetch(`${API_BASE}/api/decisions`,{headers:authHeaders()});
    if(dr.ok){
      const dd=await dr.json();
      (dd.decisions||[]).forEach(d=>{ State.decisions[d.candidate_id]=d.status; });
    }
  }catch(_){}

  wireChrome();
  setLens("shortlist");
}

/* ============================================================ */
/*  CHROME (nav, topbar, cmdk)                                  */
/* ============================================================ */
function wireChrome(){
  $$(".nav-btn").forEach(b=>b.addEventListener("click",()=>setLens(b.dataset.lens)));
  $$("[data-lens]").forEach(b=>{ if(!b.classList.contains("nav-btn")) b.addEventListener("click",()=>setLens(b.dataset.lens)); });
  $("#open-cmdk").addEventListener("click",openCmdk);
  $("#rail-scrim").addEventListener("click",closeRail);
  document.addEventListener("keydown",e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); openCmdk(); }
    if(e.key==="Escape"){ closeCmdk(); closeRail(); closeNotifPanel(); closeAvatarMenu(); }
  });
  $("#cmdk-input").addEventListener("input",renderCmdk);
  $("#cmdk").addEventListener("click",closeCmdk);
  $(".cmdk").addEventListener("click",e=>e.stopPropagation());

  // Bell notification panel — positioned via JS so it never clips off-screen
  renderNotifPanel();
  updateBellDot();
  $("#bell-btn").addEventListener("click", e=>{
    e.stopPropagation();
    const panel = $("#notif-panel");
    const isHidden = panel.hidden;
    closeAvatarMenu();
    if(isHidden){
      const r = e.currentTarget.getBoundingClientRect();
      const panelW = 300;
      let left = r.right - panelW;                          // right-align with button
      if(left < 8) left = 8;                               // never clip left edge
      if(left + panelW > window.innerWidth - 8) left = window.innerWidth - panelW - 8;
      panel.style.top  = (r.bottom + 8) + "px";
      panel.style.left = left + "px";
      panel.style.right = "auto";
      markNotificationsRead();                              // opening = seen
    }
    panel.hidden = !isHidden;
    if(!panel.hidden) setTimeout(()=>document.addEventListener("click",_closeNotifOnOutside),0);
  });

  // Avatar / user menu
  const name = localStorage.getItem("hiq_name") || "Recruiter";
  const email = localStorage.getItem("hiq_email") || "demo@hireiq.com";
  const initial = name.charAt(0).toUpperCase();
  const av = $("#sb-avatar");
  if(av) av.textContent = initial;
  const nameEl = $("#avatar-name"); if(nameEl) nameEl.textContent = name;
  const emailEl = $("#avatar-email"); if(emailEl) emailEl.textContent = email;

  $("#sb-avatar").addEventListener("click", e=>{
    e.stopPropagation();
    const menu = $("#avatar-menu");
    const isHidden = menu.hidden;
    closeNotifPanel();
    if(isHidden){
      const r = e.currentTarget.getBoundingClientRect();
      menu.style.bottom = (window.innerHeight - r.top + 8) + "px";
      menu.style.left   = (r.right + 8) + "px";
    }
    menu.hidden = !isHidden;
    if(!menu.hidden) setTimeout(()=>document.addEventListener("click",_closeAvatarOnOutside),0);
  });
}

function closeNotifPanel(){
  const p=$("#notif-panel"); if(p) p.hidden=true;
  document.removeEventListener("click",_closeNotifOnOutside);
}
function _closeNotifOnOutside(e){
  if(!$("#bell-btn")?.contains(e.target)) closeNotifPanel();
}
function closeAvatarMenu(){
  const m=$("#avatar-menu"); if(m) m.hidden=true;
  document.removeEventListener("click",_closeAvatarOnOutside);
}
function _closeAvatarOnOutside(e){
  if(!$("#sb-avatar")?.contains(e.target)) closeAvatarMenu();
}
function signOut(){
  localStorage.removeItem("hiq_token");
  localStorage.removeItem("hiq_name");
  localStorage.removeItem("hiq_email");
  window.location.href="signin.html";
}

function setLens(lens){
  State.lens=lens;
  $$(".nav-btn").forEach(b=>b.classList.toggle("active",b.dataset.lens===lens));
  const root=$("#lens-root");
  if(lens==="shortlist") root.innerHTML=renderShortlist();
  else if(lens==="role") root.innerHTML=renderRole();
  else if(lens==="explorer") root.innerHTML=renderExplorer();
  else if(lens==="guide") root.innerHTML=renderGuide();
  else if(lens==="copilot") root.innerHTML=renderCopilot();
  else if(lens==="simulator") root.innerHTML=renderSimulator();
  else if(lens==="pipeline") root.innerHTML=renderPipeline();
  else if(lens==="compare") root.innerHTML=root.innerHTML; // handled by openCompare
  wireLens(lens);
}

/* ============================================================ */
/*  SHORTLIST                                                   */
/* ============================================================ */
function renderShortlist(){
  const tiers = State.data.candidates_by_tier||{};
  const stats = State.data.stats||{};
  const byTier = stats.by_tier||{};
  const ranked = byTier.STRONGLY_ADVANCE||0, adv=byTier.ADVANCE||0,
        rev=(byTier.REVIEW_FURTHER||0)+(byTier.ADVANCE_IF_POOL_THIN||0)+(byTier.DECLINE||0);

  let funnel = `<div class="funnel">
    <span class="big">100,000</span>
    ${arrow()}<span class="step">47 honeypots excluded</span>
    ${arrow()}<span class="step">${stats.total_evaluated||State.ranked.length} ranked</span>
    ${arrow()}<div style="display:flex;align-items:center;gap:7px;">
      <span class="tier-pill t1">${ranked}</span><span style="color:var(--hair)">·</span>
      <span class="tier-pill t2">${adv}</span><span style="color:var(--hair)">·</span>
      <span class="tier-pill t3">${rev}</span></div>
    <div class="fresh"><span class="dot dot-success"></span><span class="fresh-label">Fresh · run v3</span></div>
  </div>`;

  const top3 = State.ranked.slice(0,3);
  const advancedCount = Object.values(State.decisions).filter(v=>v==="advanced").length;
  const setasideCount = Object.values(State.decisions).filter(v=>v==="setaside").length;
  const avgScore = State.ranked.length
    ? (State.ranked.reduce((s,c)=>s+(c.overall_match_score||0),0)/State.ranked.length).toFixed(3)
    : "—";

  const sidePanel = `<div class="sl-side">
    <div class="sl-side-card">
      <div class="sl-side-label">Pipeline status</div>
      <div class="sl-stat-row"><span class="sl-stat-num" style="color:var(--success)">${advancedCount}</span><span class="sl-stat-text">Advanced</span><button class="sl-side-link" onclick="setLens('pipeline')">View →</button></div>
      <div class="sl-stat-row"><span class="sl-stat-num" style="color:var(--ink-400)">${setasideCount}</span><span class="sl-stat-text">Set aside</span></div>
    </div>
    <div class="sl-side-card">
      <div class="sl-side-label">Run summary</div>
      <div class="sl-kv"><span>Total scored</span><span class="mono">${State.ranked.length}</span></div>
      <div class="sl-kv"><span>Avg score</span><span class="mono">${avgScore}</span></div>
      <div class="sl-kv"><span>Honeypots caught</span><span class="mono" style="color:var(--warning)">47</span></div>
      <div class="sl-kv"><span>Run</span><span class="mono">v3 · fresh</span></div>
    </div>
    <div class="sl-side-card">
      <div class="sl-side-label">Top 3 candidates</div>
      ${top3.map(c=>`<div class="sl-top-row" onclick="openRail('${esc(c.candidate_id)}')">
        <span class="sl-top-rank mono">#${c._rank}</span>
        <span class="sl-top-name">${esc(c.name)}</span>
        <span class="sl-top-score mono">${fmtScore(c.overall_match_score)}</span>
      </div>`).join("")}
    </div>
  </div>`;

  let body = `<div class="lens-pad"><div class="sl-two-col"><div class="sl-main">`;
  TIER_ORDER.forEach(tk=>{
    const list = tiers[tk]; if(!list||!list.length) return;
    const meta = TIER_META[tk];
    // resolve full candidate records (ranked) preserving tier order by score
    const cands = list.map(x=> State.byId[x.candidate_id] || x)
                      .sort((a,b)=>(b.overall_match_score||0)-(a.overall_match_score||0));
    if(tk==="STRONGLY_ADVANCE"){
      const showAll = State.expanded[tk];
      const shown = showAll?cands:cands.slice(0,4);
      body += `<div class="tier" data-tier="${tk}">
        <div class="tier-head"><div class="tier-head-l">
          <span class="dot" style="width:9px;height:9px;background:${meta.dot}"></span>
          <span class="tier-name">${esc(meta.name)}</span>
          <span class="tier-count">${cands.length}</span>
          <span class="tier-sub">${esc(meta.sub)}</span>
        </div>
        <button class="tier-action">Advance all ${cands.length} to pipeline
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"></path></svg>
        </button></div>
        <div class="tier-cards">
          ${shown.map(c=>card(c,meta)).join("")}
          ${cands.length>4?`<button class="show-more" data-expand="${tk}">${showAll?"Show fewer ↑":`Show ${cands.length-4} more in ${meta.name} ↓`}</button>`:""}
        </div></div>`;
    } else {
      const open = State.expanded[tk];
      body += `<div class="tier" data-tier="${tk}">`;
      body += `<div class="tier-collapsed" data-expand="${tk}">
        <div class="tier-head-l">
          <span class="dot" style="width:8px;height:8px;background:${meta.dot}"></span>
          <span class="tier-name" style="color:${meta.dot}">${esc(meta.name)}</span>
          <span class="tier-count" style="background:var(--canvas)">${cands.length}</span>
          <span class="tier-sub">${esc(meta.sub)}</span>
        </div>
        <span class="mono" style="font-size:11px;color:var(--ink-400)">${open?"Hide ▾":`Show ${cands.length} ▸`}</span>
      </div>`;
      if(open) body += `<div class="tier-cards" style="margin-top:10px">${cands.map(c=>card(c,meta)).join("")}</div>`;
      body += `</div>`;
    }
  });
  body += `</div>${sidePanel}</div></div>`;
  return funnel + body;
}

function card(c,meta){
  const ev=(c.top_evidence||[]).slice(0,2);
  const risk=(c.hiring_risks||[])[0];
  return `<div class="hiq-card" data-open="${esc(c.candidate_id)}" ${meta.pill==="t1"?'style="box-shadow:inset 3px 0 0 0 var(--success),var(--e1)"':""}>
    <div class="card-rank">#${c._rank}</div>
    <div class="card-tierdot" style="background:${meta.dot}"></div>
    <div class="card-body">
      <div class="card-name-row"><span class="card-name">${esc(c.name||c.candidate_id)}</span>
        <span class="card-meta">${esc(metaLine(c))}</span></div>
      <div class="card-ev">${ev.map(e=>`<div class="card-ev-row"><span class="arr">→</span><span>${esc(e)}</span></div>`).join("")}</div>
      ${risk?`<div class="card-risk"><span class="dot dot-warning"></span>${esc(risk.description||risk.risk_type||"")}</div>`:""}
    </div>
    <div class="card-right">
      <div class="card-score tabular">${fmtScore(c.overall_match_score)}</div>
      ${noticeLabel(c)?`<div class="card-notice" style="color:${noticeColor(c)}">${esc(noticeLabel(c))}</div>`:""}
      <button class="card-open-btn">Open <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"></path></svg></button>
    </div>
  </div>`;
}
const arrow=()=>`<svg class="arrow" width="16" height="10" viewBox="0 0 16 10"><path d="M0 5h13M9 1l4 4-4 4" stroke-width="1.5" fill="none" stroke-linecap="round"></path></svg>`;

/* ============================================================ */
/*  CANDIDATE RAIL                                              */
/* ============================================================ */
function openRail(cid){
  const c=State.byId[cid]; if(!c) return;
  State.currentCandidate=cid;
  const d=dims(c);
  const tier=TIER_META[c.recommendation]||TIER_META.REVIEW_FURTHER;
  const recColor = c.recommendation==="STRONGLY_ADVANCE"?"var(--success)":
                   c.recommendation==="ADVANCE"?"var(--accent)":"var(--ink-400)";
  const trust=c.trust_assessment||{};
  const sigCount=(trust.signals||[]).length;
  const neighbor = State.ranked[c._rank]; // rank is 1-based; next one
  const dimRows=[
    ["Technical fit",d.technical],["Product fit",d.product],["Cultural fit",d.cultural],
    ["Growth",d.growth],["Availability",d.availability],["Trust score",d.trust],
  ];
  const ev=c.top_evidence||[];
  const risks=c.hiring_risks||[];
  const ivs=c.interview_focus||[];

  const html=`
  <div class="rail-head">
    <div class="rail-head-top">
      <div><div class="rail-name">${esc(c.name||c.candidate_id)}</div>
        <div class="rail-sub">${esc(metaLine(c))}${noticeLabel(c)?" · "+esc(noticeLabel(c)):""}</div></div>
      <button class="rail-close" id="rail-close">×</button>
    </div>
    <div class="rail-actions">
      <button class="btn btn-success" id="rail-advance">Advance to pipeline</button>
      <button class="btn" id="rail-setaside">Set aside</button>
      <button class="btn" id="rail-guide">Interview guide ↗</button>
      ${neighbor?`<button class="btn" data-compare="${esc(cid)}|${esc(neighbor.candidate_id)}">Compare ↔ #${neighbor._rank}</button>`:""}
    </div>
  </div>
  <div class="rail-body">
    <div class="rail-rec">
      <span class="rec-badge" style="background:color-mix(in srgb,${recColor} 13%,#fff);color:${recColor}">
        <span class="dot" style="background:${recColor}"></span>${esc((c.recommendation||"").replace(/_/g," "))}</span>
      <span style="font-size:12px;color:var(--ink-400)" class="mono">${esc(trust.trust_tier||"")} · ${sigCount} signals</span>
      <span class="rail-bigscore tabular">${fmtScore(c.overall_match_score)}</span>
    </div>
    ${c.recommendation_rationale?`<div class="rail-rationale">${esc(c.recommendation_rationale)}</div>`:""}
    <div id="rail-ai-output"></div>

    <div class="section-label">Dimension breakdown</div>
    ${dimRows.map(([n,v])=>`<div class="dim-row"><span class="dim-name">${n}</span>
      <span class="dim-track"><span class="dim-fill" style="width:${pct(v)}%"></span></span>
      <span class="dim-val tabular">${(Number(v)||0).toFixed(2)}</span></div>`).join("")}

    ${ev.length?`<div class="section-label">Strongest evidence</div>
      ${ev.map(e=>`<div class="ev-row"><span class="arr">→</span><span>${esc(e)}</span></div>`).join("")}`:""}

    ${risks.length?`<div class="section-label">Hiring risks</div>
      ${risks.map(r=>`<div class="risk-row">
        <div class="risk-top"><span class="sev sev-${esc(r.severity||"LOW")}">${esc(r.severity||"LOW")}</span>${esc(r.description||r.risk_type||"")}</div>
        ${r.mitigation?`<div class="risk-mit">Mitigation · ${esc(r.mitigation)}</div>`:""}
      </div>`).join("")}`:""}

    ${ivs.length?`<div class="section-label">Interview focus</div>
      ${ivs.map(q=>`<div class="iv-row">
        <div class="iv-q">${esc(q.question)}</div>
        <div class="iv-tags"><span class="tag pri-${esc(q.priority||"")}">${esc(q.priority||"")}</span><span class="tag">${esc(q.dimension||"")}</span></div>
        ${q.what_to_listen_for?`<div class="iv-listen">Listen for · ${esc(q.what_to_listen_for)}</div>`:""}
      </div>`).join("")}`:""}

    ${c.timing_assessment?.urgency_signal?`<div class="section-label">Timing</div>
      <div class="rail-rationale" style="font-size:13.5px">${esc(c.timing_assessment.urgency_signal)}</div>`:""}
  </div>`;

  const rail=$("#rail");
  rail.innerHTML=html; rail.hidden=false; $("#rail-scrim").hidden=false;
  const railActions = rail.querySelector(".rail-actions");
  if(railActions){
    railActions.insertAdjacentHTML("beforeend", `
      <button class="btn" id="rail-outreach">Draft outreach</button>
      <button class="btn" id="rail-ai-sim">AI what-if</button>
    `);
  }
  $("#rail-close").addEventListener("click",closeRail);
  $$("[data-compare]",rail).forEach(b=>b.addEventListener("click",()=>{
    const [a,bb]=b.dataset.compare.split("|"); openCompare(a,bb);
  }));
  $("#rail-guide")?.addEventListener("click",()=>{ closeRail(); setLens("guide"); });
  $("#rail-outreach")?.addEventListener("click",()=>draftOutreach(cid));
  $("#rail-ai-sim")?.addEventListener("click",()=>runAiSimulation(cid));
  $("#rail-advance")?.addEventListener("click",()=>{
    const cid=State.currentCandidate; if(!cid) return;
    const c=State.byId[cid]; if(!c) return;
    State.decisions[cid]="advanced";
    persistDecision(cid,"advanced");
    pushNotification(`${c.name} advanced to pipeline`, "var(--success)");
    closeRail();
    showToast(`✓ ${c.name} advanced to pipeline`, "success", ()=>{
      delete State.decisions[cid];
      removeDecision(cid);
      pushNotification(`${c.name} removed from pipeline`, "var(--ink-400)");
      showToast(`Undone — ${c.name} removed from pipeline`, "neutral");
    });
  });
  $("#rail-setaside")?.addEventListener("click",()=>{
    const cid=State.currentCandidate; if(!cid) return;
    const c=State.byId[cid]; if(!c) return;
    State.decisions[cid]="setaside";
    persistDecision(cid,"setaside");
    pushNotification(`${c.name} set aside`, "var(--warning)");
    closeRail();
    showToast(`${c.name} set aside`, "neutral", ()=>{
      delete State.decisions[cid];
      removeDecision(cid);
      pushNotification(`${c.name} restored`, "var(--accent)");
      showToast(`Undone — ${c.name} restored`, "success");
    });
  });
}
function closeRail(){ $("#rail").hidden=true; $("#rail-scrim").hidden=true; }

function setRailAiOutput(title, body, loading=false){
  const out=$("#rail-ai-output");
  if(!out) return;
  out.innerHTML = `<div class="rail-rationale" style="font-size:13.5px;margin-top:12px">
    <div class="section-label" style="margin-top:0">${esc(title)}</div>
    ${loading?`<span class="hiq-dots"><span></span><span></span><span></span></span> `:""}${body}
  </div>`;
}

async function draftOutreach(cid){
  const c=State.byId[cid]; if(!c) return;
  setRailAiOutput("Outreach draft", "Drafting outreach...", true);
  try{
    const res=await fetch(`${API_BASE}/api/outreach/${encodeURIComponent(cid)}`,{
      method:"POST",
      headers:authHeaders(),
    });
    const data=await res.json();
    if(!res.ok) throw new Error(data.error||`API ${res.status}`);
    setRailAiOutput("Outreach draft", llmHtml(data.email||"No outreach returned."));
  }catch(e){
    setRailAiOutput("Outreach draft", `<p>${esc(e.message||"Outreach unavailable.")}</p>`);
  }
}

async function runAiSimulation(cid){
  const c=State.byId[cid]; if(!c) return;
  const scenario = `The recruiter prioritizes immediate availability and production LLM/RAG experience for ${c.name}. Would the recommendation change?`;
  setRailAiOutput("AI what-if", "Running scenario...", true);
  try{
    const res=await fetch(`${API_BASE}/api/simulate`,{
      method:"POST",
      headers:{"Content-Type":"application/json",...authHeaders()},
      body:JSON.stringify({candidate_id:cid, scenario}),
    });
    const data=await res.json();
    if(!res.ok) throw new Error(data.error||`API ${res.status}`);
    setRailAiOutput("AI what-if", llmHtml(data.result||"No simulation returned."));
  }catch(e){
    setRailAiOutput("AI what-if", `<p>${esc(e.message||"Simulation unavailable.")}</p>`);
  }
}

/* ============================================================ */
/*  ROLE INTELLIGENCE                                           */
/* ============================================================ */
function renderRole(){
  const j=State.data.job_intelligence||{};
  const disc=(j.discriminator_hierarchy||[]).slice().sort((a,b)=>(b.weight||0)-(a.weight||0));
  const maxW=Math.max(...disc.map(d=>d.weight||0),0.01);
  const reds=j.red_line_requirements||[];
  const culture=j.culture_signals||[];
  const topDisc = disc.slice(0,3);
  return `<div class="lens-pad"><div class="ri-two-col">
    <div class="ri-main">
      <div class="ri-head">
        <div class="ri-title">Role Intelligence</div>
        <div class="ri-meta">RECOMMENDATION SYSTEMS ENGINEER · ${esc((j.jd_source||"job description").split(/[\\/]/).pop())}</div>
      </div>

      <div class="ri-section">
        <div class="section-label">AI narrative · what HireIQ understood</div>
        <p class="ri-narr">${esc(j.ideal_candidate_narrative||j.role_summary||"")}</p>
      </div>

      <div class="ri-section">
        <div class="ri-h">Discriminator hierarchy</div>
        <div class="ri-hsub">What separates strong candidates from weak ones, for this role.</div>
        ${disc.map(d=>`<div class="disc-row">
          <span class="disc-name">${esc(d.name)}</span>
          <span class="disc-track"><span class="disc-fill" style="width:${Math.round((d.weight||0)/maxW*100)}%"></span></span>
          <span class="disc-w tabular">${(d.weight||0).toFixed(2)}</span></div>`).join("")}
      </div>

      ${reds.length?`<div class="ri-section">
        <div class="ri-h">Red-line requirements · hard rules</div>
        <div class="ri-hsub">Non-negotiables. Missing any of these caps the score.</div>
        <div class="chip-wrap">${reds.map(r=>`<span class="chip req">${esc(r)}</span>`).join("")}</div>
      </div>`:""}

      ${j.seniority_calibration?`<div class="ri-section">
        <div class="ri-h">Seniority calibration</div>
        <p style="font-size:14px;line-height:1.6;color:var(--ink-600)">${esc(j.seniority_calibration)}</p>
      </div>`:""}
    </div>

    <div class="ri-side">
      ${culture.length?`<div class="sl-side-card">
        <div class="sl-side-label">Culture signals</div>
        <div class="chip-wrap" style="margin:0">${culture.map(s=>`<span class="chip">${esc(s)}</span>`).join("")}</div>
      </div>`:""}
      <div class="sl-side-card">
        <div class="sl-side-label">Top discriminators</div>
        ${topDisc.map(d=>`<div class="sl-kv">
          <span>${esc(d.name)}</span>
          <span class="mono" style="color:var(--accent)">${(d.weight||0).toFixed(2)}</span>
        </div>`).join("")}
      </div>
      <div class="sl-side-card">
        <div class="sl-side-label">Role snapshot</div>
        <div class="sl-kv"><span>Red-line rules</span><span class="mono">${reds.length}</span></div>
        <div class="sl-kv"><span>Discriminators</span><span class="mono">${disc.length}</span></div>
        <div class="sl-kv"><span>Culture signals</span><span class="mono">${culture.length}</span></div>
      </div>
    </div>
  </div></div>`;
}

/* ============================================================ */
/*  COMPARISON                                                  */
/* ============================================================ */
function openCompare(aId,bId){
  const a=State.byId[aId], b=State.byId[bId];
  if(!a||!b) return;
  setLens("compare");
  // find precomputed comparison
  const comps=State.data.comparisons||{};
  let comp = comps[`${aId}_${bId}`], flip=false;
  if(!comp && comps[`${bId}_${aId}`]){ comp=comps[`${bId}_${aId}`]; flip=true; }
  const da=dims(a), db=dims(b);
  const dimList=[
    ["Technical fit",da.technical,db.technical],
    ["Product fit",da.product,db.product],
    ["Cultural fit",da.cultural,db.cultural],
    ["Growth",da.growth,db.growth],
    ["Availability",da.availability,db.availability],
    ["Trust score",da.trust,db.trust],
  ];
  const evA=(a.top_evidence||[]).slice(0,3), evB=(b.top_evidence||[]).slice(0,3);
  const why = comp?.why_a_over_b ? (flip? `${esc(b.name)} is favoured: ${esc(comp.why_a_over_b)}` : esc(comp.why_a_over_b))
            : `${esc(a.name)} ranks above ${esc(b.name)} on overall match (${fmtScore(a.overall_match_score)} vs ${fmtScore(b.overall_match_score)}), led by the dimensions marked below.`;
  const salvage = comp?.b_salvage_scenario || `Choose ${esc(b.name)} if availability or a specific skill depth outweighs the overall gap.`;

  const decisiveDims = dimList.filter(([n,va,vb])=>Math.abs(va-vb)>=0.12);
  const aWins = dimList.filter(([n,va,vb])=>va>vb+0.02).length;
  const bWins = dimList.filter(([n,va,vb])=>vb>va+0.02).length;
  const scoreDelta = (a.overall_match_score - b.overall_match_score);

  const side = `<div class="ri-side">
    <div class="sl-side-card">
      <div class="sl-side-label">Head to head</div>
      <div class="sl-kv"><span>Score delta</span><span class="mono" style="color:var(--accent)">+${scoreDelta.toFixed(3)}</span></div>
      <div class="sl-kv"><span>${esc(a.name.split(" ")[0])} wins on</span><span class="mono">${aWins} dims</span></div>
      <div class="sl-kv"><span>${esc(b.name.split(" ")[0])} wins on</span><span class="mono">${bWins} dims</span></div>
      <div class="sl-kv"><span>Decisive dims</span><span class="mono" style="color:var(--warning)">${decisiveDims.length}</span></div>
    </div>
    ${decisiveDims.length ? `<div class="sl-side-card">
      <div class="sl-side-label">Decisive dimensions</div>
      ${decisiveDims.map(([n,va,vb])=>`<div class="sl-kv"><span>${esc(n)}</span><span class="mono" style="color:${va>vb?"var(--accent)":"var(--ink-600)"}">${va.toFixed(2)} vs ${vb.toFixed(2)}</span></div>`).join("")}
    </div>` : ""}
    <div class="sl-side-card">
      <div class="sl-side-label">Quick actions</div>
      <button class="sl-side-link" style="margin-bottom:8px" onclick="openRail('${esc(aId)}')">Open ${esc(a.name.split(" ")[0])} →</button><br>
      <button class="sl-side-link" onclick="openRail('${esc(bId)}')">Open ${esc(b.name.split(" ")[0])} →</button>
    </div>
  </div>`;

  $("#lens-root").innerHTML=`<div class="lens-pad"><div class="ri-two-col">
    <div class="ri-main">
      <div class="cmp-head">
        <div><div class="cmp-title">#${a._rank} ${esc(a.name)} vs #${b._rank} ${esc(b.name)}</div>
          <div class="cmp-sub">Why this order — and when you'd choose differently.</div></div>
        <button class="btn" id="cmp-back">← Back to shortlist</button>
      </div>
      <div class="cmp-cards">
        ${cmpCard(a,evA,true)}
        ${cmpCard(b,evB,false)}
      </div>
      <div class="dim-cmp">
        ${dimList.map(([n,va,vb])=>{
          const aw=va>vb+0.02, bw=vb>va+0.02, decisive=Math.abs(va-vb)>=0.12;
          return `<div class="dim-cmp-row">
            <div class="dcell a ${aw?'winr':''}">${(va).toFixed(2)} ${aw?'◀':''}</div>
            <div class="dmid">${esc(n)}${decisive?`<span class="decisive">decisive</span>`:""}</div>
            <div class="dcell b ${bw?'winr':''}">${bw?'▶':''} ${(vb).toFixed(2)}</div>
          </div>`;}).join("")}
      </div>
      <div class="cmp-why"><h3>Why #${a._rank} over #${b._rank}</h3><p>${why}</p></div>
      <div class="cmp-salvage"><h3>Choose ${esc(b.name)} if…</h3><p>${salvage}</p></div>
    </div>
    ${side}
  </div></div>`;
  $("#cmp-back").addEventListener("click",()=>setLens("shortlist"));
}
function cmpCard(c,ev,win){
  return `<div class="cmp-card ${win?'win':''}">
    <div class="cmp-rank">#${c._rank}${win?' · ranked higher':''}</div>
    <div class="cmp-name">${esc(c.name)}</div>
    <div class="cmp-meta">${esc(metaLine(c))}${noticeLabel(c)?" · "+esc(noticeLabel(c)):""}</div>
    <div class="cmp-score tabular">${fmtScore(c.overall_match_score)}</div>
    ${ev.map(e=>`<div class="cmp-ev"><span class="arr">→</span><span>${esc(e)}</span></div>`).join("")}
  </div>`;
}

/* ============================================================ */
/*  CANDIDATE EXPLORER  (S07)                                   */
/* ============================================================ */
function renderExplorer(){
  const flt=State.explorerFilter||"ALL", srt=State.explorerSort||"score";
  const sa=State.ranked.filter(c=>c.recommendation==="STRONGLY_ADVANCE").length;
  const adv=State.ranked.filter(c=>c.recommendation==="ADVANCE").length;
  const rev=State.ranked.filter(c=>!["STRONGLY_ADVANCE","ADVANCE"].includes(c.recommendation)).length;
  const pills=[
    {key:"ALL",label:`All ${State.ranked.length}`},
    {key:"STRONGLY_ADVANCE",label:`Strongly advance ${sa}`,dot:"var(--success)"},
    {key:"ADVANCE",label:`Advance ${adv}`,dot:"var(--accent)"},
    {key:"REVIEW",label:`Review ${rev}`,dot:"var(--ink-400)"},
  ];
  let cands=State.ranked;
  if(flt==="STRONGLY_ADVANCE") cands=cands.filter(c=>c.recommendation==="STRONGLY_ADVANCE");
  else if(flt==="ADVANCE") cands=cands.filter(c=>c.recommendation==="ADVANCE");
  else if(flt==="REVIEW") cands=cands.filter(c=>!["STRONGLY_ADVANCE","ADVANCE"].includes(c.recommendation));
  if(srt==="notice") cands=[...cands].sort((a,b)=>(noticeDays(a)??999)-(noticeDays(b)??999));

  const trustBars=c=>{
    const ts=c.trust_assessment?.overall_trust_score||0;
    const tier=c.trust_assessment?.trust_tier||"—";
    const col=ts>=0.85?"var(--success)":ts>=0.6?"var(--accent)":ts>=0.4?"var(--warning)":"var(--danger)";
    // each bar lights up at its own threshold so the pattern varies across the 0–1 range
    const th=[0.2,0.45,0.7,0.9];
    const heights=[5,8,11,14];
    const bars=th.map((t,i)=>`<div style="width:3px;height:${heights[i]}px;background:${ts>=t?col:"var(--hair)"};border-radius:1px;${ts>=t?"":"opacity:0.4;"}"></div>`).join("");
    return `<div title="Trust score ${ts.toFixed(2)} · ${esc(tier)}" style="display:flex;align-items:flex-end;gap:2px;cursor:help;">${bars}</div>`;
  };
  const recDot=c=>{
    const col=c.recommendation==="STRONGLY_ADVANCE"?"var(--success)":c.recommendation==="ADVANCE"?"var(--accent)":"var(--ink-400)";
    const meta=TIER_META[c.recommendation]||TIER_META.REVIEW_FURTHER;
    return `<div style="display:flex;align-items:center;gap:6px;"><span style="width:7px;height:7px;border-radius:50%;background:${col};flex-shrink:0;"></span><span style="font-size:12.5px;color:${col};font-weight:500;">${meta.name}</span></div>`;
  };

  return `<div style="display:flex;flex-direction:column;height:100%;overflow:hidden;">
    <div class="expl-bar">
      ${pills.map(p=>`<button class="expl-pill${flt===p.key?" active":""}" data-filter="${p.key}">
        ${p.dot?`<span style="width:7px;height:7px;border-radius:50%;background:${p.dot};flex-shrink:0;"></span>`:""}
        ${esc(p.label)}</button>`).join("")}
      <div style="flex:1;"></div>
      <span class="mono" style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-400);">Sort</span>
      <button class="expl-sort${srt==="score"?" active":""}" data-sort="score">Score ↓</button>
      <button class="expl-sort${srt==="notice"?" active":""}" data-sort="notice">Notice ↑</button>
    </div>
    <div style="flex:1;overflow-y:auto;">
      <div style="min-width:860px;">
        <div class="expl-head">
          <div class="ec ec-rank">Rank</div>
          <div class="ec ec-trust" title="Trust score — profile credibility &amp; consistency (0–1). More bars filled = higher trust.">Trust</div>
          <div class="ec ec-name">Candidate</div>
          <div class="ec ec-score">Score</div>
          <div class="ec ec-rec">Recommendation</div>
          <div class="ec ec-notice">Notice</div>
          <div class="ec"></div>
        </div>
        ${cands.map(c=>`<div class="expl-row" data-open="${esc(c.candidate_id)}">
          <div class="ec ec-rank mono">#${c._rank}</div>
          <div class="ec ec-trust">${trustBars(c)}</div>
          <div class="ec ec-name">
            <div style="font-weight:600;font-size:14px;">${esc(c.name||c.candidate_id)}</div>
            <div style="font-size:12px;color:var(--ink-400);margin-top:1px;">${esc(metaLine(c))}</div>
          </div>
          <div class="ec ec-score mono">${fmtScore(c.overall_match_score)}</div>
          <div class="ec ec-rec">${recDot(c)}</div>
          <div class="ec ec-notice mono" style="color:${(noticeDays(c)||0)>30?"var(--warning)":"var(--ink-400)"}">${noticeLabel(c)||"—"}</div>
          <div class="ec" style="text-align:right;"><button class="expl-open row-open">Open →</button></div>
        </div>`).join("")}
      </div>
    </div>
  </div>`;
}

/* ============================================================ */
/*  PIPELINE  (S15)                                             */
/* ============================================================ */
function renderPipeline(){
  const advanced = State.ranked.filter(c=>State.decisions[c.candidate_id]==="advanced");
  const setaside = State.ranked.filter(c=>State.decisions[c.candidate_id]==="setaside");

  const cardHtml = (c, stage) => {
    const score = fmtScore(c.overall_match_score);
    const notice = noticeLabel(c);
    const recColor = {STRONGLY_ADVANCE:"var(--success)",ADVANCE_AFTER_SCREEN:"var(--accent)",REVIEW_IF_POOL_THIN:"var(--warning)",RESERVE_POOL:"var(--ink-400)"}[c.recommendation]||"var(--ink-400)";
    return `<div class="pl-card" data-open="${esc(c.candidate_id)}">
      <div class="pl-card-left">
        <div class="pl-rank mono">#${c._rank}</div>
        <div>
          <div class="pl-name">${esc(c.name)}</div>
          <div class="pl-meta">${esc(metaLine(c))}${notice?` · <span style="color:${noticeColor(c)}">${esc(notice)}</span>`:""}</div>
        </div>
      </div>
      <div class="pl-card-right">
        <span class="pl-score tabular">${score}</span>
        ${stage==="advanced"
          ? `<button class="btn pl-remove" data-remove="${esc(c.candidate_id)}">Remove</button>`
          : `<button class="btn pl-restore" data-restore="${esc(c.candidate_id)}">Restore</button>`}
      </div>
    </div>`;
  };

  const emptyState = `<div class="pl-empty">
    <div style="font-size:32px;margin-bottom:12px">📋</div>
    <div style="font-size:16px;font-weight:600;margin-bottom:6px">No candidates yet</div>
    <div style="font-size:13px;color:var(--ink-400)">Open a candidate and click "Advance to pipeline"</div>
  </div>`;

  const avgAdv = advanced.length
    ? (advanced.reduce((s,c)=>s+(c.overall_match_score||0),0)/advanced.length).toFixed(3) : "—";

  const side = `<div class="ri-side">
    <div class="sl-side-card">
      <div class="sl-side-label">Summary</div>
      <div class="sl-kv"><span>Advanced</span><span class="mono" style="color:var(--success)">${advanced.length}</span></div>
      <div class="sl-kv"><span>Set aside</span><span class="mono" style="color:var(--ink-400)">${setaside.length}</span></div>
      <div class="sl-kv"><span>Avg score</span><span class="mono">${avgAdv}</span></div>
    </div>
    ${advanced.length ? `<div class="sl-side-card">
      <div class="sl-side-label">Advanced candidates</div>
      ${advanced.map(c=>`<div class="sl-top-row" onclick="openRail('${esc(c.candidate_id)}')">
        <span class="sl-top-rank mono">#${c._rank}</span>
        <span class="sl-top-name">${esc(c.name)}</span>
        <span class="sl-top-score mono">${fmtScore(c.overall_match_score)}</span>
      </div>`).join("")}
    </div>` : ""}
    ${setaside.length ? `<div class="sl-side-card">
      <div class="sl-side-label">Set aside</div>
      ${setaside.map(c=>`<div class="sl-top-row" onclick="openRail('${esc(c.candidate_id)}')">
        <span class="sl-top-rank mono">#${c._rank}</span>
        <span class="sl-top-name">${esc(c.name)}</span>
        <span class="sl-top-score mono" style="color:var(--ink-400)">${fmtScore(c.overall_match_score)}</span>
      </div>`).join("")}
    </div>` : ""}
  </div>`;

  return `<div class="lens-pad"><div class="pl-two-col">
    <div class="ri-main">
      <div class="lens-header" style="margin-bottom:20px">
        <div>
          <div class="lens-kicker">Pipeline</div>
          <h1 class="lens-title">Rec. Systems Engineer</h1>
        </div>
      </div>

      <div class="section-label" style="margin-bottom:12px">Advanced to pipeline · ${advanced.length}</div>
      ${advanced.length ? advanced.map(c=>cardHtml(c,"advanced")).join("") : emptyState}

      ${setaside.length ? `
      <div class="section-label" style="margin-top:28px;margin-bottom:12px">Set aside · ${setaside.length}</div>
      ${setaside.map(c=>cardHtml(c,"setaside")).join("")}
      ` : ""}
    </div>
    ${side}
  </div></div>`;
}

/* ============================================================ */
/*  INTERVIEW GUIDE  (S11)                                      */
/* ============================================================ */
function renderGuide(forceCid){
  const cid = forceCid || State.currentCandidate;
  const c = cid ? State.byId[cid] : State.ranked[0];
  if(!c) return `<div class="lens-pad"><p style="color:var(--ink-400)">Open a candidate from the Shortlist first.</p></div>`;
  const ivs=c.interview_focus||[];
  const recColor=c.recommendation==="STRONGLY_ADVANCE"?"var(--success)":c.recommendation==="ADVANCE"?"var(--accent)":"var(--ink-400)";
  const catCol=dim=>{
    if(!dim) return "var(--accent)";
    const d=dim.toLowerCase();
    if(d.includes("gap")||d.includes("risk")) return "var(--warning)";
    if(d.includes("cult")||d.includes("behav")) return "var(--ink-400)";
    return "var(--accent)";
  };
  const d=dims(c);
  const dimRows=[["Technical",d.technical],["Product",d.product],["Cultural",d.cultural],["Growth",d.growth],["Availability",d.availability],["Trust",d.trust]];
  const risks=c.hiring_risks||[];
  const ev=c.top_evidence||[];

  const side = `<div class="ri-side">
    <div class="sl-side-card">
      <div class="sl-side-label">Candidate snapshot</div>
      <div class="sl-kv"><span>Rank</span><span class="mono">#${c._rank}</span></div>
      <div class="sl-kv"><span>Score</span><span class="mono">${fmtScore(c.overall_match_score)}</span></div>
      <div class="sl-kv"><span>Notice</span><span class="mono">${esc(noticeLabel(c)||"—")}</span></div>
    </div>
    <div class="sl-side-card">
      <div class="sl-side-label">Dimension breakdown</div>
      ${dimRows.map(([n,v])=>`<div class="dim-row" style="padding:5px 0">
        <span class="dim-name" style="font-size:12.5px">${esc(n)}</span>
        <span class="dim-track"><span class="dim-fill" style="width:${pct(v)}%"></span></span>
        <span class="dim-val tabular" style="font-size:12px">${(Number(v)||0).toFixed(2)}</span></div>`).join("")}
    </div>
    ${ev.length?`<div class="sl-side-card">
      <div class="sl-side-label">Strongest evidence</div>
      ${ev.slice(0,3).map(e=>`<div class="sl-kv" style="display:block;font-size:12.5px;line-height:1.5;padding:5px 0;"><span class="arr" style="color:var(--accent)">→</span> ${esc(e)}</div>`).join("")}
    </div>`:""}
    ${risks.length?`<div class="sl-side-card">
      <div class="sl-side-label">Hiring risks</div>
      ${risks.map(r=>`<div class="sl-kv" style="display:block;font-size:12.5px;line-height:1.5;padding:5px 0;"><span class="sev sev-${esc(r.severity||"LOW")}">${esc(r.severity||"LOW")}</span> ${esc(r.description||r.risk_type||"")}</div>`).join("")}
    </div>`:""}
  </div>`;

  return `<div class="lens-pad"><div class="ri-two-col">
    <div class="ri-main">
    <div style="background:#fff;border:1px solid var(--hair);border-radius:var(--r-md);padding:18px 22px;margin-bottom:24px;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
      <div>
        <div class="mono" style="font-size:10px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent);margin-bottom:7px;">Interview Focus</div>
        <div style="font-weight:600;font-size:22px;letter-spacing:-0.02em;">${esc(c.name||c.candidate_id)}</div>
        <div style="font-size:13.5px;color:var(--ink-600);margin-top:4px;">${esc(metaLine(c))} · Rank #${c._rank} · ${fmtScore(c.overall_match_score)}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
        <div style="display:flex;align-items:center;gap:7px;"><span class="dot" style="background:${recColor}"></span><span style="font-size:13px;font-weight:600;color:${recColor};">${esc((c.recommendation||"").replace(/_/g," "))}</span></div>
        <div style="font-size:12px;color:var(--ink-400);">${ivs.length} questions · 30 min screen</div>
        <button class="btn" id="guide-back">← Back to candidate</button>
      </div>
    </div>
    ${ivs.length===0?`<div style="background:var(--panel);border:1px solid var(--hair);border-radius:var(--r-md);padding:24px;text-align:center;color:var(--ink-400);">No interview questions for this candidate.</div>`:""}
    <div style="display:flex;flex-direction:column;gap:14px;">
      ${ivs.map((q,i)=>{
        const dim=q.dimension||q.category||"Technical";
        const pri=(q.priority||"").toLowerCase();
        const col=catCol(dim);
        const listen=q.what_to_listen_for||q.listen_for||"";
        const redflag=q.red_flag||"";
        return `<div style="background:#fff;border:1px solid var(--hair);border-radius:var(--r-md);overflow:hidden;">
          <div style="padding:13px 18px;border-bottom:1px solid var(--hair-soft);display:flex;align-items:center;gap:10px;">
            <span class="mono" style="font-size:13px;font-weight:600;background:var(--canvas);border-radius:6px;padding:3px 10px;">Q${i+1}</span>
            <span class="mono" style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;background:color-mix(in srgb,${col} 13%,var(--canvas));color:${col};border-radius:999px;padding:3px 10px;">${esc(dim)}${pri?" · "+esc(pri)+" priority":""}</span>
          </div>
          <div style="padding:16px 18px;">
            <p style="font-weight:600;font-size:15px;line-height:1.5;margin-bottom:12px;">"${esc(q.question)}"</p>
            <div style="display:flex;flex-direction:column;gap:7px;">
              ${listen?`<div style="padding:10px 12px;background:color-mix(in srgb,var(--success) 7%,var(--panel));border-radius:7px;border-left:3px solid var(--success);">
                <div class="mono" style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:var(--success);">Listen for</div>
                <p style="font-size:13px;color:var(--ink);margin-top:4px;line-height:1.45;">${esc(listen)}</p>
              </div>`:""}
              ${redflag?`<div style="padding:10px 12px;background:color-mix(in srgb,var(--danger) 6%,var(--panel));border-radius:7px;border-left:3px solid var(--danger);">
                <div class="mono" style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:var(--danger);">Red flag</div>
                <p style="font-size:13px;color:var(--ink);margin-top:4px;line-height:1.45;">${esc(redflag)}</p>
              </div>`:""}
            </div>
          </div>
        </div>`;
      }).join("")}
    </div>
    </div>
    ${side}
  </div></div>`;
}

/* ============================================================ */
/*  COPILOT  (client-side grounded retrieval — no hallucination)*/
/* ============================================================ */
const SUGGESTED=[
  "Why is the top candidate ranked first?",
  "Who is available in under 30 days?",
  "Show strongly advance candidates",
  "Who has the deepest skill match in the pool?",
  "What does this role actually require?",
];
function renderCopilot(){
  const empty=State.copilotThread.length===0;
  return `<div class="copilot-wrap">
    <div class="cp-thread" id="cp-thread">
      ${empty?`<div class="cp-empty">
        <h2>Ask about the candidates</h2>
        <p>Grounded in ${State.ranked.length} ranked candidates. It won't answer outside this role's data.</p>
        <div class="cp-suggest">${SUGGESTED.map(q=>`<button class="cp-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      </div>`: State.copilotThread.map(m=>copilotMsg(m)).join("")}
    </div>
    <div class="cp-inputbar"><div class="cp-inputbar-inner">
      <input id="cp-input" type="text" placeholder="Ask a question…" autocomplete="off">
      <button class="cp-send" id="cp-send"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"></path></svg></button>
    </div><div class="cp-grounded">Retrieval before generation · won't answer outside candidate, ranking & role data</div></div>
  </div>`;
}
function copilotMsg(m){
  const meta = m.loading
    ? `<div class="cp-meta cp-thinking"><span class="hiq-dots"><span></span><span></span><span></span></span> Thinking…</div>`
    : m.llm
      ? `<div class="cp-meta">Copilot · <span style="color:var(--accent)">LLM</span></div>`
      : `<div class="cp-meta">Copilot · grounded in ${m.grounded} record${m.grounded===1?"":"s"}</div>`;
  return `<div class="cp-msg">
    <div class="cp-q">${esc(m.q)}</div>
    ${meta}
    <div class="cp-a">${m.html}</div>
    ${m.cands&&m.cands.length?`<div class="cp-cands">${m.cands.map(c=>`
      <div class="cp-cand" data-open="${esc(c.candidate_id)}">
        <span class="r">#${c._rank}</span>
        <div><div style="font-weight:600;font-size:14px">${esc(c.name)}</div>
        <div style="font-size:12.5px;color:var(--ink-600)">${esc(metaLine(c))}${noticeLabel(c)?" · "+esc(noticeLabel(c)):""}</div></div>
        <span class="s tabular">${fmtScore(c.overall_match_score)}</span>
      </div>`).join("")}</div>`:""}
  </div>`;
}
function llmHtml(text){
  return "<p>"+esc(text).replace(/\n\n/g,"</p><p>").replace(/\n/g,"<br>")+"</p>";
}
async function copilotAsk(q){
  // push a loading placeholder immediately so the user sees feedback
  const pending={q, html:"", grounded:0, cands:[], loading:true};
  State.copilotThread.push(pending);
  setLens("copilot");
  const scroll=()=>{ const t=$("#cp-thread"); if(t) t.scrollTop=t.scrollHeight; };
  scroll();

  // try LLM API first; fall back to client-side retrieval if server is not running
  try{
    const cid=State.currentCandidate||null;
    const res=await fetch(`${API_BASE}/api/copilot`,{
      method:"POST",
      headers:{"Content-Type":"application/json",...authHeaders()},
      body:JSON.stringify({question:q, candidate_id:cid}),
    });
    if(!res.ok) throw new Error("API "+res.status);
    const data=await res.json();
    const idx=State.copilotThread.indexOf(pending);
    State.copilotThread[idx]={q, html:llmHtml(data.answer), grounded:1, cands:[], llm:true};
  } catch(_){
    // server not running — silent fallback to grounded retrieval
    const ans=answerQuestion(q);
    const idx=State.copilotThread.indexOf(pending);
    State.copilotThread[idx]={q, ...ans};
  }

  setLens("copilot");
  scroll();
}
/* the grounded "RAG" engine — pure retrieval over the loaded data */
function answerQuestion(qRaw){
  const q=qRaw.toLowerCase();
  const ranked=State.ranked;
  // 1. specific candidate by name or id
  const idMatch=qRaw.match(/CAND_\d{7}/i);
  let named=null;
  if(idMatch) named=State.byId[idMatch[0].toUpperCase()];
  if(!named){ named=ranked.find(c=>c.name && q.includes(c.name.toLowerCase().split(" ")[0])); }

  // why ranked first / explain top
  if(/why.*(first|top|#?1|number one)|why.*rank/.test(q) || (named && /why|explain|rank/.test(q))){
    const c=named|| ranked[0];
    const d=dims(c), ev=(c.top_evidence||[]);
    const neighbor=State.ranked[c._rank];
    let html=`<p>#${c._rank} <b>${esc(c.name)}</b> (${esc(metaLine(c))}) carries a <span class="cite">match ${fmtScore(c.overall_match_score)}</span> with a <span class="cite">${esc(c.recommendation.replace(/_/g," "))}</span> recommendation.</p>`;
    if(ev[0]) html+=`<p>${esc(ev[0])} <span class="cite">evidence</span></p>`;
    html+=`<p>Strongest dimensions: technical <span class="cite">${d.technical.toFixed(2)}</span>, product <span class="cite">${d.product.toFixed(2)}</span>, growth <span class="cite">${d.growth.toFixed(2)}</span>.</p>`;
    const risk=(c.hiring_risks||[])[0];
    if(risk) html+=`<p>Main concern: ${esc(risk.description)} <span class="cite">risk</span>.</p>`;
    if(neighbor) html+=`<p>Ranks above #${neighbor._rank} ${esc(neighbor.name)} (${fmtScore(neighbor.overall_match_score)}).</p>`;
    return {html, grounded:neighbor?2:1, cands:[c]};
  }
  // availability / notice
  const dayMatch=q.match(/(\d+)\s*day/);
  if(/avail|notice|start|immediate/.test(q)){
    const lim=dayMatch?parseInt(dayMatch[1]):30;
    const hits=ranked.filter(c=>{const dd=noticeDays(c); return dd!=null && dd<=lim;}).slice(0,8);
    const html=`<p>${hits.length} candidate${hits.length===1?"":"s"} can start within <span class="cite">${lim} days</span>${hits.length?", best first":""}.</p>`;
    return {html, grounded:hits.length, cands:hits};
  }
  // tier filter
  for(const [tk,meta] of Object.entries(TIER_META)){
    if(q.includes(meta.name.toLowerCase()) || (tk==="STRONGLY_ADVANCE"&&/strongly/.test(q)) || (tk==="ADVANCE"&&/\badvance\b/.test(q)&&!/strongly/.test(q))){
      const hits=ranked.filter(c=>c.recommendation===tk).slice(0,10);
      if(hits.length) return {html:`<p>${hits.length} in <span class="cite">${esc(meta.name)}</span>.</p>`, grounded:hits.length, cands:hits};
    }
  }
  // role / requirements
  if(/role|require|looking for|job|jd/.test(q)){
    const j=State.data.job_intelligence||{};
    const disc=(j.discriminator_hierarchy||[]).slice().sort((a,b)=>(b.weight||0)-(a.weight||0)).slice(0,3);
    let html=`<p>${esc(j.role_summary||j.ideal_candidate_narrative||"")}</p>`;
    if(disc.length) html+=`<p>Top discriminators: ${disc.map(d=>`${esc(d.name)} <span class="cite">${(d.weight||0).toFixed(2)}</span>`).join(", ")}.</p>`;
    return {html, grounded:1, cands:[]};
  }
  // skill / deepest match — full-text over evidence + matched skills
  const stop=new Set(["who","has","the","deepest","most","in","entire","pool","best","strongest","which","candidate","candidates","with","have","a","an","of","for"]);
  const terms=q.replace(/[^a-z0-9 ]/g,"").split(/\s+/).filter(w=>w.length>2&&!stop.has(w));
  if(terms.length){
    const scored=ranked.map(c=>{
      const hay=((c.top_evidence||[]).join(" ")+" "+(c.required_skills_matched||[]).join(" ")+" "+(c.recommendation_rationale||"")).toLowerCase();
      let s=0; terms.forEach(t=>{ if(hay.includes(t)) s++; });
      return {c,s};
    }).filter(x=>x.s>0).sort((a,b)=>b.s-a.s||(b.c.overall_match_score-a.c.overall_match_score)).slice(0,6);
    if(scored.length){
      return {html:`<p>${scored.length} candidate${scored.length===1?"":"s"} match <span class="cite">${esc(terms.join(", "))}</span> in their evidence, strongest first.</p>`,
              grounded:scored.length, cands:scored.map(x=>x.c)};
    }
  }
  // honest miss
  return {html:`<p>Nothing in the candidate, ranking, or role data matched that. Try asking about a candidate by name, a tier (e.g. "strongly advance"), availability, a skill, or the role requirements.</p>`, grounded:0, cands:[]};
}

/* ============================================================ */
/*  SIMULATOR                                                   */
/* ============================================================ */
function defaultWeights(){
  return { technical:0.28, product:0.15, cultural:0.10, growth:0.12, trust:0.05, availability:0.30 };
}
const SIM_LABELS={technical:"Technical fit",product:"Product fit",cultural:"Cultural fit",growth:"Career trajectory",trust:"Trust",availability:"Availability"};
const SIM_PRESETS={
  "Default": defaultWeights(),
  "Prioritise availability": {technical:0.20,product:0.12,cultural:0.08,growth:0.10,trust:0.05,availability:0.45},
  "Prioritise tech depth": {technical:0.45,product:0.18,cultural:0.07,growth:0.15,trust:0.05,availability:0.10},
};
function renderSimulator(){
  const w=State.simWeights, total=Object.values(w).reduce((a,b)=>a+b,0);
  const res=simulate(w);
  const baseline=State.ranked.map(c=>c.candidate_id);
  const movers=res.slice(0,5).filter(r=>r.delta!==0);
  let changed;
  if(movers.length){
    const up=res.filter(r=>r.delta>0).sort((a,b)=>b.delta-a.delta)[0];
    const down=res.filter(r=>r.delta<0).sort((a,b)=>a.delta-b.delta)[0];
    changed=`${up?`<b>${esc(up.c.name)}</b> rises ${up.delta} (#${up.was}→#${up.now}). `:""}${down?`<b>${esc(down.c.name)}</b> drops ${Math.abs(down.delta)} (#${down.was}→#${down.now}).`:""}`;
  } else changed="Rankings are stable — these weights already reflect the current order.";

  const presetActive=Object.entries(SIM_PRESETS).find(([k,v])=>JSON.stringify(v)===JSON.stringify(w))?.[0];
  const bigMover = res.filter(r=>Math.abs(r.delta)>0).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)).slice(0,5);

  return `<div class="lens-pad"><div style="width:100%">
    <div class="cmp-head"><div><div class="cmp-title">Decision Simulator</div>
      <div class="cmp-sub">Adjust weights and watch the ranking move. Re-ranking is instant — no model in the loop.</div></div>
      <button class="btn" id="sim-reset">Reset to default</button></div>
    <div class="sim-grid3">
      <div class="sim-panel">
        <div class="sim-h">Adjust weights</div>
        <div class="sim-sub">Weights auto-normalise. Drag to re-rank.</div>
        <div class="preset-row">${Object.keys(SIM_PRESETS).map(p=>`<button class="preset ${presetActive===p?'active':''}" data-preset="${esc(p)}">${esc(p)}</button>`).join("")}</div>
        ${Object.keys(SIM_LABELS).map(k=>`<div class="slider-row">
          <div class="slider-top"><span class="slider-name">${SIM_LABELS[k]}</span><span class="slider-val tabular" id="sv-${k}">${w[k].toFixed(2)}</span></div>
          <input type="range" min="0" max="0.6" step="0.01" value="${w[k]}" data-weight="${k}">
        </div>`).join("")}
        <div class="sim-total"><span>Total weight</span><b class="tabular" id="sim-total">${total.toFixed(2)} ✓</b></div>
      </div>
      <div class="sim-list" id="sim-list">${res.slice(0,15).map(r=>simRow(r)).join("")}</div>
      <div class="sim-side">
        <div class="sim-side-card" id="sim-changed-card">
          <div class="sim-side-label">What changed</div>
          <div id="sim-changed" class="sim-changed-body">${
            bigMover.length
              ? bigMover.map(r=>`<div class="sim-mover-row">
                  <span class="sim-mover-name">${esc(r.c.name)}</span>
                  <span class="sim-mover-delta ${r.delta>0?'up':'down'}">${r.delta>0?'↑ +'+r.delta:'↓ '+r.delta}</span>
                  <span class="sim-mover-pos mono">#${r.was}→#${r.now}</span>
                </div>`).join("")
              : `<div class="sim-stable">Rankings stable — these weights reflect the current order.</div>`
          }</div>
        </div>
        <div class="sim-side-card">
          <div class="sim-side-label">Weight breakdown</div>
          ${Object.keys(SIM_LABELS).map(k=>`
            <div class="sim-weight-row">
              <span class="sim-weight-name">${SIM_LABELS[k]}</span>
              <div class="sim-weight-bar-wrap"><div class="sim-weight-bar" style="width:${Math.round((w[k]/0.6)*100)}%"></div></div>
              <span class="sim-weight-val mono">${Math.round((w[k]/total)*100)}%</span>
            </div>`).join("")}
        </div>
      </div>
    </div></div></div>`;
}
function simulate(w){
  const total=Object.values(w).reduce((a,b)=>a+b,0)||1;
  const nw={}; Object.keys(w).forEach(k=>nw[k]=w[k]/total);
  const scored=State.ranked.map(c=>{
    const d=dims(c);
    let s=0; Object.keys(nw).forEach(k=>s+=nw[k]*(d[k]||0));
    return {c, score:s, was:(c._simBase??c._rank)};
  }).sort((a,b)=>b.score-a.score);
  scored.forEach((r,i)=>{ r.now=i+1; r.delta=r.was-r.now; });
  return scored;
}
function updateSimResults(){
  const w=State.simWeights, total=Object.values(w).reduce((a,b)=>a+b,0);
  const res=simulate(w);
  Object.keys(SIM_LABELS).forEach(k=>{ const el=$("#sv-"+k); if(el) el.textContent=w[k].toFixed(2); });
  const tot=$("#sim-total"); if(tot) tot.textContent=total.toFixed(2)+" ✓";
  // deactivate preset highlight if weights no longer match
  const active=Object.entries(SIM_PRESETS).find(([k,v])=>JSON.stringify(v)===JSON.stringify(w))?.[0];
  $$("[data-preset]").forEach(p=>p.classList.toggle("active",p.dataset.preset===active));
  const up=res.filter(r=>r.delta>0).sort((a,b)=>b.delta-a.delta)[0];
  const down=res.filter(r=>r.delta<0).sort((a,b)=>a.delta-b.delta)[0];
  const changed=(up||down)
    ? `${up?`<b>${esc(up.c.name)}</b> rises ${up.delta} (#${up.was}→#${up.now}). `:""}${down?`<b>${esc(down.c.name)}</b> drops ${Math.abs(down.delta)} (#${down.was}→#${down.now}).`:""}`
    : "Rankings are stable — these weights already reflect the current order.";
  const bigMover=res.filter(r=>Math.abs(r.delta)>0).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)).slice(0,5);
  const cb=$("#sim-changed");
  if(cb) cb.innerHTML = bigMover.length
    ? bigMover.map(r=>`<div class="sim-mover-row">
        <span class="sim-mover-name">${esc(r.c.name)}</span>
        <span class="sim-mover-delta ${r.delta>0?'up':'down'}">${r.delta>0?'↑ +'+r.delta:'↓ '+r.delta}</span>
        <span class="sim-mover-pos mono">#${r.was}→#${r.now}</span>
      </div>`).join("")
    : `<div class="sim-stable">Rankings stable — these weights reflect the current order.</div>`;
  // update weight bars in side panel
  Object.keys(SIM_LABELS).forEach(k=>{
    const bar=document.querySelector(`.sim-weight-bar[data-wk="${k}"]`);
    if(bar) bar.style.width=Math.round((w[k]/0.6)*100)+"%";
    const val=document.querySelector(`.sim-weight-val[data-wk="${k}"]`);
    if(val) val.textContent=Math.round((w[k]/total)*100)+"%";
  });
  const list=$("#sim-list"); if(list){ list.innerHTML=res.slice(0,15).map(r=>simRow(r)).join(""); }
}
function simRow(r){
  const c=r.c;
  const cls=r.delta>0?"up":r.delta<0?"down":"flat";
  const ico=r.delta>0?`↑ +${r.delta}`:r.delta<0?`↓ ${r.delta}`:"—";
  return `<div class="sim-item">
    <span class="sim-rank">#${r.now}</span>
    <span class="sim-move ${cls}">${ico}</span>
    <div class="sim-cand"><div class="sim-cn">${esc(c.name)}${r.delta!==0?` <span style="color:var(--ink-400);font-weight:400">(was #${r.was})</span>`:""}</div>
      <div class="sim-cm">${esc(metaLine(c))}</div></div>
    <div class="sim-cs"><div class="sim-score tabular">${r.score.toFixed(3)}</div>
      <div class="sim-notice">${esc(noticeLabel(c)||"")}</div></div>
  </div>`;
}

/* ============================================================ */
/*  COMMAND PALETTE                                             */
/* ============================================================ */
function openCmdk(){ $("#cmdk").hidden=false; $("#cmdk-input").value=""; renderCmdk(); $("#cmdk-input").focus(); }
function closeCmdk(){ $("#cmdk").hidden=true; }
function renderCmdk(){
  const q=($("#cmdk-input").value||"").toLowerCase().trim();
  const lenses=[["shortlist","Shortlist"],["explorer","Candidate Explorer"],["role","Role Intelligence"],["copilot","Copilot"],["simulator","Simulator"],["guide","Interview Guide"]]
    .filter(([k,n])=>!q||n.toLowerCase().includes(q));
  let cands=State.ranked;
  if(q) cands=cands.filter(c=>(c.name||"").toLowerCase().includes(q)||(c.candidate_id||"").toLowerCase().includes(q)||(c.current_company||"").toLowerCase().includes(q));
  cands=cands.slice(0,7);
  let html="";
  if(lenses.length){ html+=`<div class="cmdk-section">Lenses</div>`;
    lenses.forEach(([k,n])=>html+=`<div class="cmdk-item" data-lens-go="${k}"><span class="r">›</span><span class="t">${esc(n)}</span></div>`); }
  if(cands.length){ html+=`<div class="cmdk-section">Candidates</div>`;
    cands.forEach(c=>html+=`<div class="cmdk-item" data-open="${esc(c.candidate_id)}"><span class="r">#${c._rank}</span><span class="t">${esc(c.name)}</span><span class="m">${esc(metaLine(c))} · ${fmtScore(c.overall_match_score)}</span></div>`); }
  if(q && !cands.length && !lenses.length){
    html+=`<div class="cmdk-item" data-ask="${esc($("#cmdk-input").value)}"><span class="r">?</span><span class="t">Ask Copilot: "${esc($("#cmdk-input").value)}"</span></div>`;
  }
  $("#cmdk-results").innerHTML=html;
  $$("#cmdk-results .cmdk-item").forEach(it=>it.addEventListener("click",()=>{
    if(it.dataset.lensGo){ closeCmdk(); setLens(it.dataset.lensGo); }
    else if(it.dataset.open){ closeCmdk(); openRail(it.dataset.open); }
    else if(it.dataset.ask){ closeCmdk(); setLens("copilot"); copilotAsk(it.dataset.ask); }
  }));
}

/* ============================================================ */
/*  PER-LENS WIRING                                             */
/* ============================================================ */
function wireLens(lens){
  // universal: open candidate
  $$("[data-open]").forEach(el=>el.addEventListener("click",e=>{
    if(e.target.closest("[data-compare]"))return;
    openRail(el.dataset.open);
  }));
  if(lens==="shortlist"){
    $$("[data-expand]").forEach(b=>b.addEventListener("click",e=>{
      e.stopPropagation(); const t=b.dataset.expand;
      State.expanded[t]=!State.expanded[t]; setLens("shortlist");
    }));
    $$(".tier-action").forEach(b=>b.addEventListener("click",e=>{
      e.stopPropagation();
      const tier=b.closest("[data-tier]")?.dataset.tier;
      const cands=(State.data.candidates_by_tier||{})[tier]||[];
      cands.forEach(x=>{ State.decisions[x.candidate_id]="advanced"; persistDecision(x.candidate_id,"advanced"); });
      pushNotification(`${cands.length} candidates advanced to pipeline`, "var(--success)");
      setLens("shortlist");
      showToast(`✓ ${cands.length} candidates advanced to pipeline`, "success", ()=>{
        cands.forEach(x=>{ delete State.decisions[x.candidate_id]; removeDecision(x.candidate_id); });
        pushNotification(`${cands.length} candidates removed from pipeline`, "var(--ink-400)");
        setLens("shortlist");
        showToast(`Undone — removed from pipeline`, "neutral");
      });
    }));
  }
  if(lens==="copilot"){
    const ask=()=>{ const v=$("#cp-input").value.trim(); if(v){ $("#cp-input").value=""; copilotAsk(v); } };
    $("#cp-send")?.addEventListener("click",ask);
    $("#cp-input")?.addEventListener("keydown",e=>{ if(e.key==="Enter") ask(); });
    $$(".cp-chip").forEach(c=>c.addEventListener("click",()=>copilotAsk(c.dataset.q)));
    const inp=$("#cp-input"); if(inp) inp.focus();
  }
  if(lens==="simulator"){
    $("#sim-reset")?.addEventListener("click",()=>{ State.simWeights=defaultWeights(); setLens("simulator"); });
    $$("[data-preset]").forEach(p=>p.addEventListener("click",()=>{ State.simWeights={...SIM_PRESETS[p.dataset.preset]}; setLens("simulator"); }));
    $$("[data-weight]").forEach(s=>s.addEventListener("input",()=>{
      State.simWeights[s.dataset.weight]=parseFloat(s.value);
      updateSimResults();   // patch in place — keeps slider drag alive
    }));
  }
  if(lens==="explorer"){
    $$("[data-filter]").forEach(b=>b.addEventListener("click",()=>{ State.explorerFilter=b.dataset.filter; setLens("explorer"); }));
    $$("[data-sort]").forEach(b=>b.addEventListener("click",()=>{ State.explorerSort=b.dataset.sort; setLens("explorer"); }));
    $$(".row-open").forEach(b=>b.addEventListener("click",e=>{ e.stopPropagation(); openRail(b.closest("[data-open]").dataset.open); }));
  }
  if(lens==="guide"){
    $("#guide-back")?.addEventListener("click",()=>{ if(State.currentCandidate) openRail(State.currentCandidate); else setLens("shortlist"); });
  }
  if(lens==="pipeline"){
    $$("[data-remove]").forEach(b=>b.addEventListener("click",e=>{
      e.stopPropagation();
      const c=State.byId[b.dataset.remove]; if(!c) return;
      delete State.decisions[c.candidate_id];
      removeDecision(c.candidate_id);
      pushNotification(`${c.name} removed from pipeline`, "var(--ink-400)");
      setLens("pipeline");
      showToast(`${c.name} removed from pipeline`,"neutral",()=>{
        State.decisions[c.candidate_id]="advanced"; persistDecision(c.candidate_id,"advanced");
        pushNotification(`${c.name} restored to pipeline`, "var(--success)");
        setLens("pipeline");
        showToast(`✓ ${c.name} restored to pipeline`,"success");
      });
    }));
    $$("[data-restore]").forEach(b=>b.addEventListener("click",e=>{
      e.stopPropagation();
      const c=State.byId[b.dataset.restore]; if(!c) return;
      delete State.decisions[c.candidate_id];
      removeDecision(c.candidate_id);
      pushNotification(`${c.name} removed from set aside`, "var(--ink-400)");
      setLens("pipeline");
      showToast(`${c.name} removed from set aside`,"neutral",()=>{
        State.decisions[c.candidate_id]="setaside"; persistDecision(c.candidate_id,"setaside");
        pushNotification(`${c.name} set aside again`, "var(--warning)");
        setLens("pipeline");
      });
    }));
  }
}

/* ============================================================ */
/*  TOAST                                                       */
/* ============================================================ */
function showToast(msg, type="neutral", undoFn=null){
  let t=document.getElementById("hiq-toast");
  if(!t){ t=document.createElement("div"); t.id="hiq-toast"; document.body.appendChild(t); }
  t.className="hiq-toast hiq-toast-"+type+" hiq-toast-show";
  t.innerHTML = esc(msg) + (undoFn
    ? ` <button class="toast-undo" id="toast-undo-btn">Undo</button>`
    : "");
  if(undoFn){
    document.getElementById("toast-undo-btn").addEventListener("click",()=>{
      undoFn();
      t.classList.remove("hiq-toast-show");
      clearTimeout(t._timer);
    });
  }
  clearTimeout(t._timer);
  t._timer=setTimeout(()=>t.classList.remove("hiq-toast-show"),4000);
}

/* ============================================================ */
/*  ROLE PILL DROPDOWN                                          */
/* ============================================================ */
function toggleRoleDropdown(){
  const dd=document.getElementById("role-dropdown");
  if(!dd) return;
  dd.hidden=!dd.hidden;
  if(!dd.hidden){
    setTimeout(()=>document.addEventListener("click",_closeRoleOnOutside),0);
  }
}
function closeRoleDropdown(){
  const dd=document.getElementById("role-dropdown");
  if(dd) dd.hidden=true;
  document.removeEventListener("click",_closeRoleOnOutside);
}
function _closeRoleOnOutside(e){
  if(!document.getElementById("role-pill")?.contains(e.target)) closeRoleDropdown();
}

boot();
