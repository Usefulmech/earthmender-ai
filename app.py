"""
EarthMender AI — Final Application
Run: streamlit run app.py
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

st.set_page_config(
    page_title="EarthMender AI", page_icon="🌍",
    layout="wide", initial_sidebar_state="collapsed",
)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in {
    "logged_in": False, "user_name": "", "user_role": "Citizen",
    "user_initials": "?",
    "cam_open": False,
    "img_raw": None, "img_ann": None,
    "det_dets": [], "det_qual": None, "det_done": False,
    "show_all": False,
    "show_cam_det": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── JS: click a Streamlit tab by index ───────────────────────────────────────
def _tjs(i):
    return (f"(function(){{var t=window.parent.document"
            f".querySelectorAll('[data-baseweb=\"tab\"]');"
            f"if(t[{i}])t[{i}].click();}})();")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

#MainMenu,header,footer,[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"]{display:none!important}

*{box-sizing:border-box;margin:0;padding:0}

html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],
.main,[data-testid="stMainBlockContainer"]{
  font-family:'Inter',sans-serif!important;
  background:#141d16!important;
  color:#1a1a1a!important;
  padding:0!important;margin:0!important;width:100%!important}

.block-container{padding:0!important;max-width:480px!important;
  margin:0 auto!important;width:100%!important}
@media(max-width:640px){
  .block-container{max-width:100vw!important;margin:0!important}}

/* ── Top bar ── */
.top{background:#1a7a4a;padding:13px 16px 11px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:300}
.av{width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.22);
  display:flex;align-items:center;justify-content:center;
  font-size:15px;font-weight:900;color:#fff}
.grt{color:rgba(255,255,255,.65);font-size:11px;line-height:1.3}
.usr{color:#fff;font-size:16px;font-weight:800;letter-spacing:-.3px}
.role-badge{background:rgba(255,255,255,.15);border-radius:8px;
  padding:4px 10px;font-size:11px;font-weight:700;
  color:rgba(255,255,255,.8);letter-spacing:.4px}

/* ── Tab bar ── */
.stTabs [data-baseweb="tab-list"]{
  background:#1a2e1e!important;
  border-bottom:1px solid rgba(255,255,255,.07)!important;
  gap:0!important;padding:0!important;
  display:flex!important;width:100%!important}
.stTabs [data-baseweb="tab"]{
  flex:1!important;display:flex!important;flex-direction:column!important;
  align-items:center!important;justify-content:center!important;
  gap:3px!important;padding:9px 2px 10px!important;
  font-size:10px!important;font-weight:800!important;
  color:#4a6450!important;letter-spacing:.7px!important;
  text-transform:uppercase!important;
  border-bottom:3px solid transparent!important;
  font-family:'Inter',sans-serif!important;min-height:56px!important}
.stTabs [aria-selected="true"]{
  color:#1a7a4a!important;border-bottom:3px solid #1a7a4a!important;
  background:rgba(26,122,74,.06)!important}
.stTabs [data-baseweb="tab-panel"]{background:#141d16!important;padding:0!important}

/* ── Hero ── */
.hero{background:linear-gradient(160deg,#1a7a4a,#145c38);
  padding:16px 16px 18px}
.bal{background:rgba(255,255,255,.12);border-radius:16px;
  padding:16px 18px;border:.5px solid rgba(255,255,255,.18);margin-bottom:14px}
.bal-lbl{color:rgba(255,255,255,.65);font-size:11px;margin-bottom:6px;
  text-transform:uppercase;letter-spacing:1px;font-weight:600}
.bal-val{color:#fff;font-size:28px;font-weight:900;letter-spacing:-.5px}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
.sc{background:rgba(255,255,255,.11);border-radius:10px;
  padding:10px 4px;text-align:center}
.sv{color:#fff;font-size:17px;font-weight:900}
.sl{color:rgba(255,255,255,.55);font-size:9px;margin-top:2px;
  text-transform:uppercase;letter-spacing:.5px;font-weight:600}

/* ── Page ── */
.pg{background:#141d16;padding:0 16px 80px}

/* ── Section title ── */
.sh{font-size:15px;font-weight:800;color:#e0ece0;letter-spacing:-.2px}

/* ── Alert ── */
.al{background:rgba(255,152,0,.1);border-radius:12px;padding:9px 12px;
  display:flex;align-items:center;gap:9px;
  border:.5px solid rgba(255,152,0,.25);margin:6px 0 4px}
.ald{width:7px;height:7px;border-radius:50%;background:#e65100;flex-shrink:0}
.alt{font-size:13px;color:#ffcc80;flex:1;font-weight:600}

/* rw button replaced by Streamlit button */

/* ── Case cards ── */
.cc{background:#1e3022;border-radius:14px;padding:14px 16px;
  border:.5px solid rgba(255,255,255,.07);
  display:flex;align-items:flex-start;gap:11px;margin-bottom:8px;}
.cdot{width:9px;height:9px;border-radius:50%;flex-shrink:0;margin-top:5px}
.ctype{font-size:13px;font-weight:700;color:#eee;line-height:1.3}
.cloc{font-size:12px;color:#8aaa8c;margin-top:3px}
.cmeta{display:flex;align-items:center;gap:6px;margin-top:7px;flex-wrap:wrap}
.pi{font-size:11px;padding:3px 10px;border-radius:20px;font-weight:800}
.ctm{font-size:10px;color:#aabcac;margin-left:auto}

/* ── See all toggle ── */
.tog{font-size:12px;color:#1a7a4a;font-weight:700;background:rgba(26,122,74,.08);
  border:none;border-radius:8px;padding:5px 11px;cursor:pointer;
  font-family:'Inter',sans-serif}

/* ── Pollution intensity card ── */
.hm-card{background:#1e3022;border-radius:16px;border:.5px solid rgba(255,255,255,.07);
  overflow:hidden;margin-bottom:4px}
.hm-hdr{padding:14px 16px 9px;display:flex;align-items:flex-start;
  justify-content:space-between}
.hm-title{font-size:15px;font-weight:800;color:#e0ece0}
.hm-sub{font-size:12px;color:#8aaa8c;margin-top:2px;font-weight:500}
.hm-openbtn{font-size:12px;font-weight:800;color:#fff;
  background:#1a7a4a;border:none;border-radius:14px;
  padding:6px 13px;cursor:pointer;font-family:'Inter',sans-serif;
  white-space:nowrap;flex-shrink:0;margin-left:8px}
.hm-grid{display:grid;gap:4px;padding:0 16px 12px}
.hm-cell{border-radius:5px;height:30px;transition:opacity .2s}
.hm-legend{display:flex;align-items:center;gap:10px;
  padding:0 16px 10px;font-size:11px;color:#7a927c;font-weight:500}
.hm-legbar{flex:1;height:6px;border-radius:3px;
  background:linear-gradient(90deg,#c8e6c9,#4caf50,#ff9800,#f44336)}
.hm-zones{display:flex;gap:5px;padding:0 16px 14px;flex-wrap:wrap}
.hm-zone{background:#162818;border-radius:8px;padding:6px 10px;
  font-size:11px;display:flex;align-items:center;gap:6px;
  border:.5px solid rgba(255,255,255,.07);font-weight:600}
.hm-zdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.hm-empty{padding:32px 16px;text-align:center}
.hm-empty-icon{font-size:28px;margin-bottom:8px}
.hm-empty-txt{font-size:13px;color:#7a927c;font-weight:500}

/* ── Camera / upload zone ── */
.cap{border:2px dashed rgba(76,175,80,.25);border-radius:18px;
  padding:36px 20px;text-align:center;background:#1e3022;
  margin:10px 0;}
.cap-t{font-size:15px;font-weight:700;color:#b0cdb4;margin-top:12px}
.cap-s{font-size:12px;color:#7a927c;margin-top:4px}

/* ── Detect info tiles ── */
.dtiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0 12px}
.dtile{background:#1e3022;border-radius:12px;padding:12px 6px;text-align:center;
  border:.5px solid rgba(255,255,255,.07)}
.dtile-i{font-size:20px;margin-bottom:4px}
.dtile-l{font-size:11px;color:#8aaa8c;text-transform:uppercase;
  letter-spacing:.5px;font-weight:700}

/* ── Results ── */
.res-ok{background:rgba(76,175,80,.12);border-left:4px solid #4caf50;
  padding:13px 15px;border-radius:12px;margin:10px 0;
  color:#a5d6a7;font-size:14px;font-weight:700}
.res-warn{background:rgba(255,152,0,.1);border-left:4px solid #ff9800;
  padding:13px 15px;border-radius:12px;margin:10px 0;
  color:#ffcc80;font-size:14px;font-weight:600}
.tip-box{background:rgba(33,150,243,.1);border-left:4px solid #1976d2;
  padding:12px 14px;border-radius:12px;font-size:13px;
  color:#90caf9;margin:8px 0;font-weight:500}

/* ── Confidence pills ── */
.conf-Certain{background:rgba(76,175,80,.18);color:#81c784}
.conf-Likely{background:rgba(255,193,7,.18);color:#ffd54f}
.conf-Possible{background:rgba(158,158,158,.14);color:#aaa}

/* ── Page headers ── */
.pg-hdr{padding:0 0 4px}
.pg-title{font-size:16px;font-weight:800;color:#e0ece0;letter-spacing:-.2px}
.pg-sub{font-size:13px;color:#8aaa8c;margin-top:3px;font-weight:500}

/* ── Streamlit overrides ── */
.stButton>button{font-family:'Inter',sans-serif!important;font-weight:800!important;
  border-radius:28px!important;border:none!important;font-size:14px!important;
  padding:11px 20px!important}
.stButton>button[kind="primary"]{background:#1a7a4a!important;color:#fff!important;
  box-shadow:0 3px 10px rgba(26,122,74,.25)!important;
  font-size:15px!important;padding:13px 20px!important;border-radius:28px!important}
.stButton>button:not([kind="primary"]){background:#1e3022!important;color:#b0cdb4!important;
  border:.5px solid rgba(255,255,255,.1)!important}

div[data-testid="stMetric"]{background:#1e3022!important;border-radius:12px!important;
  padding:14px!important;border:.5px solid rgba(255,255,255,.07)!important}
div[data-testid="stMetricLabel"] p{color:#6a826c!important;font-size:10px!important;
  text-transform:uppercase!important;letter-spacing:.5px!important;font-weight:700!important}
div[data-testid="stMetricValue"] div{color:#e0ece0!important;font-size:22px!important;font-weight:900!important}

.stTextInput input,.stTextArea textarea,.stNumberInput input{
  background:#1e3022!important;border:.5px solid rgba(255,255,255,.09)!important;
  border-radius:10px!important;color:#e0ece0!important;padding:10px 13px!important;
  font-size:14px!important;font-family:'Inter',sans-serif!important}
.stTextInput input:focus{border-color:#1a7a4a!important;
  box-shadow:0 0 0 3px rgba(26,122,74,.12)!important}
.stSelectbox>div>div{background:#1e3022!important;
  border:.5px solid rgba(255,255,255,.09)!important;color:#e0ece0!important;
  border-radius:10px!important;font-size:14px!important}
label,[data-testid="stWidgetLabel"] p,.stRadio label p{
  color:#8aaa8c!important;font-size:13px!important;font-weight:600!important;
  font-family:'Inter',sans-serif!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#b0cdb4!important;font-size:14px!important}

details,summary{background:#1e3022!important;border-radius:12px!important;
  border:.5px solid rgba(255,255,255,.07)!important;color:#e0ece0!important;
  font-size:13px!important}
hr{border-color:rgba(255,255,255,.07)!important;margin:14px 0!important}
.stProgress>div>div>div{background:#1a7a4a!important;border-radius:4px!important}
.stCaption p{color:#8aaa8c!important;font-size:13px!important;font-weight:500!important}
[data-testid="stAlert"]{background:#1e3022!important;border-radius:12px!important;
  border:.5px solid rgba(255,255,255,.07)!important;color:#b0cdb4!important;font-size:14px!important}
[data-testid="stMarkdownContainer"] p{color:#b0cdb4!important;font-size:14px!important;font-weight:500!important}
[data-testid="stMarkdownContainer"] h2,h3,h4{color:#e0ece0!important;
  font-family:'Inter',sans-serif!important;font-weight:800!important}
[data-testid="stTable"] table{background:#1e3022!important;border-radius:10px!important}
thead tr th{background:#162818!important;color:#6a826c!important;
  font-size:11px!important;text-transform:uppercase!important;font-weight:700!important}
tbody tr td{color:#b0cdb4!important;border-color:rgba(255,255,255,.05)!important;
  font-size:13px!important;font-weight:500!important}

/* ── Sub-tabs (stats) ── */
.stTabs .stTabs [data-baseweb="tab-list"]{
  background:#162818!important;border-radius:10px!important;
  padding:4px!important;gap:3px!important;border:none!important}
.stTabs .stTabs [data-baseweb="tab"]{
  flex:none!important;border-radius:8px!important;min-height:34px!important;
  font-size:12px!important;padding:6px 13px!important;
  border-bottom:none!important;flex-direction:row!important;
  gap:5px!important;text-transform:none!important;
  letter-spacing:0!important;font-weight:700!important;color:#8aaa8c!important}
.stTabs .stTabs [aria-selected="true"]{
  background:rgba(76,175,80,.2)!important;color:#4caf50!important;border-bottom:none!important}

/* Bottom nav removed */

@media(max-width:360px){.sg,.dtiles{grid-template-columns:repeat(2,1fr)}}

/* All images always fit container — never overflow */
[data-testid="stImage"]{width:100%!important;max-width:100%!important}
[data-testid="stImage"] img{width:100%!important;max-width:100%!important;
  height:auto!important;border-radius:12px;display:block}
</style>
""", unsafe_allow_html=True)

# ── ICONS ─────────────────────────────────────────────────────────────────────
_IC = {
    "home":   '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="24" height="24"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "map":    '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" width="24" height="24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "stats":  '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" width="24" height="24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "learn":  '<svg viewBox="0 0 24 24" fill="none" stroke="CLR" stroke-width="2.5" stroke-linecap="round" width="24" height="24"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    "plus":   '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" width="22" height="22"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "cam":    '<svg viewBox="0 0 24 24" fill="none" stroke="#1a7a4a" stroke-width="2" stroke-linecap="round" width="48" height="48"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
    "upl":    '<svg viewBox="0 0 24 24" fill="none" stroke="#1a7a4a" stroke-width="2" stroke-linecap="round" width="48" height="48"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>',
}
_T = {"home":0,"detect":1,"map":2,"learn":3,"stats":4}

WASTE_LABELS = {
    "plastic_bottle":"🍶 Plastic Bottle","water_sachet":"💧 Water Sachet",
    "polythene_bag":"🛍️ Polythene Bag","disposable":"🥤 Disposable",
    "waste_container":"🛢️ Waste Container",
}

def _ic(k, col="#1a7a4a"):
    return _IC[k].replace("CLR", col)

def _bn_html(idx, ik, lbl, cur):
    on  = "on" if idx==cur else ""
    col = "#1a7a4a" if idx==cur else "#aabcac"
    op  = "1" if idx==cur else "0.5"
    return (f'<button class="bn {on}" onclick="{_tjs(idx)}">'
            f'<span class="bn-ic" style="opacity:{op};">{_ic(ik,col)}</span>'
            f'<span class="bn-lbl" style="color:{col};">{lbl}</span>'
            f'</button>')

# ── ANALYTIC HEATMAP ──────────────────────────────────────────────────────────
def _heatmap(reports, map_idx=2):
    open_r = [r for r in reports if r.get("status")=="OPEN"]
    open_js = _tjs(map_idx)

    if not open_r:
        return f"""
        <div class="hm-card">
          <div class="hm-hdr">
            <div>
              <div class="hm-title">🗺️ Pollution Intensity</div>
              <div class="hm-sub">No active reports yet</div>
            </div>
            <button class="hm-openbtn" onclick="{open_js}">Open Map →</button>
          </div>
          <div class="hm-empty">
            <div class="hm-empty-icon">🌿</div>
            <div class="hm-empty-txt">All clear — no open waste reports in your area</div>
          </div>
        </div>"""

    # Group into ~2km grid cells
    grid = defaultdict(lambda: {"c":0,"h":0,"t":set()})
    for r in open_r:
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
        if h>0 and i>0.4: return f"rgba(198,40,40,{.3+i*.5:.2f})"
        if i>=0.65:        return f"rgba(230,81,0,{.3+i*.4:.2f})"
        if i>=0.35:        return f"rgba(245,127,23,{.25+i*.35:.2f})"
        if i>=0.15:        return f"rgba(76,175,80,{.2+i*.3:.2f})"
        return                    f"rgba(200,230,201,{.3+i*.3:.2f})"

    cols   = 8
    rows_n = max(3, -(-min(len(top),24)//cols))
    cells  = ""
    for i in range(cols*rows_n):
        if i < len(top):
            _, z = top[i]
            bg  = hcol(z["c"],z["h"],mx)
            cnt = z["c"]
            # tooltip text explaining what each cell means
            tt  = f"{cnt} waste report{'s' if cnt>1 else ''} in this zone"
            cells += (f'<div class="hm-cell" style="background:{bg};" '
                      f'title="{tt}"></div>')
        else:
            cells += '<div class="hm-cell" style="background:rgba(0,0,0,.04);"></div>'

    # Zone list — human readable location tags
    ticons={"plastic_bottle":"🍶","water_sachet":"💧","polythene_bag":"🛍️",
            "disposable":"🥤","waste_container":"🛢️"}
    zones=""
    for (lat,lon),z in top[:5]:
        i   = z["c"]/mx
        dc  = "#d32f2f" if z["h"]>0 else "#e65100" if i>.5 else "#f9a825" if i>.25 else "#388e3c"
        ics = "".join(ticons.get(t,"♻️") for t in list(z["t"])[:2])
        cnt = z["c"]
        zones += (f'<div class="hm-zone">'
                  f'<span class="hm-zdot" style="background:{dc};"></span>'
                  f'<span style="color:#4a6450;">{lat:.2f}°,{lon:.2f}°</span>'
                  f'<span>{ics}</span>'
                  f'<span style="color:#7a927c;font-weight:700;">{cnt} report{"s" if cnt>1 else ""}</span>'
                  f'</div>')

    return f"""
    <div class="hm-card">
      <div class="hm-hdr">
        <div>
          <div class="hm-title">🗺️ Pollution Intensity Map</div>
          <div class="hm-sub">Each cell = one ~2km zone · darker = more waste reported</div>
        </div>
        <button class="hm-openbtn" onclick="{open_js}">Open Map →</button>
      </div>
      <div class="hm-grid" style="grid-template-columns:repeat({cols},1fr);">{cells}</div>
      <div class="hm-legend">
        <span style="font-weight:600;">Low</span>
        <div class="hm-legbar"></div>
        <span style="font-weight:600;">High</span>
      </div>
      <div class="hm-zones">{zones}</div>
    </div>"""

# ── GPS WIDGET ────────────────────────────────────────────────────────────────
def _gps_widget():
    comp_html("""
    <style>
    body{margin:0;font-family:Inter,sans-serif}
    #gs{padding:10px 12px;background:#e3f2fd;border-radius:10px;
        color:#1565c0;line-height:1.7;margin-bottom:7px;font-size:13px;font-weight:500}
    #gb{display:none;margin-bottom:6px}
    #gbt{font-size:11px;color:#7a927c;margin-bottom:3px;font-weight:600}
    #gbt2{background:#dde8de;border-radius:3px;height:5px}
    #gbf{height:5px;border-radius:3px;background:#4caf50;width:0%;transition:width .4s}
    #gl{font-size:11px;color:#7a927c;margin-top:2px;font-weight:500}
    #gc{display:none;background:#e8f5e9;border-radius:10px;
        padding:10px 12px;font-size:13px;color:#1b5e20;font-weight:600}
    </style>
    <div id="gs">⏳ Acquiring GPS signal...</div>
    <div id="gb">
      <div id="gbt">GPS Accuracy</div>
      <div id="gbt2"><div id="gbf"></div></div>
      <div id="gl"></div>
    </div>
    <div id="gc"><span id="glat"></span><br><span id="glon"></span></div>
    <script>
    var best=9999;
    function upd(a){
      var f=document.getElementById('gbf'),l=document.getElementById('gl');
      var p=Math.max(0,Math.min(100,100-(a/50*100)));
      f.style.width=p+'%';
      f.style.background=a<=10?'#4caf50':a<=30?'#ff9800':'#f44336';
      l.textContent=(a<=10?'Excellent':a<=30?'Good':'Still acquiring')+' \u00b1'+Math.round(a)+'m';
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
        s.style.background='#e8f5e9';s.style.color='#1b5e20';
        s.innerHTML='📍 GPS locked — copy coordinates below';
        upd(a);
      }
    }
    function onE(e){
      var s=document.getElementById('gs');
      s.style.background='#fff3e0';s.style.color='#bf360c';
      s.innerHTML='⚠️ '+(e.code===1?'Permission denied — use Manual Entry':'GPS unavailable — use Manual Entry');
    }
    if(navigator.geolocation){
      navigator.geolocation.watchPosition(onP,onE,{enableHighAccuracy:true,timeout:15000,maximumAge:0});
    }else{document.getElementById('gs').textContent='❌ GPS not supported — use Manual Entry';}
    </script>
    """, height=140)
    c1,c2 = st.columns(2)
    with c1: lat_s = st.text_input("Latitude", placeholder="e.g. 6.524400", key="gps_lat_v3")
    with c2: lon_s = st.text_input("Longitude", placeholder="e.g. 3.379200", key="gps_lon_v3")
    lat, lon = 6.5244, 3.3792
    if lat_s and lon_s:
        try: lat,lon = float(lat_s),float(lon_s)
        except ValueError: st.warning("⚠️ Invalid coordinates — Lagos default used.")
    return lat, lon

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def _login():
    st.markdown("""
    <div style="text-align:center;padding:56px 0 32px;
         background:linear-gradient(180deg,rgba(26,122,74,.15),transparent);">
      <div style="font-size:56px;margin-bottom:10px;">🌍</div>
      <div style="font-size:26px;font-weight:900;color:#e0ece0;letter-spacing:-.5px;margin-bottom:5px;">
        EarthMender AI</div>
      <div style="font-size:11px;color:#4a6450;letter-spacing:2.5px;font-weight:700;">
        DETECT · REPORT · LEARN · ACT</div>
    </div>
    """, unsafe_allow_html=True)

    col_l,col_m,col_r = st.columns([1,8,1])
    with col_m:
        st.markdown("""
        <div style="background:#1e3022;border-radius:20px;padding:26px 22px 22px;
             border:.5px solid rgba(255,255,255,.08);">
          <div style="font-size:20px;font-weight:900;color:#e0ece0;margin-bottom:3px;">
            Welcome 👋</div>
          <div style="font-size:13px;color:#6a826c;margin-bottom:20px;font-weight:500;">
            Demo mode — no account needed</div>
        </div>
        """, unsafe_allow_html=True)
        name = st.text_input("Your name", placeholder="e.g. Adeniji Yusuf")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        role = st.selectbox("I am a",[
            "Citizen — I want to report waste",
            "Operator — I manage waste collection",
        ])
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
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
                st.warning("Please enter your name to continue.")
        st.markdown('<div style="text-align:center;margin-top:14px;font-size:11px;'
                    'color:#aabcac;font-weight:500;">🔒 Session only — no data stored permanently</div>',
                    unsafe_allow_html=True)

if not st.session_state.logged_in:
    _login()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def _det(): return PlasticDetector()

det       = _det()
all_r     = load_reports()
open_r    = get_open_reports()
res_r     = get_resolved_reports()
stats     = get_report_stats(all_r)
hi_open   = sum(1 for r in open_r if r.get("severity")=="HIGH")
total     = stats.get("total",0)
open_c    = stats.get("open",0)
resolved  = stats.get("resolved",0)
items     = stats.get("items",0)
rate      = f"{int(resolved/total*100)}%" if total>0 else "0%"
uname     = st.session_state.user_name
initials  = st.session_state.user_initials
role      = st.session_state.user_role

# ── TOP BAR ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top">
  <div style="display:flex;align-items:center;gap:10px;">
    <div class="av">{initials}</div>
    <div><div class="grt">Welcome back,</div>
    <div class="usr">{uname}</div></div>
  </div>
  <div class="role-badge">{role.split()[0].upper()}</div>
</div>
""", unsafe_allow_html=True)

# Camera is rendered inside the Detect tab block only

# ── TABS ──────────────────────────────────────────────────────────────────────
_tl = ["🏠 Home","🌿 Mend","🗺️ Map","📚 Learn","📊 Stats"]
if role=="Operator": _tl.append("🏢 Ops")
_tabs = st.tabs(_tl)
t_home,t_det,t_map,t_learn,t_stats = _tabs[:5]
t_ops = _tabs[5] if role=="Operator" else None

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
with t_home:
    st.session_state.cam_open = False

    st.markdown(f"""
    <div class="hero">
      <div class="bal">
        <div class="bal-lbl">Community Waste Reports</div>
        <div class="bal-val">{total} Cases</div>
      </div>
      <div class="sg">
        <div class="sc"><div class="sv" style="color:#ffcc80;">{open_c}</div>
          <div class="sl">Open</div></div>
        <div class="sc"><div class="sv" style="color:#a5d6a7;">{resolved}</div>
          <div class="sl">Resolved</div></div>
        <div class="sc"><div class="sv">{rate}</div><div class="sl">Rate</div></div>
        <div class="sc"><div class="sv">{items}</div><div class="sl">Items</div></div>
      </div>
    </div>
    <div class="pg" style="margin-top:-4px;">
    """, unsafe_allow_html=True)
    # Alert
    if hi_open > 0:
        st.markdown(f"""
        <div class="al"><div class="ald"></div>
          <div class="alt">{hi_open} HIGH severity case{'s' if hi_open>1 else ''} need urgent attention</div>
        </div>""", unsafe_allow_html=True)

    # Recent Reports
    show_all  = st.session_state.show_all
    _sorted   = sorted(all_r, key=lambda x:x.get("timestamp",""), reverse=True)
    _display  = _sorted if show_all else _sorted[:3]

    _tog_label = "Less" if show_all else f"All ({len(all_r)})"
    
    # Title and toggle button in a row - flush with top
    st.markdown('<div style="margin-top:-60px;margin-bottom:6px;">', unsafe_allow_html=True)
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.markdown('<span style="font-size:16px;font-weight:800;color:#e0ece0;line-height:1;padding-top:2px;">Recent Reports</span>', unsafe_allow_html=True)
    with col2:
        if st.button(_tog_label, key="tog", use_container_width=False):
            st.session_state.show_all = not show_all
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Style button to be compact
    st.markdown("""
    <style>
    div[data-testid="element-container"]:has(button[key="tog"]) {
        margin-top: -38px !important;
        margin-bottom: 0 !important;
    }
    div[data-testid="element-container"]:has(button[key="tog"]) button {
        height: 20px !important;
        padding: 0px 8px !important;
        font-size: 11px !important;
        border-radius: 16px !important;
        background: rgba(76,175,80,.15) !important;
        border: .5px solid rgba(76,175,80,.35) !important;
        color: #4caf50 !important;
        line-height: 20px !important;
        min-height: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not _display:
        st.info("No reports yet — be the first to report waste!")
    for r in _display:
        sev   = r.get("severity","LOW")
        sta   = r.get("status","OPEN")
        dc    = {"HIGH":"#c62828","MEDIUM":"#e65100","LOW":"#2e7d32"}.get(sev,"#2e7d32")
        types = ", ".join(WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
        desc  = r.get("description","") or r.get("date","")
        ss    = {"HIGH":"background:#ffebee;color:#c62828;",
                 "MEDIUM":"background:#fff3e0;color:#bf360c;",
                 "LOW":"background:#e8f5e9;color:#1b5e20;"}.get(sev,"")
        ts    = ("background:#fff3e0;color:#bf360c;" if sta=="OPEN"
                 else "background:#e8f5e9;color:#1b5e20;")
        st.markdown(f"""
        <div class="cc">
          <div class="cdot" style="background:{dc};"></div>
          <div style="flex:1;min-width:0;">
            <div class="ctype">{types}</div>
            <div class="cloc">{str(desc)[:52]}</div>
            <div class="cmeta">
              <span class="pi" style="{ss}">{sev}</span>
              <span class="pi" style="{ts}">{sta}</span>
              <span class="ctm">{r.get('time','')}</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Pollution intensity heatmap
    st.markdown('<div class="sh" style="padding-top:12px;padding-bottom:8px;">'
                'Pollution Intensity</div>', unsafe_allow_html=True)
    st.markdown(_heatmap(all_r, map_idx=_T["map"]), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DETECT
# ══════════════════════════════════════════════════════════════════════════════
with t_det:
    # pg wrapper with no side padding so banner bleeds full width
    st.markdown('<div style="background:#141d16;padding-bottom:100px;margin-top:-20px;">', unsafe_allow_html=True)
    # Hero banner — full width, flush under tab bar
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a7a4a 0%,#0e4828 100%);
         padding:22px 20px 30px;
         border-radius:0 0 18px 18px;
         clip-path:ellipse(100% 96% at 50% 0%);">
      <div style="text-align:center;font-family:'Georgia',serif;
           line-height:1.6;letter-spacing:.1px;padding-bottom:2px;">
        <span style="font-size:17px;font-weight:400;color:rgba(255,255,255,.8);">
          Be an Earthmender
        </span>
        <span style="font-size:21px;font-weight:700;color:#fff;display:block;
             margin-top:2px;">
          with EarthMender AI
        </span>
      </div>
      <div style="display:flex;justify-content:center;gap:20px;
           margin-top:14px;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="rgba(255,255,255,.95)" stroke-width="2.5" stroke-linecap="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span style="font-size:12px;font-weight:900;color:#fff;letter-spacing:.6px;
                font-family:'Inter',sans-serif;">AI DETECT</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="rgba(255,255,255,.95)" stroke-width="2.5" stroke-linecap="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          <span style="font-size:12px;font-weight:900;color:#fff;letter-spacing:.6px;
                font-family:'Inter',sans-serif;">GPS TAGGED</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="rgba(255,255,255,.95)" stroke-width="2.5" stroke-linecap="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <span style="font-size:12px;font-weight:900;color:#fff;letter-spacing:.6px;
                font-family:'Inter',sans-serif;">INSTANT REPORT</span>
        </div>
      </div>
    </div>
    <div style="padding:0 16px;">
    """, unsafe_allow_html=True)

    mode = st.radio("Source",["📷 Camera","📁 Upload"],
                    horizontal=True, label_visibility="collapsed", key="det_mode")

    if not st.session_state.det_done:
        if mode == "📷 Camera":
            if st.session_state.img_raw is None:
                # Camera toggle — use show_cam_det flag (not cam_open which home resets)
                if not st.session_state.get("show_cam_det", False):
                    st.markdown(f"""
                    <div class="cap">{_IC["cam"]}
                      <div class="cap-t">Tap to open camera</div>
                      <div class="cap-s">Hold steady · Good lighting = better accuracy</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("📷 Open Camera", type="primary",
                                 use_container_width=True, key="open_cam"):
                        st.session_state["show_cam_det"] = True
                        st.rerun()
                else:
                    st.markdown("""
                    <div style="font-size:13px;color:#4caf50;font-weight:700;
                         text-align:center;padding:6px 0 6px;">
                      📷 Camera active — hold steady for best results
                    </div>""", unsafe_allow_html=True)
                    _cam = st.camera_input("", label_visibility="collapsed",
                                           key="cam_widget_det")
                    if _cam:
                        st.session_state.img_raw = Image.open(_cam).convert("RGB")
                        st.session_state["show_cam_det"] = False
                        st.rerun()
                    if st.button("✕ Close Camera", key="close_cam"):
                        st.session_state["show_cam_det"] = False
                        st.rerun()
        else:
            if st.session_state.cam_open:
                st.session_state.cam_open = False
            if st.session_state.img_raw is None:
                st.markdown(f"""
                <div class="cap">{_IC["upl"]}
                  <div class="cap-t">Tap to upload a photo</div>
                  <div class="cap-s">JPG, PNG, WEBP · Max 10MB</div>
                </div>""", unsafe_allow_html=True)
                upl = st.file_uploader("", type=["jpg","jpeg","png","webp"],
                                       label_visibility="collapsed", key="upl")
                if upl:
                    st.session_state.img_raw = Image.open(upl).convert("RGB")
                    st.rerun()

    # Image — original before detect, annotated after
    if st.session_state.img_raw and not st.session_state.det_done:
        st.markdown('<div class="img-wrap">', unsafe_allow_html=True)
        st.image(st.session_state.img_raw,
                 caption="Ready for analysis", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.det_done:
        if st.session_state.img_ann:
            st.markdown('<div class="img-wrap">', unsafe_allow_html=True)
            st.image(st.session_state.img_ann,
                     caption="Detection result", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
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
                        f'<div class="tip-box"><b style="color:#0d47a1;">{lbl}</b>'
                        f'&nbsp;<span class="pi conf-{band}" '
                        f'style="font-size:10px;padding:3px 9px;border-radius:20px;">'
                        f'{band} {conf:.0%}</span>'
                        f'<br><span style="color:#1565c0;font-size:12px;line-height:1.6;">'
                        f'{d["tip"]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="res-warn">⚠️ No plastic waste detected — '
                        'try better lighting or move closer.</div>', unsafe_allow_html=True)

        if st.button("🔄 Scan Another", use_container_width=True, key="scan_again"):
            st.session_state.update({
                "img_raw":None,"img_ann":None,"det_dets":[],
                "det_qual":None,"det_done":False,"cam_open":False,"show_cam_det":False,
            })
            st.rerun()

    if st.session_state.img_raw and not st.session_state.det_done:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:14px;font-weight:800;color:#1a2e1e;'
                    'margin-bottom:8px;">📍 Location</div>', unsafe_allow_html=True)
        lm = st.radio("Loc",["🌐 Auto GPS","✏️ Manual"],
                      horizontal=True, label_visibility="collapsed", key="lm")
        if lm=="🌐 Auto GPS":
            lat,lon = _gps_widget()
        else:
            c1,c2=st.columns(2)
            with c1: lat=st.number_input("Latitude",value=6.524400,format="%.6f",key="mlat")
            with c2: lon=st.number_input("Longitude",value=3.379200,format="%.6f",key="mlon")
        desc = st.text_area("📝 Location description (optional)",
                            placeholder="e.g. Near Ojota bus stop, beside the drainage",
                            max_chars=200, key="desc")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("🔍 Analyse & Submit Report", type="primary",
                     use_container_width=True, key="analyse"):
            with st.spinner("🌍 Analysing image for plastic waste..."):
                ann,dets,qual = det.detect_from_image(st.session_state.img_raw)
                st.session_state.update({
                    "img_ann":ann,"det_dets":dets,"det_qual":qual,"det_done":True,
                })
                if dets:
                    save_report(dets,lat=lat,lon=lon,description=desc,reporter_name=uname)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
with t_map:
    st.session_state.cam_open = False
    st.markdown('<div style="background:#141d16;padding:0 16px 100px;margin-top:-20px;">', unsafe_allow_html=True)
    st.markdown("""<div style="padding:6px 0 8px;">
      <div class="pg-title">🗺️ Live Pollution Map</div>
      <div class="pg-sub">Heatmap · severity · recurrence · time-weighted</div>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    c1.metric("Total",len(all_r)); c2.metric("Open",len(open_r)); c3.metric("Resolved",len(res_r))
    mf=st.radio("Show",["All","Open Only","Resolved Only"],horizontal=True,key="mf")
    md=open_r if mf=="Open Only" else res_r if mf=="Resolved Only" else all_r
    st_folium(build_map(md,all_reports=all_r),width=None,height=430,
              returned_objects=[],key="fmap")
    hs=get_hotspots(open_r) if open_r else []
    if hs:
        st.markdown('<div style="font-size:15px;font-weight:800;color:#e0ece0;margin:14px 0 8px;">🔥 Active Hotspots</div>',unsafe_allow_html=True)
        for i,h in enumerate(hs[:3],1):
            osm=f"https://www.openstreetmap.org/?mlat={h['lat']}&mlon={h['lon']}&zoom=16"
            sev_col = "#f44336" if h.get("count",0) >= 3 else "#ff9800" if h.get("count",0) >= 2 else "#4caf50"
            st.markdown(f"""
            <div style="background:#1e3022;border-radius:12px;padding:12px 14px;
                 margin-bottom:8px;border:.5px solid rgba(255,255,255,.08);">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:13px;font-weight:700;color:#e0ece0;">
                  #{i} &nbsp;<span style="color:#a5d6a7;font-size:12px;font-family:monospace;">
                  {h['lat']:.3f}, {h['lon']:.3f}</span>
                </div>
                <span style="background:{sev_col}22;color:{sev_col};font-size:10px;
                     font-weight:800;padding:3px 8px;border-radius:20px;border:.5px solid {sev_col}55;">
                  {h['count']} report{"s" if h['count']!=1 else ""}
                </span>
              </div>
              <div style="font-size:11px;color:#6a826c;margin-top:4px;">
                {h['items']} items detected &nbsp;·&nbsp;
                <a href="{osm}" target="_blank" style="color:#4caf50;font-weight:600;">
                📍 View on map</a>
              </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LEARN
# ══════════════════════════════════════════════════════════════════════════════
with t_learn:
    st.session_state.cam_open = False
    render_education_tab()


# ══════════════════════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════════════════════
with t_stats:
    st.session_state.cam_open = False
    render_full_dashboard(
        get_report_stats(load_reports()),
        get_hotspots(load_reports()),
        load_reports(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# OPS
# ══════════════════════════════════════════════════════════════════════════════
if t_ops:
    with t_ops:
        st.session_state.cam_open = False
        st.markdown('<div class="pg" style="padding-top:0;">',unsafe_allow_html=True)
        st.markdown('<div class="pg-hdr"><div class="pg-title">🏢 Operator Dashboard</div></div>',
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
        st.markdown(f"#### 🟠 Open Cases ({len(fl)})")
        if not fl: st.success("All clear — no open cases!")
        for r in fl:
            sev=r.get("severity","LOW"); icon={"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(sev,"🟢")
            types=", ".join(WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
            osm=f"https://www.openstreetmap.org/?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17"
            with st.expander(f"{icon} #{r['id']} — {sev} — {types}",expanded=(sev=="HIGH")):
                c1,c2=st.columns([2,1])
                with c1:
                    st.write(f"**Waste:** {types}")
                    st.write(f"**Reporter:** {r.get('reporter','Anonymous')}")
                    if r.get("description"): st.write(f"**Location:** {r['description']}")
                with c2:
                    st.code(f"{r['latitude']:.5f}\n{r['longitude']:.5f}")
                    st.markdown(f"[📍 Open Map]({osm})")
                note=st.text_input("Resolution note","Area cleaned.",key=f"note_{r['id']}")
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
        st.markdown("</div>",unsafe_allow_html=True)
