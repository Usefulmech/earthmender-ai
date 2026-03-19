"""
EarthMender AI — Final Application
====================================
Run: streamlit run app.py

Camera fix: st.camera_input is rendered at the TOP LEVEL of the script,
completely outside all tab with-blocks. Streamlit renders all tab content
simultaneously in Python, so any widget inside a tab block always gets
mounted. The only way to truly unmount the camera is to place it outside
all tabs and control it with a session-state flag.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from PIL import Image
from streamlit_folium import st_folium
from streamlit.components.v1 import html as comp_html
from collections import defaultdict

from phase1_detection.detector import PlasticDetector, confidence_band
from phase2_reporting.reporter import (
    load_reports, save_report, resolve_report, reopen_report,
    get_open_reports, get_resolved_reports, get_report_stats,
    get_manual_location,
)
from phase3_map.mapper import build_map, get_hotspots
from phase4_dashboard.dashboard import render_full_dashboard
from phase5_education.educator import render_education_tab

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EarthMender AI", page_icon="🌍",
    layout="wide", initial_sidebar_state="collapsed",
)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
_defs = {
    "logged_in": False, "user_name": "", "user_role": "Citizen",
    "user_initials": "?",
    # which tab the user is visibly on (0-4) — driven by bottom-nav JS
    "cur_tab": 0,
    # detect tab state
    "det_mode": "camera",       # "camera" | "upload"
    "cam_open": False,          # True only when user explicitly opens camera
    "open_cam_from_home": False, # flag set when Home->Report should open camera
    "img_raw": None,            # PIL Image captured/uploaded
    "img_ann": None,            # annotated PIL Image after detection
    "det_dets": [],             # list of detection dicts
    "det_qual": None,           # quality dict
    "det_done": False,          # True after detection ran
    # home
    "show_all": False,
    # GPS
    "gps_lat": "", "gps_lon": "",
}
for k, v in _defs.items():
    if k not in st.session_state:
        st.session_state[k] = v

# If the tab UI changes, we need to keep server state in sync.
# Streamlit doesn't expose the active tab server-side, so we use a tiny component
# that reads the DOM tab state and sends it back via Streamlit.setComponentValue.
_tab_active = st.components.v1.html(
    """
    <script>
    (function(){
      const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
      if(!tabs.length) return;
      const active = Array.from(tabs).findIndex(t=>t.getAttribute('aria-selected')==='true');
      if(active>=0) Streamlit.setComponentValue(active);
      tabs.forEach((t,i)=>{
        t.addEventListener('click',()=>Streamlit.setComponentValue(i));
      });
    })();
    </script>
    """,
    height=1,
    width=1,
)
if _tab_active is not None:
    try:
        st.session_state.cur_tab = int(_tab_active)
    except Exception:
        pass

# ─── JS tab helper ────────────────────────────────────────────────────────────
def _tab_js(idx: int) -> str:
    """Click a tab in the Streamlit tab bar."""
    return (
        f"(function(){{"
        f"var tabs=window.parent.document"
        f".querySelectorAll('[data-baseweb=\"tab\"]');"
        f"if(tabs[{idx}])tabs[{idx}].click();"
        f"}})();"
    )

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

/* Hide Streamlit chrome */
#MainMenu,header,footer,[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"]{display:none!important}

*{box-sizing:border-box;margin:0;padding:0}

html,body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],.main,
[data-testid="stMainBlockContainer"]{
  font-family:'Inter',sans-serif!important;
  background:#080f0a!important;color:#f0f0f0!important;
  padding:0!important;margin:0!important;width:100%!important}

/* Desktop: 480px centre. Mobile: full width */
.block-container{
  padding:0!important;max-width:480px!important;
  margin:0 auto!important;width:100%!important}
@media(max-width:640px){
  .block-container{max-width:100vw!important;margin:0!important}}

/* ── Top bar ── */
.top{background:#1a7a4a;padding:11px 14px 10px;display:flex;
  align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:300}
.av{width:36px;height:36px;border-radius:50%;
  background:rgba(255,255,255,0.2);display:flex;align-items:center;
  justify-content:center;font-size:13px;font-weight:900;color:#fff}
.grt{color:rgba(255,255,255,0.6);font-size:10px}
.usr{color:#fff;font-size:14px;font-weight:900;letter-spacing:-.2px}
.badge{background:rgba(255,255,255,0.13);border-radius:6px;
  padding:3px 8px;font-size:10px;font-weight:800;
  color:rgba(255,255,255,0.75);letter-spacing:.5px}

/* ── Tab bar — icon above bold text ── */
.stTabs [data-baseweb="tab-list"]{
  background:#0c1810!important;
  border-bottom:1px solid rgba(255,255,255,0.07)!important;
  gap:0!important;padding:0!important;display:flex!important;width:100%!important}
.stTabs [data-baseweb="tab"]{
  flex:1!important;display:flex!important;flex-direction:column!important;
  align-items:center!important;justify-content:center!important;
  gap:4px!important;padding:8px 2px 9px!important;
  font-size:10px!important;font-weight:900!important;
  color:#2e3e32!important;letter-spacing:.8px!important;
  text-transform:uppercase!important;
  border-bottom:2.5px solid transparent!important;
  font-family:'Inter',sans-serif!important;min-height:54px!important}
.stTabs [aria-selected="true"]{
  color:#4caf50!important;border-bottom:2.5px solid #4caf50!important;
  background:rgba(76,175,80,0.05)!important}
.stTabs [data-baseweb="tab-panel"]{background:#080f0a!important;padding:0!important}

/* ── Hero ── */
.hero{background:linear-gradient(160deg,#1a7a4a,#0e4828);padding:13px 14px 15px}
.bal{background:rgba(255,255,255,0.09);border-radius:13px;
  padding:12px 14px;border:.5px solid rgba(255,255,255,0.14);margin-bottom:11px}
.bal-lbl{color:rgba(255,255,255,0.55);font-size:9px;margin-bottom:5px;
  text-transform:uppercase;letter-spacing:1px}
.bal-val{color:#fff;font-size:24px;font-weight:900;letter-spacing:-.5px}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.sc{background:rgba(255,255,255,0.09);border-radius:8px;
  padding:8px 4px;text-align:center}
.sv{color:#fff;font-size:15px;font-weight:900}
.sl{color:rgba(255,255,255,0.5);font-size:8px;margin-top:2px;
  text-transform:uppercase;letter-spacing:.5px}

/* ── Page body ── */
.pg{background:#080f0a;padding:0 14px 100px}

/* ── Section headings ── */
.sh{font-size:13px;font-weight:900;color:#eee;letter-spacing:-.1px}

/* ── Alert ── */
.al{background:rgba(255,152,0,.09);border-radius:10px;padding:9px 12px;
  display:flex;align-items:center;gap:8px;
  border:.5px solid rgba(255,152,0,.2);margin:7px 0 5px}
.ald{width:6px;height:6px;border-radius:50%;background:#ff9800;flex-shrink:0}
.alt{font-size:11px;color:#ffcc80;flex:1}

/* ── Report Waste btn ── */
.rw-btn{width:100%;background:#1a7a4a;color:#fff;border:none;
  border-radius:24px;padding:10px 18px;font-size:13px;font-weight:800;
  font-family:'Inter',sans-serif;cursor:pointer;letter-spacing:.1px;
  margin:5px 0 8px;display:block}
.rw-btn:active{background:#145c38}

/* ── Case cards ── */
.cc{background:#111c14;border-radius:11px;padding:11px 13px;
  border:.5px solid rgba(255,255,255,0.05);display:flex;
  align-items:flex-start;gap:10px;margin-bottom:6px}
.cdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:5px}
.ctype{font-size:12px;font-weight:700;color:#eee;line-height:1.3}
.cloc{font-size:10px;color:#444;margin-top:2px}
.cmeta{display:flex;align-items:center;gap:5px;margin-top:5px;flex-wrap:wrap}
.pi{font-size:9px;padding:2px 7px;border-radius:20px;font-weight:800}
.ctm{font-size:9px;color:#2e3e32;margin-left:auto}

/* ── Analytic heatmap ── */
.hm-wrap{background:#111c14;border-radius:13px;
  border:.5px solid rgba(255,255,255,0.05);overflow:hidden}
.hm-hdr{padding:11px 13px 7px;display:flex;align-items:center;
  justify-content:space-between}
.hm-title{font-size:13px;font-weight:900;color:#eee}
.hm-sub{font-size:9px;color:#3a4a3e;margin-top:2px}
.hm-openbtn{font-size:10px;font-weight:800;color:#080f0a;
  background:#4caf50;border:none;border-radius:12px;
  padding:5px 11px;cursor:pointer;font-family:'Inter',sans-serif}
.hm-grid{display:grid;gap:3px;padding:0 13px 10px}
.hm-cell{border-radius:4px;height:26px}
.hm-legend{display:flex;align-items:center;gap:8px;
  padding:0 13px 9px;font-size:9px;color:#3a4a3e}
.hm-legbar{flex:1;height:4px;border-radius:2px;
  background:linear-gradient(90deg,#1a3d22,#2d7a3a,#ffd600,#ff6d00,#c62828)}
.hm-zones{display:flex;gap:4px;padding:0 13px 11px;flex-wrap:wrap}
.hm-zone{background:#182418;border-radius:7px;padding:5px 8px;
  font-size:10px;display:flex;align-items:center;gap:5px;
  border:.5px solid rgba(255,255,255,0.04)}
.hm-zdot{width:6px;height:6px;border-radius:50%;flex-shrink:0}

/* ── Camera/upload zone ── */
.cap{border:2px dashed rgba(76,175,80,.28);border-radius:15px;
  padding:30px 18px;text-align:center;background:#111c14;margin:8px 0}
.cap-t{font-size:13px;font-weight:700;color:#aaa;margin-top:9px}
.cap-s{font-size:10px;color:#3a4a3e;margin-top:3px}

/* ── Detect info tiles ── */
.dtiles{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:7px 0 10px}
.dtile{background:#111c14;border-radius:10px;padding:10px 6px;text-align:center;
  border:.5px solid rgba(255,255,255,0.05)}
.dtile-i{font-size:18px;margin-bottom:3px}
.dtile-l{font-size:8px;color:#444;text-transform:uppercase;letter-spacing:.5px;font-weight:800}

/* ── Results ── */
.res-ok{background:rgba(76,175,80,.09);border-left:3px solid #4caf50;
  padding:11px 13px;border-radius:10px;margin:9px 0;
  color:#a5d6a7;font-size:12px;font-weight:700}
.res-warn{background:rgba(255,152,0,.09);border-left:3px solid #ff9800;
  padding:11px 13px;border-radius:10px;margin:9px 0;color:#ffcc80;font-size:12px}
.tip-box{background:rgba(33,150,243,.07);border-left:3px solid #1565c0;
  padding:10px 12px;border-radius:10px;font-size:11px;color:#ccc;margin:6px 0}

/* ── Confidence pills ── */
.conf-Certain{background:rgba(76,175,80,.16);color:#81c784}
.conf-Likely{background:rgba(255,193,7,.16);color:#ffd54f}
.conf-Possible{background:rgba(158,158,158,.12);color:#888}

/* ── GPS widget ── */
.gps-box{padding:10px 12px;background:rgba(33,150,243,.1);border-radius:9px;
  color:#90caf9;font-size:12px;line-height:1.7;margin-bottom:6px}
.gps-bar{background:rgba(255,255,255,.07);border-radius:3px;height:4px;
  margin:3px 0}
.gps-fill{height:4px;border-radius:3px;background:#4caf50;
  transition:width .4s}

/* ── Streamlit widget overrides ── */
.stButton>button{font-family:'Inter',sans-serif!important;font-weight:800!important;
  border-radius:24px!important;border:none!important;font-size:13px!important}
.stButton>button[kind="primary"]{background:#1a7a4a!important;color:#fff!important}
.stButton>button:not([kind="primary"]){background:#111c14!important;color:#999!important;
  border:.5px solid rgba(255,255,255,0.08)!important}

div[data-testid="stMetric"]{background:#111c14!important;border-radius:11px!important;
  padding:12px!important;border:.5px solid rgba(255,255,255,0.05)!important}
div[data-testid="stMetricLabel"] p{color:#444!important;font-size:9px!important;
  text-transform:uppercase!important;letter-spacing:.5px!important}
div[data-testid="stMetricValue"] div{color:#eee!important;font-size:20px!important;font-weight:900!important}

.stTextInput input,.stTextArea textarea,.stNumberInput input{
  background:#111c14!important;border:.5px solid rgba(255,255,255,0.08)!important;
  border-radius:9px!important;color:#eee!important;padding:9px 12px!important;
  font-family:'Inter',sans-serif!important}
.stTextInput input:focus{border-color:rgba(76,175,80,.4)!important;
  box-shadow:0 0 0 2px rgba(76,175,80,.08)!important}
.stSelectbox>div>div{background:#111c14!important;
  border:.5px solid rgba(255,255,255,0.08)!important;
  color:#eee!important;border-radius:9px!important}
label,[data-testid="stWidgetLabel"] p,.stRadio label p{
  color:#666!important;font-size:11px!important;font-family:'Inter',sans-serif!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#aaa!important}
details,summary{background:#111c14!important;border-radius:10px!important;
  border:.5px solid rgba(255,255,255,0.05)!important;color:#eee!important}
hr{border-color:rgba(255,255,255,0.06)!important;margin:12px 0!important}
.stProgress>div>div>div{background:#1a7a4a!important;border-radius:3px!important}
.stCaption p{color:#3a4a3e!important;font-size:10px!important}
[data-testid="stAlert"]{background:#111c14!important;border-radius:10px!important;
  border:.5px solid rgba(255,255,255,0.05)!important;color:#aaa!important}
[data-testid="stMarkdownContainer"] p{color:#bbb!important;font-size:12px!important}
[data-testid="stTable"] table{background:#111c14!important}
thead tr th{background:#182418!important;color:#555!important;
  font-size:9px!important;text-transform:uppercase!important}
tbody tr td{color:#ccc!important;border-color:rgba(255,255,255,0.03)!important;font-size:11px!important}

/* ── Sub-tabs inside stats ── */
.stTabs .stTabs [data-baseweb="tab-list"]{
  background:#111c14!important;border-radius:9px!important;
  padding:3px!important;gap:3px!important;border:none!important}
.stTabs .stTabs [data-baseweb="tab"]{
  flex:none!important;border-radius:7px!important;min-height:32px!important;
  font-size:10px!important;padding:5px 11px!important;border-bottom:none!important;
  flex-direction:row!important;gap:4px!important;text-transform:none!important;
  letter-spacing:0!important;font-weight:800!important}
.stTabs .stTabs [aria-selected="true"]{
  background:rgba(76,175,80,.13)!important;color:#4caf50!important;
  border-bottom:none!important}

/* ── Fixed bottom nav — mobile only ── */
.bnav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);
  width:100%;max-width:480px;background:#080f0a;
  border-top:.5px solid rgba(255,255,255,0.08);
  z-index:9999;padding-bottom:env(safe-area-inset-bottom);display:none}
@media(max-width:640px){.bnav{display:block!important}}
.bnav-row{display:flex;width:100%;align-items:flex-end}
.bn{flex:1;display:flex;flex-direction:column;align-items:center;
  gap:3px;padding:8px 2px 10px;cursor:pointer;border:none;
  background:transparent;-webkit-tap-highlight-color:transparent}
.bn-ic{width:22px;height:22px;display:block}
.bn-lbl{font-size:8px;font-weight:900;text-transform:uppercase;letter-spacing:.5px;
  font-family:'Inter',sans-serif}
.bn.on .bn-ic{opacity:1!important}
.bn.on .bn-lbl{color:#4caf50!important}
.fab{flex:1;display:flex;flex-direction:column;align-items:center;
  gap:3px;padding:4px 2px 10px;cursor:pointer;border:none;
  background:transparent;-webkit-tap-highlight-color:transparent}
.fab-c{width:44px;height:44px;border-radius:50%;background:#1a7a4a;
  display:flex;align-items:center;justify-content:center;
  margin-top:-8px;border:3px solid #080f0a;
  box-shadow:0 4px 16px rgba(26,122,74,.5)}
.fab-lbl{font-size:8px;color:#4caf50;font-weight:900;
  text-transform:uppercase;letter-spacing:.4px;font-family:'Inter',sans-serif}
.sp{height:68px}

@media(max-width:360px){.sg,.dtiles{grid-template-columns:repeat(2,1fr)}}
</style>
""", unsafe_allow_html=True)

# Keep url query param in sync when user clicks primary tab bar (not just bottom nav)
st.markdown("""
<script>
(function(){
  var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
  tabs.forEach(function(t,i){
    if(!t.dataset.__tabListener){
      t.dataset.__tabListener = "1";
      t.addEventListener("click", function(){
        window.history.replaceState(null,null,'?tab='+i);
      });
    }
  });
})();
</script>
""", unsafe_allow_html=True)

# ─── SVG ICONS ────────────────────────────────────────────────────────────────
_IC = {
    "home":   '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "detect": '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "map":    '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "learn":  '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    "stats":  '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "plus":   '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "cam":    '<svg viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="1.8" stroke-linecap="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
    "upl":    '<svg viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="1.8" stroke-linecap="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>',
}
_T = {"home":0,"detect":1,"map":2,"learn":3,"stats":4}

def ic(k, col="#4caf50"):
    return _IC[k].replace("CLR", col)

def _bn(idx, ik, lbl, cur):
    on  = "on" if idx==cur else ""
    col = "#4caf50" if idx==cur else "#2e3e32"
    sty = f"opacity:{'1' if idx==cur else '0.3'}"
    return (
        f'<button class="bn {on}" onclick="{_tab_js(idx)}">'
        f'<span class="bn-ic" style="{sty}">{ic(ik,col)}</span>'
        f'<span class="bn-lbl" style="color:{col};">{lbl}</span>'
        f'</button>'
    )

WASTE_LABELS = {
    "plastic_bottle":"🍶 Plastic Bottle","water_sachet":"💧 Water Sachet",
    "polythene_bag":"🛍️ Polythene Bag","disposable":"🥤 Disposable",
    "waste_container":"🛢️ Waste Container",
}

# ─── ANALYTIC HEATMAP ─────────────────────────────────────────────────────────
def _heatmap_html(reports, map_tab_idx=2):
    open_reps = [r for r in reports if r.get("status")=="OPEN"]
    if not open_reps:
        return ('<div style="background:#111c14;border-radius:13px;padding:28px;'
                'text-align:center;border:.5px solid rgba(255,255,255,.05);">'
                '<div style="font-size:22px;margin-bottom:6px;">🗺️</div>'
                '<div style="font-size:12px;color:#333;">No active reports yet</div></div>')

    grid = defaultdict(lambda: {"c":0,"h":0,"t":set()})
    for r in open_reps:
        gx  = round(r["latitude"]/0.02)*0.02
        gy  = round(r["longitude"]/0.02)*0.02
        key = (round(gx,3), round(gy,3))
        grid[key]["c"] += 1
        if r.get("severity")=="HIGH": grid[key]["h"] += 1
        for t in r.get("waste_types",[]): grid[key]["t"].add(t)

    mx  = max(z["c"] for z in grid.values()) or 1
    top = sorted(grid.items(), key=lambda x:-x[1]["c"])

    def hcol(c,h,mx):
        i = c/mx
        if h>0 and i>0.5: return f"rgba(198,40,40,{.25+i*.6:.2f})"
        if i>=0.7:         return f"rgba(255,109,0,{.25+i*.5:.2f})"
        if i>=0.4:         return f"rgba(255,214,0,{.2+i*.4:.2f})"
        if i>=0.15:        return f"rgba(100,181,100,{.18+i*.35:.2f})"
        return                    f"rgba(76,175,80,{.1+i*.15:.2f})"

    cols   = 8
    rows_n = max(3, -(-len(top)//cols))
    cells  = ""
    for i in range(cols*rows_n):
        if i < len(top):
            _,(z) = top[i]
            bg = hcol(z["c"],z["h"],mx)
            tt = f"{z['c']} reports"
        else:
            bg = "rgba(255,255,255,.02)"; tt=""
        cells += f'<div class="hm-cell" style="background:{bg};" title="{tt}"></div>'

    ticons={"plastic_bottle":"🍶","water_sachet":"💧","polythene_bag":"🛍️",
            "disposable":"🥤","waste_container":"🛢️"}
    zones=""
    for (lat,lon),z in top[:5]:
        i   = z["c"]/mx
        dc  = "#f44336" if z["h"]>0 else "#ff9800" if i>.5 else "#ffd600" if i>.25 else "#4caf50"
        ics = "".join(ticons.get(t,"♻️") for t in list(z["t"])[:2])
        zones += (f'<div class="hm-zone">'
                  f'<span class="hm-zdot" style="background:{dc};"></span>'
                  f'<span style="color:#777;">{lat:.2f},{lon:.2f}</span>'
                  f'<span>{ics}</span>'
                  f'<span style="color:#2e3e32;">{z["c"]}</span></div>')

    open_js = _tab_js(map_tab_idx)
    return f"""
    <div class="hm-wrap">
      <div class="hm-hdr">
        <div>
          <div class="hm-title">🔥 Pollution Intensity</div>
          <div class="hm-sub">{len(open_reps)} active · grouped by ~2km zone</div>
        </div>
        <button class="hm-openbtn" onclick="{open_js}">Open Live Map →</button>
      </div>
      <div class="hm-grid" style="grid-template-columns:repeat({cols},1fr);">{cells}</div>
      <div class="hm-legend">
        <span>Low</span><div class="hm-legbar"></div><span>High</span>
      </div>
      <div class="hm-zones">{zones}</div>
    </div>"""

# ─── GPS WIDGET ───────────────────────────────────────────────────────────────
def _gps_widget():
    """Inline HTML5 GPS with live accuracy bar. User copies coords into fields."""
    comp_html("""
    <style>
    body{margin:0;font-family:Inter,sans-serif;font-size:12px}
    #gs{padding:9px 11px;background:rgba(33,150,243,.12);border-radius:9px;
        color:#90caf9;line-height:1.7;margin-bottom:6px}
    #gb{display:none;margin-bottom:5px}
    #gbt{font-size:9px;color:#555;margin-bottom:3px}
    #gbt2{background:rgba(255,255,255,.07);border-radius:3px;height:4px}
    #gbf{height:4px;border-radius:3px;background:#4caf50;width:0%;transition:width .4s}
    #gl{font-size:9px;color:#666;margin-top:2px}
    #gc{display:none;background:rgba(76,175,80,.1);border-radius:9px;
        padding:9px 11px;font-size:12px;color:#a5d6a7}
    </style>
    <div id="gs">⏳ Acquiring GPS signal...</div>
    <div id="gb">
      <div id="gbt">Accuracy</div>
      <div id="gbt2"><div id="gbf"></div></div>
      <div id="gl"></div>
    </div>
    <div id="gc"><b id="glat"></b><br><b id="glon"></b></div>
    <script>
    var best=9999;
    function upd(a){
      var f=document.getElementById('gbf'),l=document.getElementById('gl');
      var p=Math.max(0,Math.min(100,100-(a/50*100)));
      f.style.width=p+'%';
      f.style.background=a<=10?'#4caf50':a<=30?'#ff9800':'#f44336';
      l.textContent=(a<=10?'Excellent':a<=30?'Good':'Acquiring')+'  \u00b1'+Math.round(a)+'m';
      document.getElementById('gb').style.display='block';
    }
    function onP(p){
      var la=p.coords.latitude.toFixed(6),lo=p.coords.longitude.toFixed(6),a=p.coords.accuracy;
      if(a<best){
        best=a;
        document.getElementById('glat').textContent='Lat: '+la;
        document.getElementById('glon').textContent='Lon: '+lo;
        document.getElementById('gc').style.display='block';
        var s=document.getElementById('gs');
        s.style.background='rgba(76,175,80,.1)';s.style.color='#a5d6a7';
        s.innerHTML='📍 GPS locked \u2014 copy coordinates below';
        upd(a);
      }
    }
    function onE(e){
      var s=document.getElementById('gs');
      s.style.background='rgba(255,152,0,.1)';s.style.color='#ffcc80';
      s.innerHTML='⚠️ '+(e.code===1?'Permission denied. Use Manual Entry.':'GPS unavailable. Use Manual Entry.');
    }
    if(navigator.geolocation){
      navigator.geolocation.watchPosition(onP,onE,{enableHighAccuracy:true,timeout:15000,maximumAge:0});
    }else{document.getElementById('gs').textContent='❌ GPS not supported. Use Manual Entry.';}
    </script>
    """, height=130)
    c1,c2 = st.columns(2)
    with c1: lat_s = st.text_input("Latitude",  placeholder="e.g. 6.524400", key="gps_lat_inp")
    with c2: lon_s = st.text_input("Longitude", placeholder="e.g. 3.379200", key="gps_lon_inp")
    lat, lon = 6.5244, 3.3792
    if lat_s and lon_s:
        try: lat,lon = float(lat_s),float(lon_s)
        except ValueError: st.warning("⚠️ Invalid coords — Lagos default used.")
    return lat, lon

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def _login():
    st.markdown("""
    <div style="text-align:center;padding:52px 0 26px;
         background:linear-gradient(180deg,rgba(26,122,74,.2),transparent);">
      <div style="font-size:52px;margin-bottom:9px;">🌍</div>
      <div style="font-size:24px;font-weight:900;color:#fff;letter-spacing:-.5px;margin-bottom:5px;">
        EarthMender AI</div>
      <div style="font-size:10px;color:rgba(255,255,255,.35);letter-spacing:2.5px;">
        DETECT · REPORT · LEARN · ACT</div>
    </div>
    """, unsafe_allow_html=True)

    col_l,col_m,col_r = st.columns([1,8,1])
    with col_m:
        st.markdown("""
        <div style="background:#111c14;border-radius:16px;padding:22px 18px 18px;
             border:.5px solid rgba(255,255,255,.07);">
          <div style="font-size:17px;font-weight:900;color:#eee;margin-bottom:2px;">
            Welcome 👋</div>
          <div style="font-size:11px;color:#2e3e32;margin-bottom:16px;">
            Demo mode — no account needed</div>
        </div>
        """, unsafe_allow_html=True)
        name = st.text_input("Your name", placeholder="e.g. Adeniji Yusuf")
        st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
        role = st.selectbox("I am a",[
            "Citizen — I want to report waste",
            "Operator — I manage waste collection",
        ])
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("Enter EarthMender AI →", type="primary", use_container_width=True):
            if name.strip():
                p = name.strip().split()
                st.session_state.update({
                    "logged_in":True,"user_name":name.strip(),
                    "user_role":"Operator" if "Operator" in role else "Citizen",
                    "user_initials":((p[0][0]+p[-1][0]).upper() if len(p)>=2 else p[0][:2].upper()),
                })
                st.rerun()
            else:
                st.warning("Please enter your name.")
        st.markdown('<div style="text-align:center;margin-top:12px;font-size:10px;'
                    'color:#1a2e1a;">🔒 Session only</div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    _login()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def _detector(): return PlasticDetector()

det         = _detector()
all_r       = load_reports()
open_r      = get_open_reports()
res_r       = get_resolved_reports()
stats       = get_report_stats(all_r)
high_open   = sum(1 for r in open_r if r.get("severity")=="HIGH")
total       = stats.get("total",0)
open_c      = stats.get("open",0)
resolved    = stats.get("resolved",0)
items       = stats.get("items",0)
rate        = f"{int(resolved/total*100)}%" if total>0 else "0%"
uname       = st.session_state.user_name
initials    = st.session_state.user_initials
role        = st.session_state.user_role
cur_tab     = st.session_state.cur_tab

# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="top">
  <div style="display:flex;align-items:center;gap:9px;">
    <div class="av">{initials}</div>
    <div><div class="grt">Welcome back,</div>
    <div class="usr">{uname}</div></div>
  </div>
  <div class="badge">{role.split()[0].upper()}</div>
</div>
""", unsafe_allow_html=True)

# If Home button requested camera open, switch to Detect tab on the client.
# (This runs before tabs are rendered.)
if st.session_state.get("open_cam_from_home", False):
    st.markdown(f"<script>{_tab_js(1)}</script>", unsafe_allow_html=True)
    st.session_state.open_cam_from_home = False

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
_tlabels = ["🏠 Home","🔍 Detect","🗺️ Map","📚 Learn","📊 Stats"]
if role=="Operator": _tlabels.append("🏢 Ops")
_tabs = st.tabs(_tlabels)
t_home,t_det,t_map,t_learn,t_stats = _tabs[:5]
t_ops = _tabs[5] if role=="Operator" else None


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — HOME
# ══════════════════════════════════════════════════════════════════════════════
with t_home:

    # Hero
    st.markdown(f"""
    <div class="hero">
      <div class="bal">
        <div class="bal-lbl">Community Waste Reports</div>
        <div class="bal-val">{total} Cases</div>
      </div>
      <div class="sg">
        <div class="sc"><div class="sv" style="color:#ffb74d;">{open_c}</div>
          <div class="sl">Open</div></div>
        <div class="sc"><div class="sv" style="color:#81c784;">{resolved}</div>
          <div class="sl">Resolved</div></div>
        <div class="sc"><div class="sv">{rate}</div><div class="sl">Rate</div></div>
        <div class="sc"><div class="sv">{items}</div><div class="sl">Items</div></div>
      </div>
    </div>
    <div class="pg">
    """, unsafe_allow_html=True)

    # Alert
    if high_open>0:
        st.markdown(f"""
        <div class="al"><div class="ald"></div>
          <div class="alt">{high_open} HIGH severity case{'s' if high_open>1 else ''} — urgent</div>
        </div>""", unsafe_allow_html=True)

    # Report Waste button (uses Streamlit button so we can set session state)
    if st.button("📸  Report Waste Now", key="home_report_btn"):
        st.session_state.cam_open = True
        st.session_state.open_cam_from_home = True
        st.rerun()

    # Recent Reports
    show_all = st.session_state.show_all
    _all_sorted = sorted(all_r, key=lambda x:x.get("timestamp",""), reverse=True)
    _display = _all_sorted if show_all else _all_sorted[:3]

    col_t, col_a = st.columns([3,1])
    with col_t:
        st.markdown('<div class="sh" style="padding-top:2px;">Recent Reports</div>',
                    unsafe_allow_html=True)
    with col_a:
        if st.button("Less" if show_all else f"All ({len(all_r)})", key="tog_rep"):
            st.session_state.show_all = not show_all
            st.rerun()

    if not _display:
        st.info("No reports yet — be the first!")
    for r in _display:
        sev   = r.get("severity","LOW")
        sta   = r.get("status","OPEN")
        dc    = {"HIGH":"#f44336","MEDIUM":"#ff9800","LOW":"#4caf50"}.get(sev,"#4caf50")
        types = ", ".join(WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
        desc  = r.get("description","") or r.get("date","")
        ss    = {"HIGH":"background:rgba(244,67,54,.15);color:#ef9a9a;",
                 "MEDIUM":"background:rgba(255,152,0,.15);color:#ffcc80;",
                 "LOW":"background:rgba(76,175,80,.15);color:#a5d6a7;"}.get(sev,"")
        ts    = ("background:rgba(255,152,0,.12);color:#ffcc80;" if sta=="OPEN"
                 else "background:rgba(76,175,80,.12);color:#a5d6a7;")
        st.markdown(f"""
        <div class="cc"><div class="cdot" style="background:{dc};"></div>
          <div style="flex:1;min-width:0;">
            <div class="ctype">{types}</div>
            <div class="cloc">{str(desc)[:50]}</div>
            <div class="cmeta">
              <span class="pi" style="{ss}">{sev}</span>
              <span class="pi" style="{ts}">{sta}</span>
              <span class="ctm">{r.get('time','')}</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Analytic heatmap
    st.markdown('<div class="sh" style="padding-top:10px;padding-bottom:6px;">'
                'Pollution Intensity</div>', unsafe_allow_html=True)
    st.markdown(_heatmap_html(all_r, map_tab_idx=_T["map"]), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DETECT
# ══════════════════════════════════════════════════════════════════════════════
with t_det:
    st.markdown('<div class="pg" style="padding-top:0;">', unsafe_allow_html=True)

    # Render camera widget (only while on Detect tab)
    if (st.session_state.cam_open and not st.session_state.det_done
        and st.session_state.cur_tab == _T["detect"]):
        st.markdown("""
        <div style="max-width:480px;margin:0 auto;padding:0 14px 4px;">
          <div style="font-size:11px;color:#4caf50;font-weight:700;
               text-align:center;padding:6px 0 2px;">
            📷 Camera open — hold steady for best results
          </div>
        </div>
        """, unsafe_allow_html=True)
        _cam_inp = st.camera_input("", label_visibility="collapsed", key="main_cam_widget")
        if _cam_inp:
            st.session_state.img_raw  = Image.open(_cam_inp).convert("RGB")
            st.session_state.cam_open = False   # close camera after capture
            st.rerun()

    # Page header — tight spacing
    st.markdown("""
    <div style="padding:7px 0 5px;">
      <div style="font-size:14px;font-weight:900;color:#eee;letter-spacing:-.2px;">
        📸 Detect Plastic Waste</div>
      <div style="font-size:10px;color:#3a4a3e;margin-top:1px;">
        AI · 5 classes · GPS-tagged</div>
    </div>
    <div class="dtiles">
      <div class="dtile"><div class="dtile-i">🎯</div><div class="dtile-l">AI Detect</div></div>
      <div class="dtile"><div class="dtile-i">📍</div><div class="dtile-l">GPS Tag</div></div>
      <div class="dtile"><div class="dtile-i">⚡</div><div class="dtile-l">Instant</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Mode selector
    det_mode = st.radio("Source",["📷 Camera","📁 Upload"],
                        horizontal=True, label_visibility="collapsed",
                        key="det_mode_sel")

    # ── Camera mode UI ────────────────────────────────────────────────────────
    if not st.session_state.det_done:
        if det_mode == "📷 Camera":
            if st.session_state.img_raw is None:
                if not st.session_state.cam_open:
                    # Show Open Camera button
                    st.markdown(f"""
                    <div class="cap">
                      {_IC["cam"]}
                      <div class="cap-t">Tap to open camera</div>
                      <div class="cap-s">Hold steady · Good lighting = better accuracy</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("📷 Open Camera", type="primary",
                                 use_container_width=True, key="open_cam_btn"):
                        st.session_state.cam_open = True
                        st.rerun()
                else:
                    # Camera is open (rendered above tabs) — show status here
                    st.markdown("""
                    <div style="background:rgba(76,175,80,.08);border-radius:10px;
                         padding:11px 14px;text-align:center;
                         border:.5px solid rgba(76,175,80,.2);margin:8px 0;">
                      <div style="font-size:12px;color:#4caf50;font-weight:700;">
                        📷 Camera is open — scroll up to see it</div>
                      <div style="font-size:10px;color:#3a4a3e;margin-top:3px;">
                        Take the photo and it will appear here</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("✕ Close Camera", key="close_cam_btn"):
                        st.session_state.cam_open = False
                        st.rerun()
            # else: image captured — show it below

        else:
            # Upload mode — close camera if it was open
            if st.session_state.cam_open:
                st.session_state.cam_open = False
            if st.session_state.img_raw is None:
                st.markdown(f"""
                <div class="cap">
                  {_IC["upl"]}
                  <div class="cap-t">Tap to upload a photo</div>
                  <div class="cap-s">JPG, PNG, WEBP · Max 10MB</div>
                </div>
                """, unsafe_allow_html=True)
                upl = st.file_uploader("", type=["jpg","jpeg","png","webp"],
                                       label_visibility="collapsed", key="upl_det")
                if upl:
                    st.session_state.img_raw = Image.open(upl).convert("RGB")
                    st.rerun()

    # Show captured image (before detection only)
    if st.session_state.img_raw and not st.session_state.det_done:
        st.image(st.session_state.img_raw,
                 caption="Ready for analysis", use_column_width=True)

    # Show annotated image (after detection only — never both)
    if st.session_state.det_done:
        if st.session_state.img_ann:
            st.image(st.session_state.img_ann,
                     caption="Detection result", use_column_width=True)

        q = st.session_state.det_qual or {}
        if q.get("quality")=="poor":
            st.markdown(f'<div class="res-warn">⚠️ {q.get("message","")}</div>',
                        unsafe_allow_html=True)

        dets = st.session_state.det_dets
        if dets:
            st.markdown(f'<div class="res-ok">✅ Detected <b>{len(dets)}</b> waste item(s)</div>',
                        unsafe_allow_html=True)
            seen = set()
            for d in dets:
                if d["label"] not in seen:
                    seen.add(d["label"])
                    lbl  = WASTE_LABELS.get(d["label"],d["label"].replace("_"," ").title())
                    band = d.get("confidence_band","Possible")
                    conf = d["confidence"]
                    st.markdown(
                        f'<div class="tip-box"><b style="color:#90caf9;">{lbl}</b>'
                        f'&nbsp;<span class="pi conf-{band}" '
                        f'style="font-size:9px;padding:2px 7px;border-radius:20px;">'
                        f'{band} {conf:.0%}</span>'
                        f'<br><span style="color:#555;font-size:11px;line-height:1.6;">'
                        f'{d["tip"]}</span></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="res-warn">⚠️ No plastic waste detected — '
                        'try better lighting or move closer.</div>',
                        unsafe_allow_html=True)

        if st.button("🔄 Scan Another", use_container_width=True, key="scan_again"):
            st.session_state.update({
                "img_raw":None,"img_ann":None,"det_dets":[],
                "det_qual":None,"det_done":False,"cam_open":False,
            })
            st.rerun()

    # Location + submit (shown when image captured but not yet detected)
    if st.session_state.img_raw and not st.session_state.det_done:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;font-weight:800;color:#ddd;'
                    'margin-bottom:7px;">📍 Location</div>', unsafe_allow_html=True)

        lm = st.radio("Loc",["🌐 Auto GPS","✏️ Manual"],
                      horizontal=True, label_visibility="collapsed", key="det_lm")
        if lm=="🌐 Auto GPS":
            lat,lon = _gps_widget()
        else:
            c1,c2 = st.columns(2)
            with c1: lat = st.number_input("Latitude",value=6.524400,format="%.6f",key="man_lat")
            with c2: lon = st.number_input("Longitude",value=3.379200,format="%.6f",key="man_lon")

        desc = st.text_area("📝 Location description (optional)",
                            placeholder="e.g. Near Ojota bus stop, beside the drainage",
                            max_chars=200, key="det_desc")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("🔍 Analyse & Submit Report", type="primary",
                     use_container_width=True, key="analyse_btn"):
            with st.spinner("🌍 Analysing..."):
                ann,dets,qual = det.detect_from_image(st.session_state.img_raw)
                st.session_state.update({
                    "img_ann":ann,"det_dets":dets,
                    "det_qual":qual,"det_done":True,
                })
                if dets:
                    save_report(dets,lat=lat,lon=lon,
                                description=desc,reporter_name=uname)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MAP
# ══════════════════════════════════════════════════════════════════════════════
with t_map:

    st.markdown('<div class="pg" style="padding-top:0;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:7px 0 5px;">
      <div style="font-size:14px;font-weight:900;color:#eee;">🗺️ Live Pollution Map</div>
      <div style="font-size:10px;color:#3a4a3e;margin-top:1px;">
        Heatmap · Severity · Recurrence · Time-weighted</div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    c1.metric("Total", len(all_r))
    c2.metric("Open",  len(open_r))
    c3.metric("Resolved", len(res_r))

    mf = st.radio("Show",["All","Open Only","Resolved Only"],
                  horizontal=True, key="map_flt")
    md = (open_r if mf=="Open Only" else
          res_r  if mf=="Resolved Only" else all_r)

    fmap = build_map(md, all_reports=all_r)
    st_folium(fmap, width=None, height=430, returned_objects=[], key="fmap_fin")

    hs = get_hotspots(open_r) if open_r else []
    if hs:
        st.markdown('<div style="font-size:13px;font-weight:900;color:#eee;'
                    'margin:12px 0 7px;">🔥 Active Hotspots</div>', unsafe_allow_html=True)
        for i,h in enumerate(hs[:3],1):
            osm=f"https://www.openstreetmap.org/?mlat={h['lat']}&mlon={h['lon']}&zoom=16"
            st.markdown(f"**#{i}** `{h['lat']:.3f},{h['lon']:.3f}` — "
                        f"{h['count']} report(s) · {h['items']} items · [📍]({osm})")

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LEARN
# ══════════════════════════════════════════════════════════════════════════════
with t_learn:
    if st.session_state.cam_open:
        st.session_state.cam_open = False
    render_education_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STATS
# ══════════════════════════════════════════════════════════════════════════════
with t_stats:
    if st.session_state.cam_open:
        st.session_state.cam_open = False
    render_full_dashboard(
        get_report_stats(load_reports()),
        get_hotspots(load_reports()),
        load_reports(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — OPS
# ══════════════════════════════════════════════════════════════════════════════
if t_ops:
    with t_ops:
        if st.session_state.cam_open:
            st.session_state.cam_open = False
        st.markdown('<div class="pg" style="padding-top:0;">', unsafe_allow_html=True)
        st.markdown('<div style="padding:7px 0 5px;"><div style="font-size:14px;'
                    'font-weight:900;color:#eee;">🏢 Operator Dashboard</div></div>',
                    unsafe_allow_html=True)
        oc=get_open_reports(); rc=get_resolved_reports(); tc=len(oc)+len(rc)
        k1,k2,k3=st.columns(3)
        k1.metric("Open",len(oc)); k2.metric("Resolved",len(rc))
        k3.metric("Rate",f"{int(len(rc)/tc*100)}%" if tc else "0%")
        st.divider()
        sf=st.selectbox("Severity",["All","HIGH","MEDIUM","LOW"])
        so=st.radio("Sort",["Severity first","Newest first"],horizontal=True)
        fl=oc if sf=="All" else [r for r in oc if r.get("severity")==sf]
        fl=(sorted(fl,key=lambda x:{"HIGH":0,"MEDIUM":1,"LOW":2}.get(x.get("severity"),3))
            if so=="Severity first"
            else sorted(fl,key=lambda x:x.get("timestamp",""),reverse=True))
        st.markdown(f"#### 🟠 Open ({len(fl)})")
        if not fl: st.success("All clear!")
        for r in fl:
            sev=r.get("severity","LOW")
            types=", ".join(WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
            icon={"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(sev,"🟢")
            osm=f"https://www.openstreetmap.org/?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17"
            with st.expander(f"{icon} #{r['id']} — {sev} — {types}",expanded=(sev=="HIGH")):
                c1,c2=st.columns([2,1])
                with c1:
                    st.write(f"**Waste:** {types}")
                    st.write(f"**Reporter:** {r.get('reporter','Anonymous')}")
                    if r.get("description"): st.write(f"**Location:** {r['description']}")
                with c2:
                    st.code(f"{r['latitude']:.5f}\n{r['longitude']:.5f}")
                    st.markdown(f"[📍 Map]({osm})")
                note=st.text_input("Note","Area cleaned.",key=f"note_{r['id']}")
                if st.button(f"✅ Resolve #{r['id']}",key=f"res_{r['id']}",type="primary"):
                    if resolve_report(r["id"],resolved_by=uname,note=note):
                        st.success("Resolved!"); st.rerun()
        st.divider()
        st.markdown(f"#### ✅ Resolved ({len(rc)})")
        for r in sorted(rc,key=lambda x:x.get("resolved_at",""),reverse=True)[:8]:
            types=", ".join(WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
            rd=(r.get("resolved_at") or "")[:10]
            with st.expander(f"✅ #{r['id']} — {types} — {rd}"):
                st.write(f"**By:** {r.get('resolved_by','Operator')}")
                st.write(f"**Note:** {r.get('resolution_note','—')}")
                if st.button(f"↩️ Reopen #{r['id']}",key=f"reopen_{r['id']}"):
                    reopen_report(r["id"]); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FIXED BOTTOM NAV — mobile only, all 5 tabs wired via JS onclick
# ══════════════════════════════════════════════════════════════════════════════
_cur = st.session_state.cur_tab

_fab = (
    f'<button class="fab" onclick="{_tab_js(_T["detect"])}">'
    f'<div class="fab-c">{_IC["plus"]}</div>'
    f'<span class="fab-lbl">Report</span></button>'
)

st.markdown(f"""
<div class="bnav">
  <div class="bnav-row">
    {_bn(_T["home"],  "home",  "Home",  _cur)}
    {_bn(_T["map"],   "map",   "Map",   _cur)}
    {_fab}
    {_bn(_T["stats"], "stats", "Stats", _cur)}
    {_bn(_T["learn"], "learn", "Learn", _cur)}
  </div>
</div>
<div class="sp"></div>
""", unsafe_allow_html=True)
