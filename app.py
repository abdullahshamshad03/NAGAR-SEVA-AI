import streamlit as st
from PIL import Image
from agent import nagarseva_graph
from database import init_db, save_issue, get_stats, get_all_issues
from modules.letter_gen import generate_letter
from datetime import datetime
import plotly.graph_objects as go

# ─── Init ─────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="NagarSeva AI",
    page_icon="🏙️",
    layout="wide"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #1a1a2e, #0f3460);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 2rem;
        color: white;
    }
    .hero h1 { font-size: 2.5rem; margin: 0; color: white; }
    .hero p { color: rgba(255,255,255,0.7); margin: 0.5rem 0 0; }
    
    .metric-card {
        background: #1e1e2e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card .val { 
        font-size: 2rem; 
        font-weight: 800;
        color: white;
    }
    .metric-card .lbl { 
        font-size: 0.75rem; 
        color: #aaa; 
        text-transform: uppercase; 
    }
    
    .result-card {
        background: #1e1e2e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        color: #eee;
    }
    .result-card h3 { color: white; }
    .result-card p { color: #ccc; }
    .result-card b { color: #fff; }

    .hinglish-box {
        background: #2a2a3e;
        border-left: 4px solid #4F46E5;
        border-radius: 8px;
        padding: 1rem;
        font-size: 1rem;
        line-height: 1.6;
        color: #ddd;
    }
</style>
""", unsafe_allow_html=True)

sev_colors = {"Critical": "#FF2D2D", "High": "#FF8C00", "Medium": "#FFD700", "Low": "#32CD32"}
# ─── Session State ────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "issue_saved" not in st.session_state:
    st.session_state.issue_saved = False

# ─── Hero Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🏙️ NagarSeva AI</h1>
    <p>Photo lo → AI sab detect kare → Complaint ready! &nbsp;|&nbsp; Powered by Gemini</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📸 Issue Report", "📊 Dashboard", "📋 Issue History"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📸 Photo Upload karo")
        uploaded = st.file_uploader(
            "Issue ki photo lo",
            type=["jpg", "jpeg", "png", "webp"]
        )
        
        st.markdown("### 📋 Details")
        reporter_name = st.text_input("Tumhara naam", placeholder="Rahul Sharma")
        location = st.text_input("Location", placeholder="Okhla Phase 2, New Delhi")
        
        analyze_btn = st.button("🚀 AI se Analyze Karo!", use_container_width=True)
    
    with col2:
        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption="Uploaded Photo", use_column_width=True)

    # ── Analysis ──────────────────────────────────────────────────────────────
    if analyze_btn and uploaded:
        image = Image.open(uploaded)
        
        with st.spinner("🤖 AI pipeline chal rahi hai... thoda wait karo!"):
            initial_state = {
                "image": image,
                "is_civic_issue": False,
                "issue_title": "",
                "description": "",
                "location_hints": "",
                "category": "",
                "severity": "",
                "severity_score": 0,
                "department": "",
                "urgency": "",
                "affected_people": 0,
                "impact_score": 0,
                "public_safety": 0,
                "health_risk": 0,
                "economic_impact": 0,
                "inconvenience": 0,
                "environmental": 0,
                "escalation_needed": False,
                "hinglish_summary": "",
                "error": ""
            }
            
            result = nagarseva_graph.invoke(initial_state)
            st.session_state.result = result
            st.session_state.issue_saved = False
        
        if result.get("error"):
            st.error(f"Error: {result['error']}")
        elif not result.get("is_civic_issue"):
            st.warning("⚠️ Is photo mein koi civic issue nahi dikh raha! Doosri photo try karo.")
        else:
            st.success("✅ Analysis complete!")

    # ── Results ───────────────────────────────────────────────────────────────
    if st.session_state.result and st.session_state.result.get("is_civic_issue"):
        r = st.session_state.result
        
        st.markdown("---")
        st.markdown("## 📊 Analysis Results")
        
        # Metric cards
        m1, m2, m3, m4 = st.columns(4)
        
        
        sev_color = sev_colors.get(r["severity"], "#888")
        
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val" style="color:{sev_color}">{r['severity']}</div>
                <div class="lbl">Severity</div>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val">{r['severity_score']}/10</div>
                <div class="lbl">Score</div>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val">{r['impact_score']}</div>
                <div class="lbl">Impact</div>
            </div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val">{r['affected_people']}</div>
                <div class="lbl">Affected</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Details + Charts
        left, right = st.columns([1, 1])
        
        with left:
            st.markdown(f"""
            <div class="result-card">
                <h3>{r['issue_title']}</h3>
                <p>{r['description']}</p>
                <hr>
                <b>📍 Location hints:</b> {r['location_hints']}<br>
                <b>🏷️ Category:</b> {r['category']}<br>
                <b>🏢 Department:</b> {r['department']}<br>
                <b>⏰ Urgency:</b> {r['urgency']}<br>
                <b>🚨 Escalation:</b> {"YES ⚠️" if r['escalation_needed'] else "No"}
            </div>
            """, unsafe_allow_html=True)
            
            if r.get("hinglish_summary"):
                st.markdown(f"""
                <div class="result-card">
                    <b>🗣️ Hinglish mein:</b>
                    <div class="hinglish-box" style="margin-top:0.5rem">
                        {r['hinglish_summary']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with right:
            # Radar chart
            categories = ["Public Safety", "Health Risk", "Economic", "Inconvenience", "Environmental"]
            values = [r["public_safety"], r["health_risk"], r["economic_impact"], r["inconvenience"], r["environmental"]]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                fillcolor='rgba(79,70,229,0.15)',
                line=dict(color='#4F46E5', width=2)
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(range=[0, 100])),
                showlegend=False,
                height=300,
                margin=dict(t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # ── Save + Letter ──────────────────────────────────────────────────────
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            if not st.session_state.issue_saved:
                if st.button("💾 Issue Save Karo", use_container_width=True):
                    save_issue({
                        "issue_title": r["issue_title"],
                        "category": r["category"],
                        "severity": r["severity"],
                        "severity_score": r["severity_score"],
                        "department": r["department"],
                        "description": r["description"],
                        "location": location,
                        "affected_people": r["affected_people"]
                    })
                    st.session_state.issue_saved = True
                    st.success("✅ Issue save ho gaya!")
            else:
                st.success("✅ Issue already saved!")
        
        with c2:
            if st.button("📝 Complaint Letter Generate Karo", use_container_width=True):
                with st.spinner("Letter likh raha hoon..."):
                    from modules.letter_gen import generate_letter
                    letter = generate_letter(
                        issue_title=r["issue_title"],
                        description=r["description"],
                        location=location or r["location_hints"],
                        severity=r["severity"],
                        department=r["department"],
                        name=reporter_name or "Concerned Citizen"
                    )
                    st.text_area("Complaint Letter", letter, height=300)
                    st.download_button(
                        "⬇️ Download Letter",
                        letter,
                        file_name="complaint.txt"
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📊 Community Dashboard")
    
    stats = get_stats()
    
    d1, d2, d3 = st.columns(3)
    with d1:
        st.metric("📋 Total Issues", stats["total"])
    with d2:
        st.metric("⏳ Pending", stats["pending"])
    with d3:
        st.metric("✅ Resolved", stats["resolved"])
    
    if stats["by_category"]:
        st.markdown("### Issues by Category")
        cats = [row["category"] for row in stats["by_category"]]
        counts = [row["count"] for row in stats["by_category"]]
        
        fig2 = go.Figure(go.Bar(x=cats, y=counts, marker_color='#4F46E5'))
        fig2.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Abhi koi issue report nahi hua — pehle Tab 1 se report karo!")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📋 Issue History")
    
    issues = get_all_issues()
    
    if not issues:
        st.info("Koi issue nahi mila abhi tak!")
    else:
        for issue in issues:
            issue = dict(issue)
            sev_color = sev_colors.get(issue["severity"], "#888")
            st.markdown(f"""
            <div class="result-card">
                <b>{issue['issue_title']}</b> &nbsp;
                <span style="color:{sev_color}">● {issue['severity']}</span> &nbsp;
                <span style="color:#888;font-size:0.85rem">{issue['created_at']}</span><br>
                <small>🏢 {issue['department']} &nbsp;|&nbsp; 
                       📍 {issue['location']} &nbsp;|&nbsp; 
                       👥 {issue['affected_people']} affected &nbsp;|&nbsp;
                       Status: {issue['status']}</small>
            </div>
            """, unsafe_allow_html=True)