"""
Design token system for NagarSeva AI.
Defines light + dark theme tokens and returns a full CSS string.
Inspired by shadcn-style design tokens (define colors once, reuse everywhere).
"""

# ─── Design Tokens ─────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":            "#0a0b10",
        "bg_elevated":   "#12141c",
        "surface":       "#161922",
        "surface_hover": "#1c2030",
        "border":        "#242838",
        "border_strong": "#323852",
        "text":          "#f1f3f9",
        "text_muted":    "#9aa3b8",
        "text_dim":      "#5a6178",
        "primary":       "#6366f1",
        "primary_hover": "#7c7ff5",
        "primary_soft":  "rgba(99,102,241,0.12)",
        "accent":        "#22d3ee",
        "success":       "#34d399",
        "warning":       "#fbbf24",
        "danger":        "#f87171",
        "critical":      "#fb5252",
        "grad_1":        "#12141c",
        "grad_2":        "#1a1d2e",
        "grad_3":        "#1e2747",
        "chart_bg":      "#12141c",
        "shadow":        "0 4px 24px rgba(0,0,0,0.4)",
        "alert_text":    "#f1f3f9",
    },
    "light": {
        "bg":            "#f7f8fc",
        "bg_elevated":   "#ffffff",
        "surface":       "#ffffff",
        "surface_hover": "#f3f4f9",
        "border":        "#e6e8f0",
        "border_strong": "#d2d6e4",
        "text":          "#11141d",
        "text_muted":    "#5a6178",
        "text_dim":      "#9aa3b8",
        "primary":       "#5b5ef0",
        "primary_hover": "#4a4dde",
        "primary_soft":  "rgba(91,94,240,0.10)",
        "accent":        "#0891b2",
        "success":       "#059669",
        "warning":       "#d97706",
        "danger":        "#dc2626",
        "critical":      "#e11d48",
        "grad_1":        "#eef1fb",
        "grad_2":        "#e4e9f9",
        "grad_3":        "#dbe4ff",
        "chart_bg":      "#ffffff",
        "shadow":        "0 4px 20px rgba(20,30,80,0.08)",
        "alert_text":    "#11141d",    
    },
}

SEVERITY_COLORS = {
    "Critical": "#fb5252",
    "High":     "#ff8c00",
    "Medium":   "#fbbf24",
    "Low":      "#34d399",
}


def get_css(mode: str = "dark") -> str:
    t = THEMES[mode]
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    --bg: {t['bg']};
    --bg-elevated: {t['bg_elevated']};
    --surface: {t['surface']};
    --surface-hover: {t['surface_hover']};
    --border: {t['border']};
    --border-strong: {t['border_strong']};
    --text: {t['text']};
    --text-muted: {t['text_muted']};
    --text-dim: {t['text_dim']};
    --primary: {t['primary']};
    --primary-hover: {t['primary_hover']};
    --primary-soft: {t['primary_soft']};
    --accent: {t['accent']};
    --success: {t['success']};
    --warning: {t['warning']};
    --danger: {t['danger']};
    --shadow: {t['shadow']};
}}

* {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}

/* App background */
[data-testid="stAppViewContainer"] {{ background: {t['bg']}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.main .block-container {{ padding-top: 2rem; max-width: 1200px; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {t['bg_elevated']} !important;
    border-right: 1px solid {t['border']};
}}
[data-testid="stSidebar"] * {{ color: {t['text']} !important; }}

/* ── Sidebar toggle button (shadcn-inspired, visible in both themes) ── */
/* Collapsed-state button (the one shown when sidebar is closed) */
[data-testid="stSidebarCollapsedControl"] {{
    background: {t['surface']} !important;
    border: 1px solid {t['border_strong']} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    padding: 2px !important;
    margin: 8px !important;
    transition: all .15s ease !important;
}}
[data-testid="stSidebarCollapsedControl"]:hover {{
    background: {t['surface_hover']} !important;
    border-color: {t['primary']} !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stSidebarCollapsedControl"] button {{
    background: transparent !important;
    color: {t['text']} !important;
}}
[data-testid="stSidebarCollapsedControl"] svg {{
    fill: {t['text']} !important;
    color: {t['text']} !important;
    width: 22px !important; height: 22px !important;
}}
/* Open-state collapse button (inside the sidebar header) */
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] button {{
    background: {t['surface']} !important;
    border: 1px solid {t['border_strong']} !important;
    border-radius: 8px !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarHeader"] button svg {{
    fill: {t['text']} !important;
    color: {t['text']} !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]:hover {{
    background: {t['surface_hover']} !important;
    border-color: {t['primary']} !important;
}}

/* Generic text color */
.main p, .main span, .main label, .main div {{ color: {t['text']}; }}

/* ── Hero ── */
.hero {{
    background: linear-gradient(135deg, {t['grad_1']} 0%, {t['grad_2']} 50%, {t['grad_3']} 100%);
    border: 1px solid {t['border']};
    border-radius: 24px;
    padding: 2.8rem 2rem;
    text-align: center;
    margin-bottom: 1.8rem;
    box-shadow: {t['shadow']};
    position: relative;
    overflow: hidden;
}}
.hero::after {{
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(circle at 30% 20%, {t['primary_soft']} 0%, transparent 55%);
    pointer-events: none;
}}
.hero-badge {{
    display: inline-block;
    background: {t['primary_soft']};
    border: 1px solid {t['primary']};
    color: {t['primary']};
    padding: 5px 16px;
    border-radius: 30px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}}
.hero-title {{
    font-size: 2.9rem;
    font-weight: 800;
    color: {t['text']};
    margin: 0;
    letter-spacing: -1.5px;
    position: relative;
}}
.hero-title .grad {{
    background: linear-gradient(135deg, {t['primary']}, {t['accent']});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.hero-sub {{
    color: {t['text_muted']};
    font-size: 1.05rem;
    margin: 0.7rem 0 0;
    position: relative;
}}

/* ── Cards ── */
.card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 18px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: border-color .2s, transform .2s;
}}
.card:hover {{ border-color: {t['border_strong']}; }}
.card h3 {{ color: {t['text']}; font-size: 1.25rem; font-weight: 700; margin: 0 0 0.3rem; }}
.card p {{ color: {t['text_muted']}; line-height: 1.7; margin: 0.4rem 0; }}

/* ── Metric cards ── */
.metric {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 18px;
    padding: 1.4rem 1rem;
    text-align: center;
    transition: border-color .2s, transform .2s;
}}
.metric:hover {{ border-color: {t['primary']}; transform: translateY(-2px); }}
.metric-val {{ font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 0.35rem; }}
.metric-lbl {{
    font-size: 0.68rem; color: {t['text_dim']};
    text-transform: uppercase; letter-spacing: 1.2px; font-weight: 700;
}}

/* ── Detail rows ── */
.drow {{
    display: flex; align-items: center; gap: 12px;
    padding: 9px 0; border-bottom: 1px solid {t['border']};
}}
.drow:last-child {{ border-bottom: none; }}
.dlabel {{ color: {t['text_dim']}; min-width: 110px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .6px; font-weight: 600; }}
.dval {{ color: {t['text']}; font-weight: 600; font-size: 0.92rem; }}

/* ── Hinglish / highlight card ── */
.highlight {{
    background: linear-gradient(135deg, {t['primary_soft']}, transparent);
    border: 1px solid {t['primary']};
    border-radius: 18px;
    padding: 1.4rem;
    color: {t['text']};
    font-size: 1rem;
    line-height: 1.8;
}}
.highlight-label {{ color: {t['primary']}; font-weight: 700; margin-bottom: 0.5rem; font-size: 0.9rem; }}

/* ── Chips & badges ── */
.chip {{
    display: inline-block;
    background: {t['primary_soft']};
    border: 1px solid {t['primary']};
    color: {t['primary']};
    padding: 3px 13px; border-radius: 30px;
    font-size: 0.78rem; font-weight: 600;
}}
.badge {{ display: inline-block; padding: 4px 14px; border-radius: 30px; font-size: 0.82rem; font-weight: 700; }}

/* ── Step indicator ── */
.step {{ display: flex; align-items: center; gap: 10px; margin-bottom: 1.2rem; }}
.step-dot {{
    width: 30px; height: 30px; border-radius: 50%;
    background: {t['primary']}; color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem; flex-shrink: 0;
}}
.step-text {{ color: {t['text_muted']}; font-size: 0.92rem; font-weight: 500; }}

/* ── Letter box ── */
.letter {{
    background: {t['bg']};
    border: 1px solid {t['border']};
    border-radius: 14px;
    padding: 1.6rem;
    color: {t['text']};
    font-family: 'Georgia', serif !important;
    font-size: 0.92rem; line-height: 1.9; white-space: pre-wrap;
}}

/* ── Stat (dashboard) ── */
.stat {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 18px; padding: 1.6rem; text-align: center;
}}
.stat-val {{ font-size: 2.8rem; font-weight: 800; line-height: 1; }}
.stat-lbl {{ color: {t['text_dim']}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-top: 0.4rem; }}

/* ── History row ── */
.hist {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 14px; padding: 1.1rem 1.4rem; margin-bottom: 0.7rem;
    transition: border-color .2s;
}}
.hist:hover {{ border-color: {t['primary']}; }}

/* ── Sidebar brand ── */
.brand {{ text-align: center; padding: 0.5rem 0 1rem; }}
.brand-icon {{ font-size: 2.6rem; }}
.brand-name {{ color: {t['text']}; font-size: 1.3rem; font-weight: 800; }}
.brand-tag {{ color: {t['text_dim']}; font-size: 0.72rem; margin-top: 2px; }}

.help-row {{
    display: flex; justify-content: space-between;
    padding: 7px 0; border-bottom: 1px solid {t['border']};
}}
.help-dept {{ color: {t['text_muted']}; font-size: 0.85rem; }}
.help-num {{ color: {t['primary']}; font-weight: 700; font-size: 0.85rem; }}

/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(135deg, {t['primary']}, {t['primary_hover']}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.65rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: transform .15s, box-shadow .15s !important;
    opacity: 1 !important;
}}
.stButton > button p,
.stButton > button span,
.stButton > button div {{
    color: #ffffff !important;
    opacity: 1 !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px {t['primary_soft']} !important;
}}
.stDownloadButton > button {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border_strong']} !important;
    border-radius: 12px !important;
}}

/* ── Tabs (modern pill-style navbar) ── */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 6px !important;
    background: {t['surface']} !important;
    padding: 6px !important;
    border-radius: 14px !important;
    border: 1px solid {t['border']} !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-list"] button {{
    color: {t['text_dim']} !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    border-radius: 10px !important;
    padding: 8px 16px !important;
    border-bottom: none !important;
    transition: all .15s ease !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-list"] button:hover {{
    background: {t['surface_hover']} !important;
    color: {t['text']} !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] {{
    color: #ffffff !important;
    background: linear-gradient(135deg, {t['primary']}, {t['primary_hover']}) !important;
    border-bottom: none !important;
    box-shadow: 0 2px 8px {t['primary_soft']} !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] * {{
    color: #ffffff !important;
}}
/* Hide the default underline highlight bar */
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background: transparent !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    background: transparent !important;
}}

/* ── Inputs ── */
[data-testid="stTextInput"] input {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 10px !important;
}}
[data-testid="stTextInput"] input::placeholder {{ color: {t['text_dim']} !important; }}

/* Password field wrapper + the show/hide eye button (baseweb) */
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stTextInput"] [data-baseweb="base-input"] {{
    background: {t['surface']} !important;
    border-radius: 10px !important;
}}
[data-testid="stTextInput"] [data-baseweb="input"] input {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
}}
/* The eye/reveal icon button on password inputs */
[data-testid="stTextInput"] button,
[data-testid="stTextInput"] [role="button"] {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
}}
[data-testid="stTextInput"] button svg,
[data-testid="stTextInput"] [role="button"] svg {{
    fill: {t['text_muted']} !important;
    color: {t['text_muted']} !important;
}}

/* Widget labels (Your name / Location / Mobile) - keep them clear, no overlap */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {{
    color: {t['text']} !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    opacity: 1 !important;
    margin-bottom: 4px !important;
}}

/* GPS geolocation component (third-party iframe) - remove its black box */
iframe[title*="geolocation"],
iframe[title*="streamlit_geolocation"] {{
    width: 52px !important;
    height: 52px !important;
    border-radius: 14px !important;
    background: transparent !important;
}}
/* The component's wrapper block that carries the dark background */
.stCustomComponentV1,
[class*="stCustomComponent"] {{
    background: transparent !important;
}}
div:has(> iframe[title*="geolocation"]) {{
    background: transparent !important;
    width: 56px !important;
}}

/* ── File uploader ── */
[data-testid="stFileUploader"] {{
    background: {t['surface']};
    border: 2px dashed {t['border_strong']};
    border-radius: 16px; padding: 1rem;
}}
[data-testid="stFileUploader"] * {{ color: {t['text_muted']} !important; }}
/* Inner dropzone area (the dark box) */
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div,
section[data-testid="stFileUploaderDropzone"] {{
    background: {t['bg_elevated']} !important;
    border-radius: 12px !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
    background: {t['surface_hover']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border_strong']} !important;
}}
/* Uploaded file pill */
[data-testid="stFileUploaderFile"] {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
}}
[data-testid="stFileUploaderFile"] * {{ color: {t['text']} !important; }}

/* ── Fix Material-icon text leaking on newer Streamlit (deploy) ── */
/* Force the icon font to render as icons, not raw text like "arrow_right" */
span[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
.material-symbols-rounded,
[data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"] {{
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    font-weight: normal !important;
    font-style: normal !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased !important;
}}
/* If the icon font fails to load, hide the raw fallback text so it doesn't
   overlap labels (better a missing icon than "arrow_right" over text). */
@font-face {{
    font-family: 'Material Symbols Rounded';
    font-style: normal;
    src: local('Material Symbols Rounded');
}}

/* ── Expander (Login as Officer / Emergency SOS) ── */
[data-testid="stExpander"] {{
    background: {t['surface']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] details > summary {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
    font-weight: 600 !important;
    padding: 0.7rem 1rem !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: {t['surface_hover']} !important;
}}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary svg {{
    color: {t['text']} !important;
    fill: {t['text']} !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background: {t['surface']} !important;
}}

/* ── Select boxes (feed filters) ── */
[data-baseweb="select"] > div {{
    background: {t['surface']} !important;
    border-color: {t['border']} !important;
    color: {t['text']} !important;
}}
[data-baseweb="select"] span {{ color: {t['text']} !important; }}
[data-baseweb="popover"] li {{
    background: {t['bg_elevated']} !important;
    color: {t['text']} !important;
}}

/* ── Text area (email body) ── */
[data-testid="stTextArea"] textarea {{
    background: {t['surface']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
}}

/* Empty state */
.empty {{
    text-align: center; padding: 3rem 1rem;
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 18px;
}}
.empty-icon {{ font-size: 3rem; }}
.empty-text {{ color: {t['text_muted']}; margin-top: 1rem; }}

/* ── Alerts (warning / error / info / success) - readable text in both themes ── */
[data-testid="stAlert"] {{
    border-radius: 12px !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] div,
[data-testid="stAlert"] span,
[data-testid="stAlertContentWarning"],
[data-testid="stAlertContentError"],
[data-testid="stAlertContentInfo"],
[data-testid="stAlertContentSuccess"] {{
    color: {t['alert_text']} !important;
}}

/* scrollbar */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: {t['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {t['border_strong']}; border-radius: 10px; }}
</style>
"""