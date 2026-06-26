import streamlit as st
from PIL import Image
from datetime import datetime
import plotly.graph_objects as go

from agent import nagarseva_graph, text_llm
from database import (
    init_db, save_issue, get_all_issues, get_pending_issues,
    merge_duplicate, upvote_issue, resolve_issue, get_stats,
    get_area_stats, get_priority_queue,
)
from modules.duplicate import check_duplicate
from modules.insights import generate_insights
from modules.letter_gen import generate_letter, build_whatsapp_message, DEPARTMENT_CONTACTS
from styles import get_css, SEVERITY_COLORS, THEMES

st.set_page_config(page_title="NagarSeva AI", page_icon="🏙️",
                   layout="wide", initial_sidebar_state="expanded")
init_db()

# Demo officer password (hackathon only — real app would use proper auth)
OFFICER_PASSWORD = "admin123"

# ─── State ─────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "role" not in st.session_state:
    st.session_state.role = "citizen"          # 'citizen' or 'officer'
if "upvoted_ids" not in st.session_state:
    st.session_state.upvoted_ids = set()        # prevent multiple upvotes per session
for k in ["result", "issue_saved", "letter", "dup_info", "whatsapp", "insights"]:
    if k not in st.session_state:
        st.session_state[k] = None
if "issue_saved" not in st.session_state:
    st.session_state.issue_saved = False

mode = st.session_state.theme
T = THEMES[mode]
is_officer = st.session_state.role == "officer"
st.markdown(get_css(mode), unsafe_allow_html=True)

# Small extra CSS for the compact theme toggle + role pills
st.markdown(f"""
<style>
.role-pill {{
    display:inline-block; padding:4px 14px; border-radius:30px;
    font-size:0.75rem; font-weight:700; letter-spacing:.5px;
}}
.theme-switch-row {{ display:flex; justify-content:center; gap:8px; margin:6px 0; }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, h=300):
    fig.update_layout(height=h, paper_bgcolor=T["chart_bg"], plot_bgcolor=T["chart_bg"],
                      font=dict(color=T["text_muted"]), margin=dict(t=30, b=30, l=30, r=30))
    return fig


# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-icon">🏙️</div>'
        '<div class="brand-name">NagarSeva AI</div>'
        '<div class="brand-tag">Gemini · LangGraph</div></div>',
        unsafe_allow_html=True)

    # Compact theme toggle (single small button that flips)
    next_theme = "light" if mode == "dark" else "dark"
    icon = "☀️ Light Mode" if mode == "dark" else "🌙 Dark Mode"
    if st.button(icon, use_container_width=True, key="theme_toggle"):
        st.session_state.theme = next_theme
        st.rerun()

    st.markdown("---")

    # ── Role switcher ──
    role_color = T["accent"] if is_officer else T["primary"]
    role_label = "👮 Officer" if is_officer else "👤 Citizen"
    st.markdown(f'<div style="text-align:center;margin-bottom:8px">'
                f'<span class="role-pill" style="background:{role_color}22;color:{role_color};border:1px solid {role_color}">'
                f'{role_label} Mode</span></div>', unsafe_allow_html=True)

    if not is_officer:
        with st.expander("👮 Login as Officer"):
            pwd = st.text_input("Officer password", type="password", key="off_pwd")
            if st.button("Login", use_container_width=True):
                if pwd == OFFICER_PASSWORD:
                    st.session_state.role = "officer"
                    st.rerun()
                else:
                    st.error("Wrong password")
        st.caption("Demo password: admin123")
    else:
        if st.button("🚪 Logout (back to Citizen)", use_container_width=True):
            st.session_state.role = "citizen"
            st.rerun()

    st.markdown("---")

    if not is_officer:
        st.markdown("### 👤 Reporter Details")
        reporter_name = st.text_input("name", placeholder="Your name", label_visibility="collapsed")
        location = st.text_input("loc", placeholder="📍 Location (e.g. Okhla, New Delhi)",
                                 label_visibility="collapsed")
    else:
        reporter_name, location = "", ""
        st.markdown("### 👮 Officer Console")
        st.caption("You can review and resolve issues reported by citizens.")

    st.markdown("---")
    st.markdown("### 🏢 Department Helplines")
    rows = "".join(
        f'<div class="help-row"><span class="help-dept">{d}</span>'
        f'<span class="help-num">{n}</span></div>'
        for d, n in DEPARTMENT_CONTACTS.items())
    st.markdown(rows, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="color:var(--text-dim);font-size:0.72rem;text-align:center">'
                "BlockseBlock × Google Hackathon<br>Community Hero Track</div>",
                unsafe_allow_html=True)

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero"><div class="hero-badge">🏆 BlockseBlock × Google Hackathon</div>'
    '<div class="hero-title">Nagar<span class="grad">Seva</span> AI</div>'
    '<div class="hero-sub">Snap a photo → AI detects the issue → A ready-to-send '
    'complaint. Be the voice of your community.</div></div>',
    unsafe_allow_html=True)

# ─── Tabs differ by role ───────────────────────────────────────────────────────
if is_officer:
    tab_review, tab_dash, tab_insights = st.tabs(
        ["🛠️  Resolve Issues", "📊  Dashboard", "🔮  Insights"])
else:
    tab1, tab_dash, tab_insights, tab_hist = st.tabs(
        ["📸  Report Issue", "📊  Dashboard", "🔮  Insights", "📋  History"])


# ══════════════════════════════════════════════════════════════════════════════
# SHARED RENDERERS
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    stats = get_stats()
    st.markdown("### 📊 Community Dashboard")
    d = st.columns(4)
    cards = [(stats["total"], "Total Issues", T["primary"]),
             (stats["pending"], "Pending", T["warning"]),
             (stats["resolved"], "Resolved", T["success"]),
             (stats["total_affected"], "People Affected", T["accent"])]
    for col, (val, lbl, color) in zip(d, cards):
        with col:
            st.markdown(f'<div class="stat"><div class="stat-val" style="color:{color}">{val}</div>'
                        f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if stats["by_category"]:
        g1, g2 = st.columns(2, gap="large")
        with g1:
            cats = [r["category"] for r in stats["by_category"]]
            counts = [r["count"] for r in stats["by_category"]]
            fig = go.Figure(go.Bar(x=cats, y=counts, marker_color=T["primary"],
                text=counts, textposition="outside", textfont=dict(color=T["text_muted"])))
            fig.update_layout(title=dict(text="Issues by Category", font=dict(color=T["text"])),
                yaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
                xaxis=dict(tickfont=dict(color=T["text_muted"])))
            st.plotly_chart(style_fig(fig, 330), use_container_width=True)
        with g2:
            depts = [r["department"] for r in stats["by_department"]]
            dcounts = [r["count"] for r in stats["by_department"]]
            fig2 = go.Figure(go.Pie(labels=depts, values=dcounts, hole=0.5,
                marker=dict(colors=["#6366f1", "#22d3ee", "#34d399", "#fbbf24", "#fb5252"])))
            fig2.update_layout(title=dict(text="Department Load", font=dict(color=T["text"])),
                legend=dict(font=dict(color=T["text_muted"])))
            st.plotly_chart(style_fig(fig2, 330), use_container_width=True)

        area_stats = get_area_stats()
        if area_stats:
            st.markdown("#### 🗺️ Most Affected Areas")
            locs = [a["location"][:30] for a in area_stats]
            ppl = [a["people"] for a in area_stats]
            fig3 = go.Figure(go.Bar(x=ppl, y=locs, orientation="h", marker_color=T["accent"],
                text=ppl, textposition="outside", textfont=dict(color=T["text_muted"])))
            fig3.update_layout(xaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
                yaxis=dict(tickfont=dict(color=T["text_muted"])))
            st.plotly_chart(style_fig(fig3, 300), use_container_width=True)
    else:
        st.markdown('<div class="empty"><div class="empty-icon">📊</div>'
                    '<div class="empty-text">No issues reported yet.</div></div>',
                    unsafe_allow_html=True)


def render_insights():
    st.markdown("### 🔮 AI Predictive Insights")
    if st.button("✨ Generate Insights", type="primary"):
        with st.spinner("AI is analyzing community data..."):
            st.session_state.insights = generate_insights(
                get_stats(), get_area_stats(), text_llm)
    if st.session_state.insights:
        st.markdown(f'<div class="highlight"><div class="highlight-label">🤖 AI Analysis</div>'
                    f'{st.session_state.insights}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><p style="color:var(--text-muted)">'
                    "Click <b>Generate Insights</b> to let the AI surface trends, "
                    "predictions, and recommendations from reported issues.</p></div>",
                    unsafe_allow_html=True)

    st.markdown("#### 🎯 Priority Queue")
    st.markdown('<p style="color:var(--text-muted);font-size:0.9rem">Issues ranked by severity, '
                "upvotes, report count, and people affected.</p>", unsafe_allow_html=True)
    pq = get_priority_queue()
    if not pq:
        st.markdown('<div class="empty"><div class="empty-icon">🎯</div>'
                    '<div class="empty-text">No pending issues to prioritize.</div></div>',
                    unsafe_allow_html=True)
    else:
        for rank, issue in enumerate(pq, 1):
            sc = SEVERITY_COLORS.get(issue["severity"], "#888")
            st.markdown(
                f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:var(--text);font-weight:700">#{rank} · {issue["issue_title"]}</span>'
                f'<span style="color:{sc};font-weight:700;font-size:0.8rem">● {issue["severity"]}</span></div>'
                f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:6px">'
                f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👍 {issue["upvotes"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">🔁 {issue["report_count"]}x</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]}</span>'
                f'</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CITIZEN VIEW
# ══════════════════════════════════════════════════════════════════════════════
if not is_officer:
    with tab1:
        col1, col2 = st.columns([1, 1], gap="large")
        with col1:
            st.markdown('<div class="step"><div class="step-dot">1</div>'
                        '<div class="step-text">Upload a photo of the issue</div></div>',
                        unsafe_allow_html=True)
            uploaded = st.file_uploader("upload", type=["jpg", "jpeg", "png", "webp"],
                                        label_visibility="collapsed")
            if uploaded:
                st.image(Image.open(uploaded), use_column_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("🚀 Analyze with AI", use_container_width=True, type="primary")

        with col2:
            if not st.session_state.result:
                st.markdown(
                    '<div class="card" style="min-height:340px"><h3>How it works</h3>'
                    '<div class="drow"><span>📸</span><span class="dval">Upload a photo — pothole, garbage, broken light, water leak</span></div>'
                    '<div class="drow"><span>🤖</span><span class="dval">Gemini Vision automatically detects the problem</span></div>'
                    '<div class="drow"><span>🔍</span><span class="dval">AI checks if it duplicates an existing nearby report</span></div>'
                    '<div class="drow"><span>📊</span><span class="dval">Scores severity & calculates community impact</span></div>'
                    '<div class="drow"><span>✉️</span><span class="dval">Generates a formal complaint letter for you</span></div>'
                    '<div class="drow"><span>🗣️</span><span class="dval">Plus a Hinglish summary to share on WhatsApp</span></div>'
                    '</div>', unsafe_allow_html=True)

        if analyze_btn and uploaded:
            image = Image.open(uploaded)
            steps = ["🔍 Scanning your photo... (our AI is working hard, promise 😎)",
                     "🏷️ Figuring out what's broken...",
                     "📊 Crunching the impact numbers...",
                     "🗣️ Cooking up some desi gyaan... 🍵"]
            prog = st.progress(0); status = st.empty()
            for i, s in enumerate(steps):
                status.markdown(f'<p style="color:var(--primary)">{s}</p>', unsafe_allow_html=True)
                prog.progress((i + 1) * 25)

            initial = {"image": image, "is_civic_issue": False, "issue_title": "",
                       "description": "", "location_hints": "", "category": "",
                       "severity": "", "severity_score": 0, "department": "",
                       "urgency": "", "affected_people": 0, "impact_score": 0,
                       "public_safety": 0, "health_risk": 0, "economic_impact": 0,
                       "inconvenience": 0, "environmental": 0, "escalation_needed": False,
                       "hinglish_summary": "", "error": ""}
            result = nagarseva_graph.invoke(initial)
            prog.empty(); status.empty()

            st.session_state.result = result
            st.session_state.issue_saved = False
            st.session_state.letter = None
            st.session_state.whatsapp = None
            st.session_state.dup_info = None

            if result.get("error") and not result.get("is_civic_issue"):
                st.error(f"❌ {result['error']}")
            elif not result.get("is_civic_issue"):
                st.warning("⚠️ No civic issue detected — try another photo!")
            else:
                st.success("✅ Analysis complete!")
                st.rerun()

        if st.session_state.result and st.session_state.result.get("is_civic_issue"):
            r = st.session_state.result
            sev_color = SEVERITY_COLORS.get(r["severity"], "#888")
            st.markdown("---")

            m = st.columns(4)
            metrics = [(r["severity"], "Severity", sev_color),
                       (f"{r['severity_score']}/10", "Score", T["primary"]),
                       (str(r["impact_score"]), "Impact", T["success"]),
                       (str(r["affected_people"]), "Affected", T["warning"])]
            for col, (val, lbl, color) in zip(m, metrics):
                with col:
                    st.markdown(f'<div class="metric"><div class="metric-val" style="color:{color}">{val}</div>'
                                f'<div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            left, right = st.columns([1, 1], gap="large")

            with left:
                esc = "⚠️ Recommended" if r["escalation_needed"] else "✅ Not needed"
                st.markdown(
                    f'<div class="card"><h3>{r["issue_title"]}</h3><p>{r["description"]}</p>'
                    f'<div class="drow"><span class="dlabel">📍 Location</span><span class="dval">{location or r["location_hints"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">🏷️ Category</span><span class="dval">{r["category"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">🏢 Department</span><span class="dval"><span class="chip">{r["department"]}</span></span></div>'
                    f'<div class="drow"><span class="dlabel">⏰ Urgency</span><span class="dval">{r["urgency"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">👥 Affected</span><span class="dval">{r["affected_people"]} residents</span></div>'
                    f'<div class="drow"><span class="dlabel">🚨 Escalation</span><span class="dval">{esc}</span></div></div>',
                    unsafe_allow_html=True)
                if r.get("hinglish_summary"):
                    st.markdown(f'<div class="highlight"><div class="highlight-label">🗣️ In Hinglish</div>'
                                f'{r["hinglish_summary"]}</div>', unsafe_allow_html=True)

            with right:
                cats = ["Public Safety", "Health Risk", "Economic", "Inconvenience", "Environmental"]
                vals = [r["public_safety"], r["health_risk"], r["economic_impact"],
                        r["inconvenience"], r["environmental"]]
                radar = go.Figure()
                radar.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=cats + [cats[0]],
                    fill="toself", fillcolor=T["primary_soft"], line=dict(color=T["primary"], width=2.5)))
                radar.update_layout(polar=dict(bgcolor=T["chart_bg"],
                    radialaxis=dict(range=[0, 100], gridcolor=T["border"], tickfont=dict(color=T["text_dim"], size=9)),
                    angularaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_muted"], size=11))),
                    showlegend=False)
                st.plotly_chart(style_fig(radar, 300), use_container_width=True)

                bar_colors = ["#fb5252" if v >= 80 else "#ff8c00" if v >= 60
                              else "#fbbf24" if v >= 40 else "#34d399" for v in vals]
                bar = go.Figure(go.Bar(x=[c.replace(" ", "<br>") for c in cats], y=vals,
                    marker_color=bar_colors, text=vals, textposition="outside",
                    textfont=dict(color=T["text_muted"], size=11)))
                bar.update_layout(yaxis=dict(range=[0, 115], gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
                    xaxis=dict(tickfont=dict(color=T["text_muted"], size=10)))
                st.plotly_chart(style_fig(bar, 230), use_container_width=True)

            if st.session_state.dup_info and st.session_state.dup_info["is_duplicate"]:
                di = st.session_state.dup_info
                st.markdown(
                    f'<div class="highlight" style="border-color:var(--warning)">'
                    f'<div class="highlight-label" style="color:var(--warning)">🔁 Duplicate Detected</div>'
                    f'{di["reason"]}<br><b>Merged with existing report #{di["matched_id"]}</b> — '
                    f'affected count updated.</div>', unsafe_allow_html=True)

            st.markdown("---")
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                if not st.session_state.issue_saved:
                    if st.button("💾 Save Issue", use_container_width=True):
                        pending = get_pending_issues()
                        new_issue = {"issue_title": r["issue_title"], "category": r["category"],
                                     "location": location or r["location_hints"],
                                     "description": r["description"]}
                        dup = check_duplicate(new_issue, pending, text_llm)
                        st.session_state.dup_info = dup
                        if dup["is_duplicate"] and dup["matched_id"]:
                            merge_duplicate(dup["matched_id"], r["affected_people"])
                        else:
                            save_issue({
                                "issue_title": r["issue_title"], "category": r["category"],
                                "severity": r["severity"], "severity_score": r["severity_score"],
                                "department": r["department"], "description": r["description"],
                                "location": location or r["location_hints"],
                                "affected_people": r["affected_people"],
                                "impact_score": r["impact_score"]})
                        st.session_state.issue_saved = True
                        st.rerun()
                else:
                    st.success("✅ Saved!")
            with a2:
                if st.button("📝 Letter", use_container_width=True):
                    with st.spinner("Writing letter..."):
                        st.session_state.letter = generate_letter(
                            issue_title=r["issue_title"], description=r["description"],
                            location=location or r["location_hints"], severity=r["severity"],
                            department=r["department"], name=reporter_name or "Concerned Citizen",
                            llm=text_llm)
            with a3:
                if st.button("📱 WhatsApp", use_container_width=True):
                    st.session_state.whatsapp = build_whatsapp_message(r, location)
            with a4:
                if st.button("🔄 New", use_container_width=True):
                    for k in ["result", "issue_saved", "letter", "whatsapp", "dup_info"]:
                        st.session_state[k] = None
                    st.session_state.issue_saved = False
                    st.rerun()

            if st.session_state.letter:
                st.markdown(f'<div class="letter">{st.session_state.letter}</div>', unsafe_allow_html=True)
                st.download_button("⬇️ Download Letter", st.session_state.letter,
                                   file_name=f"complaint_{datetime.now().strftime('%Y%m%d')}.txt")
            if st.session_state.whatsapp:
                st.markdown('<div class="highlight"><div class="highlight-label">📱 WhatsApp Message (copy & share)</div></div>',
                            unsafe_allow_html=True)
                st.code(st.session_state.whatsapp, language=None)

    with tab_dash:
        render_dashboard()

    with tab_insights:
        render_insights()

    with tab_hist:
        st.markdown("### 📋 Issue History")
        issues = get_all_issues()
        if not issues:
            st.markdown('<div class="empty"><div class="empty-icon">📋</div>'
                        '<div class="empty-text">No issues found yet.</div></div>',
                        unsafe_allow_html=True)
        else:
            for issue in issues:
                issue = dict(issue)
                sc = SEVERITY_COLORS.get(issue["severity"], "#888")
                resolved = issue["status"] == "Resolved"
                status_color = T["success"] if resolved else T["warning"]
                status_icon = "✅" if resolved else "⏳"
                st.markdown(
                    f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                    f'<span style="color:var(--text);font-weight:700;font-size:1rem">{issue["issue_title"]}</span>'
                    f'<span style="color:{sc};font-size:0.8rem;font-weight:700">● {issue["severity"]}</span></div>'
                    f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]} affected</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">👍 {issue["upvotes"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">🔁 {issue["report_count"]}x</span>'
                    f'<span style="color:{status_color};font-size:0.8rem;font-weight:600">{status_icon} {issue["status"]}</span>'
                    f'</div></div>', unsafe_allow_html=True)

                # Citizen can only upvote, once per session
                already = issue["id"] in st.session_state.upvoted_ids
                if already:
                    st.button("✓ Upvoted", key=f"up_{issue['id']}", use_container_width=False, disabled=True)
                else:
                    if st.button("👍 Upvote", key=f"up_{issue['id']}", use_container_width=False):
                        upvote_issue(issue["id"])
                        st.session_state.upvoted_ids.add(issue["id"])
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# OFFICER VIEW
# ══════════════════════════════════════════════════════════════════════════════
else:
    with tab_review:
        st.markdown("### 🛠️ Resolve Issues")
        st.markdown('<p style="color:var(--text-muted)">Review citizen-reported issues and mark them '
                    "resolved once your team has acted on the ground.</p>", unsafe_allow_html=True)

        issues = get_all_issues()
        pending = [dict(i) for i in issues if dict(i)["status"] == "Pending"]
        resolved = [dict(i) for i in issues if dict(i)["status"] == "Resolved"]

        st.markdown(f"#### ⏳ Pending ({len(pending)})")
        if not pending:
            st.markdown('<div class="empty"><div class="empty-icon">✅</div>'
                        '<div class="empty-text">No pending issues. Great work!</div></div>',
                        unsafe_allow_html=True)
        for issue in pending:
            sc = SEVERITY_COLORS.get(issue["severity"], "#888")
            st.markdown(
                f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<span style="color:var(--text);font-weight:700;font-size:1rem">{issue["issue_title"]}</span>'
                f'<span style="color:{sc};font-size:0.8rem;font-weight:700">● {issue["severity"]} ({issue["severity_score"]}/10)</span></div>'
                f'<p style="color:var(--text-muted);font-size:0.85rem;margin:4px 0">{issue["description"]}</p>'
                f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
                f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]} affected</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👍 {issue["upvotes"]} upvotes</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">🔁 {issue["report_count"]} reports</span>'
                f'</div></div>', unsafe_allow_html=True)
            if st.button(f"✅ Mark Resolved", key=f"res_{issue['id']}", use_container_width=False):
                resolve_issue(issue["id"])
                st.rerun()

        if resolved:
            st.markdown(f"#### ✅ Resolved ({len(resolved)})")
            for issue in resolved:
                st.markdown(
                    f'<div class="hist" style="opacity:0.7">'
                    f'<span style="color:var(--text);font-weight:700">{issue["issue_title"]}</span> '
                    f'<span style="color:var(--success);font-size:0.8rem;font-weight:600">✅ Resolved</span><br>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]} · 📍 {issue["location"]}</span>'
                    f'</div>', unsafe_allow_html=True)

    with tab_dash:
        render_dashboard()

    with tab_insights:
        render_insights()