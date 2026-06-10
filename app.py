import streamlit as st
import sys
import base64
from pathlib import Path

# Force UTF-8 console output so emoji in log prints (📡 ✅ →) don't crash
# with UnicodeEncodeError on Windows' default cp1252 code page.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from mongodb.read_analytics import load_dashboard_data
#  PAGE CONFIG
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="Kayfa Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════
#  GLOBAL CSS
# ══════════════════════════════════════════════════════

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  :root{
    --bg:#0B1120; --bg-2:#0F172A; --surface:#1E293B; --surface-2:#243349;
    --border:#2A3A52; --text:#E2E8F0; --muted:#94A3B8;
    --indigo:#6366F1; --indigo-light:#818CF8; --teal:#2DD4BF; --teal-2:#14BDAC;
    --green:#22C55E; --red:#EF4444; --amber:#F59E0B; --violet:#A78BFA;
  }

  html, body, [class*="css"]{ font-family:'Inter', sans-serif; }
  .stApp{ background:radial-gradient(1200px 600px at 80% -10%, #16204a 0%, var(--bg) 55%); }
  .block-container{ padding-top:2rem; max-width:1400px; }

  /* sidebar */
  section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0F172A 0%,#0B1120 100%);
    border-right:1px solid var(--border);
  }
  section[data-testid="stSidebar"] *{ color:var(--text); }

  /* brand logo card */
  .brand-logo{
    background:#FFFFFF; border-radius:16px; padding:18px 20px;
    display:flex; justify-content:center; align-items:center;
    box-shadow:0 8px 24px rgba(0,0,0,.35); margin-bottom:8px;
  }
  .brand-logo img{ width:100%; max-width:170px; height:auto; }
  .brand-sub{
    text-align:center; color:var(--muted) !important; font-size:.74rem;
    letter-spacing:.14em; text-transform:uppercase; margin:2px 0 4px; font-weight:600;
  }

  /* sidebar stat chips */
  .stat-chip{
    display:flex; justify-content:space-between; align-items:center;
    background:var(--surface); border:1px solid var(--border);
    border-radius:10px; padding:10px 14px; margin:6px 0; font-size:.9rem;
  }
  .stat-chip .v{ font-weight:700; color:var(--indigo-light) !important; }
  .stat-chip.risk .v{ color:var(--amber) !important; }

  /* radio nav */
  section[data-testid="stSidebar"] div[role="radiogroup"] label{
    border-radius:10px; padding:7px 12px; margin:2px 0;
    border:1px solid transparent; transition:all .15s ease;
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{
    background:var(--surface); border-color:var(--border);
  }

  /* KPI cards */
  .kpi-card{
    position:relative; overflow:hidden;
    background:linear-gradient(160deg,var(--surface) 0%,var(--surface-2) 100%);
    border:1px solid var(--border); border-radius:16px; padding:20px 22px;
    margin-bottom:10px; transition:transform .18s ease, box-shadow .18s ease;
  }
  .kpi-card:hover{ transform:translateY(-3px); box-shadow:0 12px 30px rgba(0,0,0,.35); }
  .kpi-card::before{
    content:''; position:absolute; top:0; left:0; height:100%; width:4px;
    background:linear-gradient(180deg,var(--indigo),var(--teal));
  }
  .kpi-value{
    font-size:2rem; font-weight:800;
    background:linear-gradient(90deg,var(--indigo-light),var(--teal));
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
  }
  .kpi-label{ font-size:.82rem; color:var(--muted); margin-top:6px; font-weight:500; letter-spacing:.02em; }
  .kpi-delta{ font-size:.78rem; margin-top:8px; font-weight:600; }
  .kpi-up{ color:var(--green); }
  .kpi-down{ color:var(--red); }

  /* insight cards */
  .insight-card{
    background:var(--surface); border:1px solid var(--border);
    border-left:4px solid var(--amber); border-radius:12px;
    padding:16px 20px; margin:10px 0; line-height:1.55;
    color:#FFFFFF !important;
  }
  .insight-card, .insight-card *{ color:#FFFFFF !important; }
  .insight-card strong{ display:inline-block; margin-bottom:4px; letter-spacing:.03em; font-size:.8rem; }
  .finding-card  { border-left-color:var(--red); }
  .action-card   { border-left-color:var(--green); }
  .solution-card { border-left-color:var(--violet); }

  /* page header */
  .page-header{
    background:linear-gradient(120deg,var(--indigo) 0%,#4F46E5 45%,var(--teal-2) 100%);
    border-radius:18px; padding:28px 34px; margin-bottom:26px;
    box-shadow:0 10px 30px rgba(79,70,229,.25);
  }
  .page-header h1{ color:#fff !important; margin:0; font-size:1.7rem; font-weight:800; letter-spacing:-.01em; }
  .page-header p { color:rgba(255,255,255,.85); margin:8px 0 0; font-size:.98rem; }

  /* misc */
  [data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:12px; }

  /* expanders (e.g. 90-Day Action Plan on the Final Solution page) */
  [data-testid="stExpander"]{
    border:1px solid var(--border) !important; border-radius:12px !important;
    background:var(--surface); margin-bottom:10px; overflow:hidden;
  }
  [data-testid="stExpander"] summary,
  [data-testid="stExpander"] summary p{
    color:var(--indigo-light) !important; font-weight:700 !important; font-size:.95rem;
  }
  [data-testid="stExpander"] summary svg{ fill:var(--indigo-light) !important; }
  [data-testid="stExpander"] [data-testid="stExpanderDetails"],
  [data-testid="stExpander"] [data-testid="stExpanderDetails"] *{
    color:var(--text) !important;
  }

  h2,h3{ color:var(--text) !important; font-weight:700; }
  hr{ border-color:var(--border); }
  #MainMenu, footer{ visibility:hidden; }
  header[data-testid="stHeader"]{ background:transparent; }

  ::-webkit-scrollbar{ width:9px; height:9px; }
  ::-webkit-scrollbar-thumb{ background:var(--border); border-radius:6px; }
  ::-webkit-scrollbar-thumb:hover{ background:#374a66; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  LOAD DATA (once per session)
# ══════════════════════════════════════════════════════

@st.cache_resource(show_spinner="📡 Connecting to MongoDB Atlas...")
def get_data():
    return load_dashboard_data()

@st.cache_data
def get_logo_b64():
    p = Path(__file__).resolve().parent / "logo.jpg"
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

DATA = get_data()

# ══════════════════════════════════════════════════════
#  HELPER COMPONENTS  (injected into every page's render())
# ══════════════════════════════════════════════════════

def page_header(title: str, description: str):
    st.markdown(f"""
    <div class="page-header">
      <h1>{title}</h1>
      <p>{description}</p>
    </div>""", unsafe_allow_html=True)

def kpi_card(col, value, label, delta=None, delta_up=True):
    delta_html = ""
    if delta:
        cls = "kpi-up" if delta_up else "kpi-down"
        arrow = "▲" if delta_up else "▼"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {delta}</div>'
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)

def insight_card(text: str, kind: str = "insight"):
    icons = {
        "insight":  "💡 KEY INSIGHT",
        "finding":  "⚠️ CRITICAL FINDING",
        "action":   "✅ RECOMMENDED ACTION",
        "solution": "🚀 SOLUTION",
    }
    cls_map = {
        "insight":  "insight-card",
        "finding":  "insight-card finding-card",
        "action":   "insight-card action-card",
        "solution": "insight-card solution-card",
    }
    st.markdown(f"""
    <div class="{cls_map[kind]}">
      <strong>{icons[kind]}</strong><br>{text}
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  PAGE REGISTRY  →  Streamlit native multipage navigation
# ══════════════════════════════════════════════════════
import importlib

def _make_page(page_key: str):
    """Wrap a page module's render() into a zero-arg callable for st.Page,
    injecting the shared DATA and UI helper components."""
    def _run():
        module = importlib.import_module(f"src.dashboard.page_{page_key}")
        module.render(DATA, page_header, kpi_card, insight_card)
    _run.__name__ = f"page_{page_key}"
    return _run

# key, title, icon  — grouped into sidebar sections
NAV = {
    "Overview": [
        ("home", "Home", "🏠"),
    ],
    "Analyses": [
        ("q1",  "Q1 · Attendance",           "📈"),
        ("q2",  "Q2 · Assessment",           "📝"),
        ("q3",  "Q3 · Course Performance",   "📚"),
        ("q4",  "Q4 · Attendance vs Grades", "🔗"),
        ("q5",  "Q5 · Engagement vs Perf.",  "⚡"),
        ("q6",  "Q6 · Concept Failures",     "❌"),
        ("q7",  "Q7 · Concept Trends",       "📉"),
        ("q8",  "Q8 · Submission Behaviour", "⏱️"),
        ("q9",  "Q9 · Cohort Trends",        "📅"),
        ("q10", "Q10 · Age Analysis",        "🎂"),
        ("q11", "Q11 · Segmentation",        "🧩"),
        ("q12", "Q12 · Group Size",          "📏"),
        ("q13", "Q13 · Group Merge",         "🔀"),
        ("q14", "Q14 · At-Risk Students",    "🚨"),
        ("q15", "Q15 · Group Trends",        "📊"),
    ],
    "Summary": [
        ("final", "Final Solution", "🚀"),
    ],
}

_sections = {}
_first = True
for _section, _items in NAV.items():
    _pages = []
    for _key, _title, _icon in _items:
        _pages.append(st.Page(
            _make_page(_key),
            title=_title,
            icon=_icon,
            url_path=_key,
            default=_first,
        ))
        _first = False
    _sections[_section] = _pages

# ── Sidebar: brand logo (rendered above the nav links) ──
with st.sidebar:
    _logo = get_logo_b64()
    if _logo:
        st.markdown(
            f'<div class="brand-logo">'
            f'<img src="data:image/jpeg;base64,{_logo}" alt="Kayfa"/></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="brand-logo">'
            '<h2 style="color:#4F46E5;margin:0;">Kayfa · كيف</h2></div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="brand-sub">Analytics Dashboard</div>',
                unsafe_allow_html=True)

# ── Native multipage navigation (renders the page links in the sidebar) ──
pg = st.navigation(_sections, position="sidebar")

# ── Sidebar: platform stats + footer (rendered below the nav links) ──
with st.sidebar:
    st.markdown("---")
    s = DATA.get("summary", {})
    st.markdown(
        f'<div class="stat-chip"><span>Students</span>'
        f'<span class="v">{s.get("total_students", "—")}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-chip"><span>Groups</span>'
        f'<span class="v">{s.get("total_groups", "—")}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-chip risk"><span>At-Risk</span>'
        f'<span class="v">{s.get("total_at_risk", "—")}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("Kayfa — كيف · AI & Data Analytics Internship · Month 1 · Week 2")

# ══════════════════════════════════════════════════════
#  RENDER SELECTED PAGE
# ══════════════════════════════════════════════════════
pg.run()
