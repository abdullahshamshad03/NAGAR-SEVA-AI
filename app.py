import streamlit as st
from PIL import Image
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import os
import uuid

from agent import nagarseva_graph, text_llm
from database import (
    init_db, save_issue, get_all_issues, get_pending_issues,
    merge_duplicate, upvote_issue, resolve_issue, get_stats,
    get_area_stats, get_priority_queue, get_issues_by_department,
    get_department_stats, confirm_resolution, reopen_issue,
    get_department_performance, get_citizen_points, get_leaderboard,
    get_geolocated_issues, get_issues_by_mobile,
)
from modules.duplicate import check_duplicate
from modules.insights import generate_insights
from modules.geocode import geocode_location, validate_location, reverse_geocode, in_ncr

# Optional GPS component — app still works if it isn't installed
try:
    from streamlit_geolocation import streamlit_geolocation
    _HAS_GPS = True
except Exception:
    _HAS_GPS = False
from modules.email_gen import (
    generate_email, build_mailto, build_whatsapp_message,
    DEPARTMENT_CONTACTS, get_department_email,
)
from styles import get_css, SEVERITY_COLORS, THEMES

st.set_page_config(page_title="NagarSeva AI", page_icon="🏙️",
                   layout="wide", initial_sidebar_state="expanded")
init_db()

# Folder to persist uploaded issue images (for the community feed)
UPLOAD_DIR = "issue_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEPARTMENT_PASSWORDS = {
    "PWD": "pwd123", "MCD": "mcd123", "DJB": "djb123",
    "BSES": "bses123", "Delhi Police": "police123",
    "Fire Service": "fire123", "Environment": "env123",
    "Health": "health123", "Transport": "transport123",
    "Education": "edu123",
}

# ─── State ─────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "role" not in st.session_state:
    st.session_state.role = "citizen"
if "officer_dept" not in st.session_state:
    st.session_state.officer_dept = None
if "upvoted_ids" not in st.session_state:
    st.session_state.upvoted_ids = set()
for k in ["result", "issue_saved", "email", "dup_info", "whatsapp", "insights"]:
    if k not in st.session_state:
        st.session_state[k] = None
if "issue_saved" not in st.session_state:
    st.session_state.issue_saved = False

mode = st.session_state.theme
T = THEMES[mode]
is_officer = st.session_state.role == "officer"
st.markdown(get_css(mode), unsafe_allow_html=True)

# Grant geolocation (and camera) permission to Streamlit component iframes.
# Without this, the GPS button and camera fail with "site can't ask for permission".
st.markdown("""
<script>
(function () {
  function grantIframePerms() {
    const frames = window.parent.document.querySelectorAll('iframe');
    frames.forEach(function (f) {
      const current = f.getAttribute('allow') || '';
      if (!current.includes('geolocation')) {
        f.setAttribute('allow', (current + '; geolocation; camera; microphone').trim());
      }
    });
  }
  grantIframePerms();
  // Re-apply when Streamlit re-renders (new iframes get added)
  const obs = new MutationObserver(grantIframePerms);
  obs.observe(window.parent.document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.role-pill { display:inline-block; padding:4px 14px; border-radius:30px;
    font-size:0.75rem; font-weight:700; letter-spacing:.5px; }
</style>
""", unsafe_allow_html=True)


def style_fig(fig, h=300):
    fig.update_layout(height=h, paper_bgcolor=T["chart_bg"], plot_bgcolor=T["chart_bg"],
                      font=dict(color=T["text_muted"]), margin=dict(t=30, b=30, l=30, r=30))
    return fig


def status_display(issue, theme):
    """
    Returns (text, color, icon) reflecting the true state, including the
    citizen-verification step between officer-resolved and truly-resolved.
    """
    status = issue.get("status", "Pending")
    verif = issue.get("verification", "NA")

    if status == "Pending":
        return ("Pending", theme["warning"], "⏳")
    # status == Resolved → depends on citizen verification
    if verif == "Pending":
        return ("Awaiting citizen verification", theme["accent"], "❓")
    if verif == "Confirmed":
        return ("Resolved (citizen confirmed)", theme["success"], "✅")
    if verif == "Reopened":
        return ("Reopened by citizen", theme["danger"], "🔄")
    # Fallback (officer resolved, no verification record yet)
    return ("Awaiting citizen verification", theme["accent"], "❓")


# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-icon">🏙️</div>'
        '<div class="brand-name">NagarSeva AI</div>'
        '<div class="brand-tag">Gemini · LangGraph</div></div>',
        unsafe_allow_html=True)

    next_theme = "light" if mode == "dark" else "dark"
    icon = "☀️ Light Mode" if mode == "dark" else "🌙 Dark Mode"
    if st.button(icon, use_container_width=True, key="theme_toggle"):
        st.session_state.theme = next_theme
        st.rerun()

    st.markdown("---")

    role_color = T["accent"] if is_officer else T["primary"]
    role_label = (f"👮 {st.session_state.officer_dept} Officer"
                  if is_officer else "👤 Citizen")
    st.markdown(f'<div style="text-align:center;margin-bottom:8px">'
                f'<span class="role-pill" style="background:{role_color}22;color:{role_color};border:1px solid {role_color}">'
                f'{role_label} Mode</span></div>', unsafe_allow_html=True)

    if not is_officer:
        with st.expander("👮 Login as Officer"):
            dept = st.selectbox("Department", list(DEPARTMENT_PASSWORDS.keys()), key="off_dept")
            # Show only the demo password for the selected department (clean hint)
            demo_pw = DEPARTMENT_PASSWORDS.get(dept, "")
            st.markdown(f'<div style="color:var(--text-muted);font-size:0.82rem;margin:4px 0">'
                        f'🔑 Demo password for {dept}: '
                        f'<b style="color:var(--primary)">{demo_pw}</b></div>',
                        unsafe_allow_html=True)
            pwd = st.text_input("Officer password", type="password", key="off_pwd")
            if st.button("Login", use_container_width=True):
                if pwd == DEPARTMENT_PASSWORDS.get(dept):
                    st.session_state.role = "officer"
                    st.session_state.officer_dept = dept
                    st.rerun()
                else:
                    st.error("Wrong password for this department")
    else:
        if st.button("🚪 Logout (back to Citizen)", use_container_width=True):
            st.session_state.role = "citizen"
            st.session_state.officer_dept = None
            st.rerun()

    st.markdown("---")

    if not is_officer:
        # Reporter name/location now live on the Report tab (front & center).
        # Sidebar just shows the live gamification score.
        reporter_name = st.session_state.get("reporter_name", "")
        location = st.session_state.get("reporter_location", "")
        if reporter_name and reporter_name.strip():
            pts = get_citizen_points(reporter_name.strip())
            st.markdown("### 👤 Your Stats")
            st.markdown(
                f'<div class="card" style="text-align:center;padding:1rem">'
                f'<div style="font-size:1.8rem">{pts["badge"]}</div>'
                f'<div style="color:var(--text);font-weight:700">{pts["title"]}</div>'
                f'<div style="color:var(--primary);font-size:1.4rem;font-weight:800">{pts["points"]} pts</div>'
                f'<div style="color:var(--text-dim);font-size:0.72rem">'
                f'{pts["reports"]} reports · {pts["upvotes"]} upvotes · {pts["confirmed"]} confirmed</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--text-dim);font-size:0.8rem;text-align:center">'
                        "👋 Enter your name & location on the<br><b>Report Issue</b> tab to get started.</div>",
                        unsafe_allow_html=True)
    else:
        reporter_name, location = "", ""
        st.markdown(f"### 👮 {st.session_state.officer_dept} Console")
        st.caption(f"You see only {st.session_state.officer_dept} issues.")

    st.markdown("---")
    st.markdown("### 🏢 Department Contacts")
    rows = "".join(
        f'<div class="help-row"><span class="help-dept">{d}</span>'
        f'<span class="help-num">{c["phone"]}</span></div>'
        for d, c in DEPARTMENT_CONTACTS.items())
    st.markdown(rows, unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("🚨 Emergency SOS"):
        emergency = [
            ("🚓 Police", "100"), ("🚑 Ambulance", "102"), ("🚒 Fire", "101"),
            ("👩 Women Helpline", "1091"), ("🧒 Child Helpline", "1098"),
            ("🆘 Emergency", "112"),
        ]
        erows = "".join(
            f'<div class="help-row"><span class="help-dept">{n}</span>'
            f'<span class="help-num" style="color:var(--danger)">{num}</span></div>'
            for n, num in emergency)
        st.markdown(erows, unsafe_allow_html=True)
        st.caption("⚠️ Use only in a real emergency. False calls are punishable.")

    st.markdown("---")
    st.markdown('<div style="color:var(--text-dim);font-size:0.72rem;text-align:center">'
                "BlockseBlock × Google Hackathon<br>Community Hero Track</div>",
                unsafe_allow_html=True)

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero"><div class="hero-badge">🏆 BlockseBlock × Google Hackathon</div>'
    '<div class="hero-title">Nagar<span class="grad">Seva</span> AI</div>'
    '<div class="hero-sub">Snap a photo → AI detects the issue → A ready-to-send '
    'complaint. Be the voice of your community.<br>'
    '<span style="font-size:0.85rem;color:var(--text-dim)">📍 Currently serving Delhi NCR · '
    'more cities coming soon</span></div></div>',
    unsafe_allow_html=True)

if is_officer:
    tab_review, tab_dash, tab_insights = st.tabs(
        ["🛠️  Resolve Issues", "📊  Dashboard", "🔮  Insights"])
else:
    tab_feed, tab1, tab_dash, tab_insights, tab_hist = st.tabs(
        ["🌍  Community Feed", "📸  Report Issue", "📊  Dashboard",
         "🔮  Insights", "📋  Track Complaints"])


# ══════════════════════════════════════════════════════════════════════════════
# SHARED RENDERERS
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard(dept_filter=None):
    if dept_filter:
        stats = get_department_stats(dept_filter)
        st.markdown(f"### 📊 {dept_filter} Dashboard")
    else:
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

    if dept_filter:
        dept_issues = get_issues_by_department(dept_filter)
        if not dept_issues:
            st.markdown('<div class="empty"><div class="empty-icon">📊</div>'
                        f'<div class="empty-text">No {dept_filter} issues yet.</div></div>',
                        unsafe_allow_html=True)
            return
        st.markdown("#### 🗺️ Most Affected Areas (your department)")
        loc_map = {}
        for i in dept_issues:
            loc_map[i["location"]] = loc_map.get(i["location"], 0) + i["affected_people"]
        locs = list(loc_map.keys())[:10]
        ppl = [loc_map[l] for l in locs]
        fig = go.Figure(go.Bar(x=ppl, y=[l[:30] for l in locs], orientation="h",
            marker_color=T["accent"], text=ppl, textposition="outside",
            textfont=dict(color=T["text_muted"])))
        fig.update_layout(xaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
            yaxis=dict(tickfont=dict(color=T["text_muted"])))
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        return

    # Community-wide: verification trust bar
    if stats["resolved"] > 0 or stats["reopened"] > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat"><div class="stat-val" style="color:{T["success"]}">'
                        f'{stats["confirmed"]}</div><div class="stat-lbl">✅ Citizen Confirmed</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat"><div class="stat-val" style="color:{T["danger"]}">'
                        f'{stats["reopened"]}</div><div class="stat-lbl">🔄 Reopened</div></div>',
                        unsafe_allow_html=True)
        with c3:
            total_verified = stats["confirmed"] + stats["reopened"]
            trust = round(100 * stats["confirmed"] / total_verified) if total_verified else 0
            st.markdown(f'<div class="stat"><div class="stat-val" style="color:{T["primary"]}">'
                        f'{trust}%</div><div class="stat-lbl">Trust Score</div></div>',
                        unsafe_allow_html=True)
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

        # Department performance (avg resolution time)
        perf = get_department_performance()
        if perf:
            st.markdown("#### ⏱️ Department Performance (avg resolution time)")
            perf_depts = [p["department"] for p in perf]
            ph = [p["avg_hours"] for p in perf]
            figp = go.Figure(go.Bar(x=perf_depts, y=ph, marker_color=T["success"],
                text=[f"{h}h" for h in ph], textposition="outside",
                textfont=dict(color=T["text_muted"])))
            figp.update_layout(yaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"]),
                title=dict(text="Hours", font=dict(color=T["text_dim"]))),
                xaxis=dict(tickfont=dict(color=T["text_muted"])))
            st.plotly_chart(style_fig(figp, 280), use_container_width=True)

        area_stats = get_area_stats()
        # Only show this chart when there are 2+ areas (a single bar looks broken)
        if area_stats and len(area_stats) >= 2:
            st.markdown("#### 🗺️ Most Affected Areas")
            locs = [a["location"][:30] for a in area_stats]
            ppl = [a["people"] for a in area_stats]
            fig3 = go.Figure(go.Bar(x=ppl, y=locs, orientation="h", marker_color=T["accent"],
                text=ppl, textposition="outside", textfont=dict(color=T["text_muted"])))
            fig3.update_layout(xaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
                yaxis=dict(tickfont=dict(color=T["text_muted"])))
            st.plotly_chart(style_fig(fig3, 300), use_container_width=True)

        # Department activity by area — which dept is busiest where
        all_for_area = [dict(i) for i in get_all_issues()]
        if len(all_for_area) >= 2:
            st.markdown("#### 🏢 Department Activity by Area")
            st.markdown('<p style="color:var(--text-muted);font-size:0.88rem">Which department '
                        "handles the most issues in each area.</p>", unsafe_allow_html=True)
            # Build {area: {dept: count}}
            area_dept = {}
            for i in all_for_area:
                a = i["location"][:25]
                area_dept.setdefault(a, {})
                area_dept[a][i["department"]] = area_dept[a].get(i["department"], 0) + 1
            areas = list(area_dept.keys())
            dept_colors = {"PWD": "#6366f1", "MCD": "#22d3ee", "DJB": "#34d399",
                           "BSES": "#fbbf24", "Delhi Police": "#fb5252",
                           "Fire Service": "#f97316", "Environment": "#10b981",
                           "Health": "#ec4899", "Transport": "#8b5cf6",
                           "Education": "#06b6d4"}
            depts = list(dept_colors.keys())
            stack = go.Figure()
            for dept in depts:
                stack.add_trace(go.Bar(
                    name=dept, x=areas,
                    y=[area_dept[a].get(dept, 0) for a in areas],
                    marker_color=dept_colors[dept]))
            stack.update_layout(
                barmode="stack",
                yaxis=dict(gridcolor=T["border"], tickfont=dict(color=T["text_dim"])),
                xaxis=dict(tickfont=dict(color=T["text_muted"])),
                legend=dict(font=dict(color=T["text_muted"]), orientation="h", y=-0.2))
            st.plotly_chart(style_fig(stack, 340), use_container_width=True)

        # ── Live Issue Map (Delhi NCR) ──
        st.markdown("#### 📍 Issue Map")
        geo_issues = get_geolocated_issues()
        total_issues = len(get_all_issues())
        if not geo_issues:
            hint = ("Save an issue with a Delhi location and it'll appear here as a pin."
                    if total_issues == 0 else
                    f"You have {total_issues} issue(s), but none have map coordinates yet. "
                    "This happens if geocoding was offline when they were saved. "
                    "Report a fresh issue with a Delhi location to see it pinned.")
            st.markdown('<div class="empty"><div class="empty-icon">📍</div>'
                        f'<div class="empty-text">No mapped issues yet. {hint}</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<p style="color:var(--text-muted);font-size:0.88rem">'
                        f'{len(geo_issues)} issue(s) pinned by location across Delhi NCR. '
                        "Color = severity.</p>", unsafe_allow_html=True)
            sev_color_map = {"Critical": "#fb5252", "High": "#ff8c00",
                             "Medium": "#fbbf24", "Low": "#34d399"}
            lats = [float(i["lat"]) for i in geo_issues]
            lons = [float(i["lon"]) for i in geo_issues]
            colors = [sev_color_map.get(i["severity"], "#6366f1") for i in geo_issues]
            texts = [f'{i["issue_title"]} ({i["severity"]}) - {i["location"]}'
                     for i in geo_issues]

            map_fig = go.Figure(go.Scattermapbox(
                lat=lats, lon=lons, mode="markers",
                marker=dict(size=16, color=colors),
                text=texts, hoverinfo="text",
            ))
            map_fig.update_layout(
                mapbox_style="open-street-map",
                mapbox=dict(
                    center=dict(lat=sum(lats) / len(lats), lon=sum(lons) / len(lons)),
                    zoom=10),
                height=450, margin=dict(t=0, b=0, l=0, r=0),
                paper_bgcolor=T["chart_bg"],
            )
            st.plotly_chart(map_fig, use_container_width=True)
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
                    "Click <b>Generate Insights</b> to surface trends and predictions.</p></div>",
                    unsafe_allow_html=True)

    # Leaderboard (gamification)
    st.markdown("#### 🏆 Top Citizens")
    lb = get_leaderboard()
    if not lb:
        st.markdown('<p style="color:var(--text-muted);font-size:0.9rem">No ranked citizens yet. '
                    "Report issues with your name to climb the leaderboard!</p>", unsafe_allow_html=True)
    else:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, c in enumerate(lb):
            st.markdown(
                f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:var(--text);font-weight:700">{medals[i] if i < 5 else ""} {c["reporter"]}</span>'
                f'<span style="color:var(--primary);font-weight:800">{c["points"]} pts</span></div>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">{c["reports"]} reports</span></div>',
                unsafe_allow_html=True)

    st.markdown("#### 🎯 Priority Queue")
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
                f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]}</span>'
                f'</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CITIZEN VIEW
# ══════════════════════════════════════════════════════════════════════════════
if not is_officer:
    with tab_feed:
        st.markdown("### 🌍 Community Feed")
        st.markdown('<p style="color:var(--text-muted)">Civic issues reported by people across Delhi NCR. '
                    "Upvote the ones that affect you — more upvotes push issues up the priority queue.</p>",
                    unsafe_allow_html=True)

        all_issues = [dict(i) for i in get_all_issues()]

        if not all_issues:
            st.markdown('<div class="empty"><div class="empty-icon">🌍</div>'
                        '<div class="empty-text">No issues reported yet. Be the first to report one!</div></div>',
                        unsafe_allow_html=True)
        else:
            # Filters
            f1, f2, f3 = st.columns(3)
            with f1:
                cats = ["All"] + sorted(set(i["category"] for i in all_issues))
                f_cat = st.selectbox("Category", cats, key="feed_cat")
            with f2:
                sevs = ["All", "Critical", "High", "Medium", "Low"]
                f_sev = st.selectbox("Severity", sevs, key="feed_sev")
            with f3:
                sort_by = st.selectbox("Sort by", ["Most Upvoted", "Newest", "Most Affected"], key="feed_sort")

            # Apply filters
            feed = all_issues
            if f_cat != "All":
                feed = [i for i in feed if i["category"] == f_cat]
            if f_sev != "All":
                feed = [i for i in feed if i["severity"] == f_sev]

            # Sort
            if sort_by == "Most Upvoted":
                feed.sort(key=lambda x: x["upvotes"], reverse=True)
            elif sort_by == "Newest":
                feed.sort(key=lambda x: x["created_at"], reverse=True)
            else:
                feed.sort(key=lambda x: x["affected_people"], reverse=True)

            st.markdown(f'<p style="color:var(--text-dim);font-size:0.85rem">Showing {len(feed)} issues</p>',
                        unsafe_allow_html=True)

            for issue in feed:
                sc = SEVERITY_COLORS.get(issue["severity"], "#888")
                status_txt, status_color, status_icon = status_display(issue, T)

                # Image + details side by side (social-media style card)
                img_path_raw = issue.get("image_path") or ""
                # image_path may hold comma-separated paths (multiple photos)
                img_list = [p for p in img_path_raw.split(",") if p and os.path.exists(p)]
                has_img = len(img_list) > 0
                if has_img:
                    ic, dc = st.columns([1, 3], gap="medium")
                    with ic:
                        # Primary photo
                        st.image(img_list[0], use_column_width=True)
                        # Extra photos as a small thumbnail gallery
                        if len(img_list) > 1:
                            extra = img_list[1:5]  # show up to 4 extra
                            tcols = st.columns(len(extra))
                            for ti, tp in enumerate(extra):
                                with tcols[ti]:
                                    st.image(tp, use_column_width=True)
                            if len(img_list) > 5:
                                st.caption(f"+{len(img_list) - 5} more")
                    detail_col = dc
                else:
                    detail_col = st.container()

                with detail_col:
                    st.markdown(
                        f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                        f'<span style="color:var(--text);font-weight:700;font-size:1rem">{issue["issue_title"]}</span>'
                        f'<span style="color:{sc};font-size:0.8rem;font-weight:700">● {issue["severity"]}</span></div>'
                        f'<p style="color:var(--text-muted);font-size:0.85rem;margin:4px 0">{issue["description"][:140]}</p>'
                        f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
                        f'<span style="color:var(--text-dim);font-size:0.8rem">🙋 {issue["reporter"]}</span>'
                        f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]}</span>'
                        f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                        f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]}</span>'
                        f'<span style="color:{status_color};font-size:0.8rem;font-weight:600">{status_icon} {status_txt}</span>'
                        f'</div></div>', unsafe_allow_html=True)

                already = issue["id"] in st.session_state.upvoted_ids
                col_u, col_c = st.columns([1, 4])
                with col_u:
                    if already:
                        st.button(f"👍 {issue['upvotes']}", key=f"feed_up_{issue['id']}",
                                  disabled=True, use_container_width=True)
                    else:
                        if st.button(f"👍 {issue['upvotes']}", key=f"feed_up_{issue['id']}",
                                     use_container_width=True):
                            upvote_issue(issue["id"])
                            st.session_state.upvoted_ids.add(issue["id"])
                            st.rerun()

    with tab1:
        # Reporter details front & center (synced via session_state)
        st.markdown('<div class="step"><div class="step-dot">1</div>'
                    '<div class="step-text">Tell us who you are & where the issue is</div></div>',
                    unsafe_allow_html=True)

        # Init persistent values + a version counter for the location widget key.
        # Bumping the version gives the widget a fresh key, which lets GPS prefill it.
        if "loc_value" not in st.session_state:
            st.session_state.loc_value = ""
        if "loc_key_version" not in st.session_state:
            st.session_state.loc_key_version = 0

        # ── Process GPS FIRST (before the text widget is created) ──
        gps_msg = None
        if _HAS_GPS:
            st.markdown('<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">'
                        '<span style="color:var(--text);font-weight:600;font-size:0.92rem">'
                        '📍 Auto-detect my location</span>'
                        '<span style="color:var(--text-dim);font-size:0.82rem">'
                        '— tap the pin, or just type below</span></div>',
                        unsafe_allow_html=True)
            gps = streamlit_geolocation()
            if gps and gps.get("latitude") and gps.get("longitude"):
                glat, glon = gps["latitude"], gps["longitude"]
                coord_key = f"{glat:.5f},{glon:.5f}"
                if st.session_state.get("last_gps_coord") != coord_key:
                    st.session_state.last_gps_coord = coord_key
                    if in_ncr(glat, glon):
                        addr = reverse_geocode(glat, glon)
                        short = (", ".join(addr.split(",")[:3]) if addr
                                 else f"{glat:.4f}, {glon:.4f}")
                        st.session_state.loc_value = short
                        st.session_state.loc_key_version += 1  # fresh key -> prefill works
                        st.rerun()
                    else:
                        gps_msg = ("warn", "📍 You appear to be outside Delhi NCR. "
                                   "NagarSeva AI currently serves Delhi NCR only.")

        d1, d2 = st.columns(2)
        with d1:
            reporter_name = st.text_input(
                "Your name", value=st.session_state.get("reporter_name", ""),
                placeholder="e.g. Abdullah Shamshad", key="inp_name")
        with d2:
            # Versioned key: changes after GPS, so the new value prefills cleanly.
            loc_key = f"inp_loc_{st.session_state.loc_key_version}"
            location = st.text_input(
                "Location", value=st.session_state.loc_value,
                placeholder="e.g. Batla House, Saket, Dwarka (Delhi NCR)", key=loc_key)

        if gps_msg:
            (st.warning if gps_msg[0] == "warn" else st.info)(gps_msg[1])

        # Mobile number — used to track complaints later
        mobile = st.text_input(
            "📱 Mobile number", value=st.session_state.get("reporter_mobile", ""),
            placeholder="10-digit mobile number (to track your complaint)",
            max_chars=10, key="inp_mobile")
        st.session_state.reporter_mobile = mobile

        # Keep canonical copies for other tabs
        st.session_state.loc_value = location
        st.session_state.reporter_location = location
        st.session_state.reporter_name = reporter_name


        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1], gap="large")
        with col1:
            st.markdown('<div class="step"><div class="step-dot">2</div>'
                        '<div class="step-text">Add photo(s) of the issue</div></div>',
                        unsafe_allow_html=True)
            # Upload one or more images, OR take a photo with the camera
            up_tab, cam_tab = st.tabs(["📁 Upload", "📷 Take Photo"])
            with up_tab:
                file_ups = st.file_uploader(
                    "upload", type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True, label_visibility="collapsed")
            with cam_tab:
                cam_up = st.camera_input("Take a photo", label_visibility="collapsed")

            # Build the list of images (camera first, then uploads)
            all_images = []
            if cam_up is not None:
                all_images.append(cam_up)
            if file_ups:
                all_images.extend(file_ups)

            # The first image is the one the AI analyzes; the rest are extra proof
            uploaded = all_images[0] if all_images else None

            if all_images:
                st.caption(f"📸 {len(all_images)} photo(s) added"
                           + (" — first one is used for AI analysis" if len(all_images) > 1 else ""))
                # Show thumbnails in a row
                thumb_cols = st.columns(min(len(all_images), 4))
                for idx, img in enumerate(all_images[:4]):
                    with thumb_cols[idx]:
                        st.image(Image.open(img), use_column_width=True)
                if len(all_images) > 4:
                    st.caption(f"+ {len(all_images) - 4} more")
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("🚀 Analyze with AI", use_container_width=True, type="primary")

        with col2:
            if not st.session_state.result:
                name_ok = bool(reporter_name and reporter_name.strip())
                loc_ok = bool(location and location.strip())
                mobile_ok = bool(mobile and mobile.strip().isdigit() and len(mobile.strip()) == 10)
                photo_ok = uploaded is not None

                def check_row(ok, label):
                    icon = "✅" if ok else "⭕"
                    color = "var(--success)" if ok else "var(--text-dim)"
                    return (f'<div class="drow"><span>{icon}</span>'
                            f'<span class="dval" style="color:{color}">{label}</span></div>')

                st.markdown(
                    '<div class="card" style="min-height:340px"><h3>Before you analyze</h3>'
                    '<p style="color:var(--text-muted);font-size:0.88rem">Complete these so '
                    'your complaint can be routed, signed, and tracked correctly:</p>'
                    + check_row(name_ok, "Your name")
                    + check_row(loc_ok, "Location (Delhi NCR)")
                    + check_row(mobile_ok, "Mobile number (10-digit)")
                    + check_row(photo_ok, "Photo added")
                    + '<p style="color:var(--text-dim);font-size:0.82rem;margin-top:12px">'
                    '🤖 Gemini Vision detects the issue, rejects spam/irrelevant photos, scores '
                    'severity, finds duplicates, and drafts your complaint email.</p></div>',
                    unsafe_allow_html=True)

        if analyze_btn:
            missing = []
            if not (reporter_name and reporter_name.strip()):
                missing.append("your name")
            if not (location and location.strip()):
                missing.append("location")
            if not (mobile and mobile.strip()):
                missing.append("mobile number")
            if uploaded is None:
                missing.append("a photo")
            if missing:
                st.warning("⚠️ Please fill in " + ", ".join(missing) +
                           " above before analyzing 👆")
                st.stop()

            # Mobile must be a valid 10-digit number
            if not (mobile.strip().isdigit() and len(mobile.strip()) == 10):
                st.error("📱 Please enter a valid 10-digit mobile number.")
                st.stop()

            # Validate the location is real + specific (not "Jupiter" or just "Mumbai")
            with st.spinner("📍 Verifying location..."):
                loc_check = validate_location(location)
            if not loc_check["ok"]:
                st.error(f"📍 {loc_check['message']}")
                st.stop()

            image = Image.open(uploaded)
            steps = ["🔍 Scanning your photo... (our AI is working hard, promise 😎)",
                     "🛡️ Checking it's a real civic issue...",
                     "🏷️ Figuring out what's broken...",
                     "📊 Crunching the impact numbers...",
                     "🗣️ Cooking up some desi gyaan... 🍵"]
            prog = st.progress(0); status = st.empty()
            for i, s in enumerate(steps):
                status.markdown(f'<p style="color:var(--primary)">{s}</p>', unsafe_allow_html=True)
                prog.progress(int((i + 1) * 100 / len(steps)))

            initial = {"image": image, "is_civic_issue": False, "confidence": 0,
                       "visual_severity": "Medium",
                       "rejection_reason": "", "issue_title": "", "description": "",
                       "location_hints": "", "category": "", "severity": "",
                       "severity_score": 0, "department": "", "urgency": "",
                       "affected_people": 0, "impact_score": 0, "public_safety": 0,
                       "health_risk": 0, "economic_impact": 0, "inconvenience": 0,
                       "environmental": 0, "escalation_needed": False,
                       "hinglish_summary": "", "error": ""}
            result = nagarseva_graph.invoke(initial)
            prog.empty(); status.empty()

            st.session_state.result = result
            st.session_state.issue_saved = False
            st.session_state.email = None
            st.session_state.whatsapp = None
            st.session_state.dup_info = None

            if result.get("error") and not result.get("is_civic_issue"):
                st.error(f"❌ {result['error']}")
            elif not result.get("is_civic_issue"):
                reason = result.get("rejection_reason") or "This doesn't look like a civic issue."
                st.warning(f"🚫 {reason}\n\nPlease upload a clear photo of a real civic problem — "
                           "pothole, garbage, broken streetlight, water leak, etc.")
                st.session_state.result = None
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
                conf = r.get("confidence", 0)
                st.markdown(
                    f'<div class="card"><h3>{r["issue_title"]}</h3><p>{r["description"]}</p>'
                    f'<div class="drow"><span class="dlabel">📍 Location</span><span class="dval">{location or r["location_hints"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">🏷️ Category</span><span class="dval">{r["category"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">🏢 Department</span><span class="dval"><span class="chip">{r["department"]}</span></span></div>'
                    f'<div class="drow"><span class="dlabel">⏰ Urgency</span><span class="dval">{r["urgency"]}</span></div>'
                    f'<div class="drow"><span class="dlabel">👥 Affected</span><span class="dval">~{r["affected_people"]} residents</span></div>'
                    f'<div class="drow"><span class="dlabel">🎯 AI Confidence</span><span class="dval">{conf}%</span></div>'
                    f'<div class="drow"><span class="dlabel">🚨 Escalation</span><span class="dval">{esc}</span></div></div>',
                    unsafe_allow_html=True)

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
                            # Geocode the location (Delhi area → coordinates)
                            coords = geocode_location(location or r["location_hints"])
                            lat, lon = (coords if coords else (None, None))
                            # Save ALL uploaded images to disk (first is primary)
                            saved_paths = []
                            try:
                                for img in all_images:
                                    ext = (img.name.split(".")[-1].lower()
                                           if getattr(img, "name", None) else "png")
                                    p = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{ext}")
                                    Image.open(img).convert("RGB").save(p)
                                    saved_paths.append(p)
                            except Exception as e:
                                print("IMAGE SAVE ERROR:", str(e))
                            # Store as comma-separated paths (primary first)
                            img_path = ",".join(saved_paths) if saved_paths else None
                            save_issue({
                                "issue_title": r["issue_title"], "category": r["category"],
                                "severity": r["severity"], "severity_score": r["severity_score"],
                                "department": r["department"], "description": r["description"],
                                "location": location or r["location_hints"],
                                "reporter": reporter_name or "Anonymous",
                                "mobile": mobile or "",
                                "affected_people": r["affected_people"],
                                "impact_score": r["impact_score"],
                                "lat": lat, "lon": lon, "image_path": img_path})
                        st.session_state.issue_saved = True
                        st.rerun()
                else:
                    st.success("✅ Saved!")
            with a2:
                if st.button("📧 Email", use_container_width=True):
                    with st.spinner("Drafting your complaint email..."):
                        st.session_state.email = generate_email(
                            issue_title=r["issue_title"], description=r["description"],
                            location=location or r["location_hints"], severity=r["severity"],
                            department=r["department"], name=reporter_name or "Concerned Citizen",
                            llm=text_llm)
            with a3:
                if st.button("📱 WhatsApp", use_container_width=True):
                    st.session_state.whatsapp = build_whatsapp_message(r, location)
            with a4:
                if st.button("🔄 New", use_container_width=True):
                    for k in ["result", "issue_saved", "email", "whatsapp", "dup_info"]:
                        st.session_state[k] = None
                    st.session_state.issue_saved = False
                    st.rerun()

            if st.session_state.email:
                em = st.session_state.email
                st.markdown('<div class="highlight"><div class="highlight-label">📧 Your Complaint Email '
                            '(edit anything before sending)</div></div>', unsafe_allow_html=True)
                to_addr = st.text_input("To", value=em["to"], key="email_to")
                subject = st.text_input("Subject", value=em["subject"], key="email_subject")
                body = st.text_area("Message", value=em["body"], height=260, key="email_body")
                mailto = build_mailto(to_addr, subject, body)
                c_send, c_copy = st.columns([1, 1])
                with c_send:
                    st.markdown(
                        f'<a href="{mailto}" target="_blank" '
                        f'style="display:block;text-align:center;background:linear-gradient(135deg,'
                        f'var(--primary),var(--primary-hover));color:#fff;padding:0.65rem;'
                        f'border-radius:12px;font-weight:600;text-decoration:none">'
                        f'📨 Open in Email App</a>', unsafe_allow_html=True)
                with c_copy:
                    st.download_button("⬇️ Save as .txt",
                                       f"To: {to_addr}\nSubject: {subject}\n\n{body}",
                                       file_name=f"complaint_{datetime.now().strftime('%Y%m%d')}.txt",
                                       use_container_width=True)
                st.caption("💡 'Open in Email App' launches Gmail / your mail app pre-filled. "
                           "Just review and hit send!")

            if st.session_state.whatsapp:
                st.markdown('<div class="highlight"><div class="highlight-label">📱 WhatsApp Message '
                            '(edit before sharing)</div></div>', unsafe_allow_html=True)
                wa_text = st.text_area("WhatsApp message", value=st.session_state.whatsapp,
                                       height=200, key="wa_edit", label_visibility="collapsed")
                import urllib.parse as _up
                wa_link = f"https://wa.me/?text={_up.quote(wa_text)}"
                st.markdown(
                    f'<a href="{wa_link}" target="_blank" '
                    f'style="display:inline-block;background:#25D366;color:#fff;padding:0.6rem 1.4rem;'
                    f'border-radius:12px;font-weight:600;text-decoration:none">📲 Share on WhatsApp</a>',
                    unsafe_allow_html=True)

    with tab_dash:
        render_dashboard()

    with tab_insights:
        render_insights()

    with tab_hist:
        st.markdown("### 📋 Track My Complaints")
        st.markdown('<p style="color:var(--text-muted)">Enter the mobile number you used while '
                    "reporting to see all your complaints and track their resolution.</p>",
                    unsafe_allow_html=True)

        # Mobile lookup — prefilled from whatever they typed on Report tab
        lookup_mobile = st.text_input(
            "📱 Mobile number", value=st.session_state.get("reporter_mobile", ""),
            placeholder="Enter your 10-digit mobile number", max_chars=10,
            key="myreports_mobile")
        if lookup_mobile:
            st.session_state.reporter_mobile = lookup_mobile

        my_mobile = (lookup_mobile or "").strip()
        if not my_mobile:
            st.markdown('<div class="empty"><div class="empty-icon">📱</div>'
                        '<div class="empty-text">Enter your mobile number above to track your complaints.</div></div>',
                        unsafe_allow_html=True)
            issues = []
        elif not (my_mobile.isdigit() and len(my_mobile) == 10):
            st.warning("📱 Please enter a valid 10-digit mobile number.")
            issues = []
        else:
            issues = get_issues_by_mobile(my_mobile)
            st.markdown(f'<p style="color:var(--text-dim);font-size:0.85rem">Showing complaints from '
                        f"<b>{my_mobile}</b> ({len(issues)} found).</p>",
                        unsafe_allow_html=True)
        if my_mobile and (my_mobile.isdigit() and len(my_mobile) == 10) and not issues:
            st.markdown('<div class="empty"><div class="empty-icon">📋</div>'
                        '<div class="empty-text">No complaints found for this number yet. '
                        "Head to <b>Report Issue</b> to file your first one!</div></div>",
                        unsafe_allow_html=True)
        else:
            for issue in issues:
                issue = dict(issue)
                sc = SEVERITY_COLORS.get(issue["severity"], "#888")
                resolved = issue["status"] == "Resolved"
                verif = issue.get("verification", "NA")
                status_color = T["success"] if resolved else T["warning"]
                status_icon = "✅" if resolved else "⏳"

                # Verification badge
                vbadge = ""
                if verif == "Confirmed":
                    vbadge = f'<span style="color:{T["success"]};font-size:0.8rem;font-weight:600">✅ Citizen Confirmed</span>'
                elif verif == "Reopened":
                    vbadge = f'<span style="color:{T["danger"]};font-size:0.8rem;font-weight:600">🔄 Reopened by citizen</span>'
                elif verif == "Pending":
                    vbadge = f'<span style="color:{T["accent"]};font-size:0.8rem;font-weight:600">❓ Awaiting your verification</span>'

                st.markdown(
                    f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                    f'<span style="color:var(--text);font-weight:700;font-size:1rem">{issue["issue_title"]}</span>'
                    f'<span style="color:{sc};font-size:0.8rem;font-weight:700">● {issue["severity"]}</span></div>'
                    f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">🏢 {issue["department"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]}</span>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">👍 {issue["upvotes"]}</span>'
                    f'<span style="color:{status_color};font-size:0.8rem;font-weight:600">{status_icon} {issue["status"]}</span>'
                    f'{vbadge}</div></div>', unsafe_allow_html=True)

                cols = st.columns([1, 1, 1, 2])
                # Upvote (once per session)
                with cols[0]:
                    already = issue["id"] in st.session_state.upvoted_ids
                    if already:
                        st.button("✓ Upvoted", key=f"up_{issue['id']}", disabled=True, use_container_width=True)
                    else:
                        if st.button("👍 Upvote", key=f"up_{issue['id']}", use_container_width=True):
                            upvote_issue(issue["id"])
                            st.session_state.upvoted_ids.add(issue["id"])
                            st.rerun()

                # Verification buttons — only when officer marked Resolved & awaiting
                if verif == "Pending":
                    with cols[1]:
                        if st.button("✅ Fixed!", key=f"conf_{issue['id']}", use_container_width=True):
                            confirm_resolution(issue["id"])
                            st.rerun()
                    with cols[2]:
                        if st.button("❌ Not fixed", key=f"reopen_{issue['id']}", use_container_width=True):
                            reopen_issue(issue["id"])
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# OFFICER VIEW
# ══════════════════════════════════════════════════════════════════════════════
else:
    with tab_review:
        dept = st.session_state.officer_dept
        st.markdown(f"### 🛠️ Resolve {dept} Issues")
        st.markdown(f'<p style="color:var(--text-muted)">You see only <b>{dept}</b> issues, '
                    "auto-routed here by the AI. Mark resolved once fixed — citizens then verify "
                    "whether it was actually fixed.</p>", unsafe_allow_html=True)

        issues = get_issues_by_department(dept)
        pending = [i for i in issues if i["status"] == "Pending"]
        resolved = [i for i in issues if i["status"] == "Resolved"]

        st.markdown(f"#### ⏳ Pending ({len(pending)})")
        if not pending:
            st.markdown('<div class="empty"><div class="empty-icon">✅</div>'
                        f'<div class="empty-text">No pending {dept} issues. Great work!</div></div>',
                        unsafe_allow_html=True)
        for issue in pending:
            sc = SEVERITY_COLORS.get(issue["severity"], "#888")
            reopened_flag = ('<span style="color:var(--danger);font-size:0.78rem;font-weight:700">'
                             '🔄 Previously reopened by citizen</span>'
                             if issue.get("verification") == "Reopened" else "")
            st.markdown(
                f'<div class="hist"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<span style="color:var(--text);font-weight:700;font-size:1rem">{issue["issue_title"]}</span>'
                f'<span style="color:{sc};font-size:0.8rem;font-weight:700">● {issue["severity"]} ({issue["severity_score"]}/10)</span></div>'
                f'<p style="color:var(--text-muted);font-size:0.85rem;margin:4px 0">{issue["description"]}</p>'
                f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
                f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👥 {issue["affected_people"]} affected</span>'
                f'<span style="color:var(--text-dim);font-size:0.8rem">👍 {issue["upvotes"]} upvotes</span>'
                f'{reopened_flag}</div></div>', unsafe_allow_html=True)
            if st.button("✅ Mark Resolved", key=f"res_{issue['id']}"):
                resolve_issue(issue["id"])
                st.rerun()

        if resolved:
            st.markdown(f"#### ✅ Resolved — awaiting / done verification ({len(resolved)})")
            for issue in resolved:
                verif = issue.get("verification", "Pending")
                vtxt = {"Pending": ("var(--accent)", "❓ Awaiting citizen verification"),
                        "Confirmed": ("var(--success)", "✅ Citizen confirmed fixed")}.get(
                            verif, ("var(--text-dim)", verif))
                st.markdown(
                    f'<div class="hist" style="opacity:0.85">'
                    f'<span style="color:var(--text);font-weight:700">{issue["issue_title"]}</span><br>'
                    f'<span style="color:var(--text-dim);font-size:0.8rem">📍 {issue["location"]}</span> · '
                    f'<span style="color:{vtxt[0]};font-size:0.8rem;font-weight:600">{vtxt[1]}</span>'
                    f'</div>', unsafe_allow_html=True)

    with tab_dash:
        render_dashboard(dept_filter=st.session_state.officer_dept)

    with tab_insights:
        render_insights()