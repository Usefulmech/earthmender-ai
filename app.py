"""
EarthMender AI — Main Application (Redesigned)
================================================
Run: streamlit run app.py

Features in this version:
  - Demo login screen (session-based, no backend needed)
  - OPay/PalmPay-inspired green UI with CSS injection
  - Responsive image capture with quality feedback
  - Real-time GPS watchPosition
  - Enhanced heatmap (time decay + recurrence weighting)
  - Smarter detection (per-class conf thresholds + NMS + confidence bands)
  - Speed optimisations for Render CPU deployment

Final 5-Class System:
  plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from phase1_detection.detector  import PlasticDetector, confidence_band
from phase2_reporting.reporter  import (
    load_reports, save_report, resolve_report, reopen_report,
    get_open_reports, get_resolved_reports, get_report_stats,
    render_gps_capture, get_gps_coords_from_inputs, get_manual_location,
)
from phase3_map.mapper          import build_map, get_hotspots
from phase4_dashboard.dashboard import render_full_dashboard
from phase5_education.educator  import render_education_tab

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EarthMender AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── GLOBAL CSS — OPay/PalmPay inspired design system ─────────────────────────
st.markdown("""
<style>
  /* ── Reset & base ── */
  [data-testid="stAppViewContainer"] { background: #f5f7f5; }
  [data-testid="stHeader"] { display: none; }
  [data-testid="stToolbar"] { display: none; }
  [data-testid="stSidebar"] { display: none; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  footer { display: none; }

  /* ── Top bar ── */
  .em-topbar {
    background: #1a7a4a;
    padding: 14px 20px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 999;
  }
  .em-topbar-left { display: flex; align-items: center; gap: 10px; }
  .em-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 600; color: #fff;
  }
  .em-greeting { color: rgba(255,255,255,0.7); font-size: 11px; line-height: 1.2; }
  .em-username { color: #fff; font-size: 15px; font-weight: 600; }
  .em-topbar-right { display: flex; gap: 8px; }
  .em-icon-btn {
    width: 34px; height: 34px; border-radius: 50%;
    background: rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; cursor: pointer;
  }

  /* ── Hero card ── */
  .em-hero {
    background: linear-gradient(160deg, #1a7a4a 0%, #2e7d32 100%);
    padding: 0 20px 24px;
  }
  .em-balance-card {
    background: rgba(255,255,255,0.13);
    border-radius: 14px;
    padding: 16px 18px;
    border: 0.5px solid rgba(255,255,255,0.22);
    margin-bottom: 12px;
  }
  .em-balance-label {
    color: rgba(255,255,255,0.7); font-size: 11px;
    margin-bottom: 6px;
  }
  .em-balance-row {
    display: flex; align-items: center;
    justify-content: space-between;
  }
  .em-balance-val { color: #fff; font-size: 24px; font-weight: 700; }
  .em-report-pill {
    background: #fff; color: #1a7a4a;
    border-radius: 20px; padding: 7px 16px;
    font-size: 12px; font-weight: 600;
    border: none; cursor: pointer;
  }
  .em-sub-stats {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 8px;
  }
  .em-sub-stat {
    background: rgba(255,255,255,0.12);
    border-radius: 10px; padding: 10px 6px; text-align: center;
  }
  .em-sub-val { color: #fff; font-size: 16px; font-weight: 700; }
  .em-sub-label { color: rgba(255,255,255,0.65); font-size: 9px; margin-top: 2px; }

  /* ── Page body ── */
  .em-body { background: #fff; padding: 0 16px 100px; }

  /* ── Section ── */
  .em-section { padding: 18px 0 8px; }
  .em-section-header {
    display: flex; align-items: center;
    justify-content: space-between; margin-bottom: 12px;
  }
  .em-section-title { font-size: 14px; font-weight: 600; color: #1a1a1a; }
  .em-see-all { font-size: 12px; color: #1a7a4a; cursor: pointer; }

  /* ── Quick actions ── */
  .em-quick-grid {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 10px;
  }
  .em-qa-item {
    display: flex; flex-direction: column;
    align-items: center; gap: 6px; cursor: pointer;
  }
  .em-qa-icon {
    width: 52px; height: 52px; border-radius: 14px;
    display: flex; align-items: center;
    justify-content: center; font-size: 22px;
  }
  .em-qa-label {
    font-size: 10px; color: #555; text-align: center; font-weight: 500;
  }

  /* ── Alert strip ── */
  .em-alert {
    background: #fff3e0;
    border-radius: 10px;
    padding: 10px 14px;
    display: flex; align-items: center; gap: 10px;
    border: 0.5px solid #ffe0b2;
    margin: 6px 0 14px;
  }
  .em-alert-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #ff9800; flex-shrink: 0;
  }
  .em-alert-text { font-size: 12px; color: #e65100; flex: 1; }
  .em-alert-cta { font-size: 12px; color: #1a7a4a; font-weight: 600; cursor: pointer; }

  /* ── Case card ── */
  .em-case-card {
    background: #fafafa;
    border-radius: 12px;
    padding: 14px;
    border: 0.5px solid #efefef;
    display: flex; align-items: flex-start; gap: 10px;
    margin-bottom: 8px;
    cursor: pointer;
  }
  .em-case-dot {
    width: 9px; height: 9px; border-radius: 50%;
    margin-top: 4px; flex-shrink: 0;
  }
  .em-case-type { font-size: 13px; font-weight: 600; color: #1a1a1a; }
  .em-case-loc { font-size: 11px; color: #888; margin-top: 2px; }
  .em-case-meta { display: flex; align-items: center; gap: 6px; margin-top: 6px; }
  .em-pill {
    font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 600;
  }
  .em-case-time { font-size: 10px; color: #aaa; margin-left: auto; }

  /* ── Confidence band tags ── */
  .conf-certain { background:#e8f5e9; color:#1b5e20; }
  .conf-likely  { background:#fff8e1; color:#f57f17; }
  .conf-possible{ background:#f5f5f5; color:#757575; }

  /* ── Bottom nav ── */
  .em-bottomnav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #fff;
    border-top: 0.5px solid #efefef;
    display: flex; z-index: 998;
    padding-bottom: env(safe-area-inset-bottom);
  }
  .em-nav-item {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; gap: 3px;
    padding: 10px 4px 12px; cursor: pointer;
  }
  .em-nav-icon {
    width: 24px; height: 24px; font-size: 18px;
    display: flex; align-items: center; justify-content: center;
  }
  .em-nav-label { font-size: 10px; color: #aaa; }
  .em-nav-item.active .em-nav-label { color: #1a7a4a; font-weight: 600; }
  .em-nav-fab {
    width: 48px; height: 48px; border-radius: 50%;
    background: #1a7a4a; margin-top: -14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; color: #fff;
    border: 3px solid #fff;
    box-shadow: 0 2px 8px rgba(26,122,74,0.4);
  }

  /* ── Detect tab image zone ── */
  .em-capture-zone {
    border: 2px dashed #c8e6c9;
    border-radius: 16px;
    padding: 32px 20px;
    text-align: center;
    background: #f9fdf9;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .em-capture-zone:hover { border-color: #1a7a4a; }
  .em-capture-icon { font-size: 48px; margin-bottom: 8px; }
  .em-capture-text { font-size: 14px; color: #555; }
  .em-capture-sub  { font-size: 11px; color: #aaa; margin-top: 4px; }

  /* ── Detection result ── */
  .em-detect-success {
    background: #e8f5e9; border-left: 4px solid #1a7a4a;
    padding: 14px 16px; border-radius: 10px; margin: 12px 0;
  }
  .em-detect-warn {
    background: #fff3e0; border-left: 4px solid #ff9800;
    padding: 14px 16px; border-radius: 10px; margin: 12px 0;
  }
  .em-tip-box {
    background: #e3f2fd; border-left: 4px solid #1565c0;
    padding: 12px 14px; border-radius: 10px;
    font-size: 13px; margin: 6px 0;
  }

  /* ── Streamlit overrides ── */
  div[data-testid="stMetric"] {
    background: #f9f9f9; border-radius: 10px;
    padding: 12px; border: 0.5px solid #efefef;
  }
  .stTabs [data-baseweb="tab-list"] {
    background: #fff;
    border-bottom: 1.5px solid #e8f5e9;
    gap: 0; padding: 0 16px;
  }
  .stTabs [data-baseweb="tab"] {
    padding: 12px 16px;
    font-size: 13px; font-weight: 500;
    color: #888;
    border-bottom: 2px solid transparent;
  }
  .stTabs [aria-selected="true"] {
    color: #1a7a4a !important;
    border-bottom: 2px solid #1a7a4a !important;
  }
  .stButton > button {
    border-radius: 24px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
  }
  .stButton > button[kind="primary"] {
    background: #1a7a4a !important;
    border-color: #1a7a4a !important;
  }
</style>
""", unsafe_allow_html=True)

# ─── WASTE LABELS ─────────────────────────────────────────────────────────────
WASTE_LABELS = {
    "plastic_bottle":  "🍶 Plastic Bottle",
    "water_sachet":    "💧 Water Sachet",
    "polythene_bag":   "🛍️ Polythene Bag",
    "disposable":      "🥤 Disposable",
    "waste_container": "🛢️ Waste Container",
}

# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "logged_in":   False,
        "user_name":   "",
        "user_role":   "Citizen",
        "user_initials": "?",
        "active_tab":  "Home",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()

# ══════════════════════════════════════════════════════════════════════════════
# DEMO LOGIN SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown("""
    <div style='min-height:100vh;background:linear-gradient(160deg,#1a7a4a,#2e7d32);
         display:flex;flex-direction:column;align-items:center;
         justify-content:center;padding:40px 24px;'>
      <div style='font-size:56px;margin-bottom:8px;'>🌍</div>
      <div style='font-size:28px;font-weight:800;color:#fff;margin-bottom:4px;'>
        EarthMender AI
      </div>
      <div style='font-size:14px;color:rgba(255,255,255,0.75);margin-bottom:40px;'>
        Detect · Report · Learn · Act
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div style='background:#fff;border-radius:20px;padding:28px 24px;
             max-width:400px;margin:0 auto;margin-top:-80px;
             box-shadow:0 8px 32px rgba(0,0,0,0.12);'>
          <div style='font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:4px;'>
            Welcome 👋
          </div>
          <div style='font-size:13px;color:#888;margin-bottom:24px;'>
            Demo mode — no account needed
          </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            name = st.text_input(
                "Your name",
                placeholder="e.g. Adeniji Yusuf",
                key="login_name",
            )
            role = st.selectbox(
                "I am a",
                ["Citizen — I want to report waste",
                 "Operator — I manage waste collection"],
                key="login_role",
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Enter EarthMender AI →", type="primary",
                         use_container_width=True):
                if name.strip():
                    st.session_state.logged_in    = True
                    st.session_state.user_name    = name.strip()
                    st.session_state.user_role    = (
                        "Operator" if "Operator" in role else "Citizen"
                    )
                    # Initials for avatar
                    parts = name.strip().split()
                    st.session_state.user_initials = (
                        (parts[0][0] + parts[-1][0]).upper()
                        if len(parts) >= 2 else parts[0][:2].upper()
                    )
                    st.rerun()
                else:
                    st.warning("Please enter your name to continue.")

            st.markdown("""
            <div style='text-align:center;margin-top:16px;font-size:11px;color:#bbb;'>
              🔒 Demo session only — no data is stored permanently
            </div>
            """, unsafe_allow_html=True)


# Show login if not authenticated
if not st.session_state.logged_in:
    show_login()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP — only reached after login
# ══════════════════════════════════════════════════════════════════════════════

# ─── LOAD MODEL (cached + warmed up) ─────────────────────────────────────────
@st.cache_resource
def get_detector():
    return PlasticDetector()

detector = get_detector()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
all_reports    = load_reports()
open_r         = get_open_reports()
resolved_r     = get_resolved_reports()
stats          = get_report_stats(all_reports)
high_open      = sum(1 for r in open_r if r.get("severity") == "HIGH")

# ─── TOP BAR ──────────────────────────────────────────────────────────────────
initials = st.session_state.user_initials
name     = st.session_state.user_name
role     = st.session_state.user_role

st.markdown(f"""
<div class="em-topbar">
  <div class="em-topbar-left">
    <div class="em-avatar">{initials}</div>
    <div>
      <div class="em-greeting">Welcome back,</div>
      <div class="em-username">{name}</div>
    </div>
  </div>
  <div class="em-topbar-right">
    <div class="em-icon-btn">🔔</div>
    <div class="em-icon-btn">🔍</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── HERO SECTION ─────────────────────────────────────────────────────────────
total    = stats.get("total", 0)
open_c   = stats.get("open", 0)
resolved = stats.get("resolved", 0)
items    = stats.get("items", 0)
rate     = f"{int(resolved/total*100)}%" if total > 0 else "0%"

st.markdown(f"""
<div class="em-hero">
  <div class="em-balance-card">
    <div class="em-balance-label">🛡️ Community Waste Reports</div>
    <div class="em-balance-row">
      <div class="em-balance-val">{total} Cases</div>
      <div class="em-report-pill">+ Report Waste</div>
    </div>
  </div>
  <div class="em-sub-stats">
    <div class="em-sub-stat">
      <div class="em-sub-val" style="color:#ffb74d;">{open_c}</div>
      <div class="em-sub-label">Open</div>
    </div>
    <div class="em-sub-stat">
      <div class="em-sub-val" style="color:#81c784;">{resolved}</div>
      <div class="em-sub-label">Resolved</div>
    </div>
    <div class="em-sub-stat">
      <div class="em-sub-val">{rate}</div>
      <div class="em-sub-label">Resolution</div>
    </div>
    <div class="em-sub-stat">
      <div class="em-sub-val">{items}</div>
      <div class="em-sub-label">Items Found</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab_labels = ["🏠 Home", "🔍 Detect", "🗺️ Map", "📚 Learn", "📊 Stats"]
if role == "Operator":
    tab_labels.append("🏢 Ops")

tabs = st.tabs(tab_labels)
tab_home   = tabs[0]
tab_detect = tabs[1]
tab_map    = tabs[2]
tab_learn  = tabs[3]
tab_stats  = tabs[4]
tab_ops    = tabs[5] if role == "Operator" else None


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — HOME
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.markdown('<div class="em-body">', unsafe_allow_html=True)

    # Alert strip for high-severity open cases
    if high_open > 0:
        st.markdown(f"""
        <div class="em-section">
          <div class="em-alert">
            <div class="em-alert-dot"></div>
            <div class="em-alert-text">
              {high_open} HIGH severity case{'s' if high_open>1 else ''} need urgent attention
            </div>
            <div class="em-alert-cta">View →</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Quick actions
    st.markdown("""
    <div class="em-section">
      <div class="em-section-header">
        <div class="em-section-title">Quick Actions</div>
      </div>
      <div class="em-quick-grid">
        <div class="em-qa-item">
          <div class="em-qa-icon" style="background:#e8f5e9;">🔍</div>
          <div class="em-qa-label">Detect</div>
        </div>
        <div class="em-qa-item">
          <div class="em-qa-icon" style="background:#e3f2fd;">🗺️</div>
          <div class="em-qa-label">Map</div>
        </div>
        <div class="em-qa-item">
          <div class="em-qa-icon" style="background:#fff3e0;">📊</div>
          <div class="em-qa-label">Stats</div>
        </div>
        <div class="em-qa-item">
          <div class="em-qa-icon" style="background:#f3e5f5;">📚</div>
          <div class="em-qa-label">Learn</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Recent reports feed
    st.markdown("""
    <div class="em-section">
      <div class="em-section-header">
        <div class="em-section-title">Recent Reports</div>
        <div class="em-see-all">See all</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    recent = sorted(all_reports,
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True)[:5]

    if not recent:
        st.info("No reports yet — be the first to report waste in your area!")
    else:
        for r in recent:
            sev    = r.get("severity", "LOW")
            status = r.get("status",   "OPEN")
            dot_c  = {"HIGH":"#f44336","MEDIUM":"#ff9800","LOW":"#4caf50"}.get(sev,"#4caf50")
            types  = ", ".join(
                WASTE_LABELS.get(t, t) for t in r.get("waste_types", []))
            desc   = r.get("description", "") or r.get("date","")

            sev_pill_style = {
                "HIGH":   "background:#ffebee;color:#c62828;",
                "MEDIUM": "background:#fff8e1;color:#f57f17;",
                "LOW":    "background:#f1f8e9;color:#33691e;",
            }.get(sev, "")

            sta_pill_style = (
                "background:#fff3e0;color:#e65100;"
                if status == "OPEN"
                else "background:#e8f5e9;color:#1b5e20;"
            )

            st.markdown(f"""
            <div class="em-case-card">
              <div class="em-case-dot" style="background:{dot_c};"></div>
              <div style="flex:1;min-width:0;">
                <div class="em-case-type">{types}</div>
                <div class="em-case-loc">{desc[:60]}</div>
                <div class="em-case-meta">
                  <span class="em-pill" style="{sev_pill_style}">{sev}</span>
                  <span class="em-pill" style="{sta_pill_style}">{status}</span>
                  <span class="em-case-time">{r.get('time','')}</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DETECT & REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_detect:
    st.markdown('<div class="em-body">', unsafe_allow_html=True)
    st.markdown("""
    <div class="em-section">
      <div class="em-section-title">📸 Detect Plastic Waste</div>
      <div style="font-size:12px;color:#888;margin-top:4px;">
        Upload a photo or use your camera — AI identifies waste type instantly
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Input mode selector ───────────────────────────────────────────────────
    input_mode = st.radio(
        "Input source",
        ["📁 Upload Photo", "📷 Use Camera"],
        horizontal=True,
        label_visibility="collapsed",
    )

    image = None

    if input_mode == "📁 Upload Photo":
        st.markdown("""
        <div class="em-capture-zone">
          <div class="em-capture-icon">📁</div>
          <div class="em-capture-text">Tap to upload a photo</div>
          <div class="em-capture-sub">JPG, PNG, WEBP · Max 10MB</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Choose photo",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded:
            image = Image.open(uploaded).convert("RGB")

    else:
        st.markdown("""
        <div class="em-capture-zone">
          <div class="em-capture-icon">📷</div>
          <div class="em-capture-text">Point camera at the waste</div>
          <div class="em-capture-sub">Hold steady for best results</div>
        </div>
        """, unsafe_allow_html=True)
        captured = st.camera_input(
            "Camera",
            label_visibility="collapsed",
        )
        if captured:
            image = Image.open(captured).convert("RGB")

    # ── Preview ───────────────────────────────────────────────────────────────
    if image:
        col_prev, col_info = st.columns([2, 1])
        with col_prev:
            st.image(image, caption="Your photo", use_column_width=True)
        with col_info:
            st.markdown(f"""
            <div style='background:#f5f5f5;border-radius:10px;padding:12px;font-size:12px;'>
              <div style='color:#888;margin-bottom:4px;'>Photo details</div>
              <div><b>Size:</b> {image.width}×{image.height}px</div>
              <div><b>Mode:</b> {image.mode}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Location ──────────────────────────────────────────────────────────────
    if image:
        st.markdown("---")
        st.markdown("""
        <div class="em-section-title" style="margin-bottom:8px;">📍 Location</div>
        """, unsafe_allow_html=True)

        loc_mode = st.radio(
            "Location source",
            ["🌐 Auto GPS", "✏️ Manual Entry"],
            horizontal=True,
            label_visibility="collapsed",
        )

        lat, lon = 6.5244, 3.3792

        if loc_mode == "🌐 Auto GPS":
            render_gps_capture()
            st.caption("GPS coordinates are captured automatically above. "
                       "Copy them into the fields below if needed:")
            lat, lon = get_gps_coords_from_inputs()
        else:
            lat, lon = get_manual_location()

        description = st.text_area(
            "📝 Location description (optional)",
            placeholder="e.g. Near Ojota bus stop, beside the drainage",
            max_chars=200,
            label_visibility="visible",
        )

        st.markdown("---")

        # ── Detect button ─────────────────────────────────────────────────────
        if st.button("🔍 Analyse & Submit Report",
                     type="primary", use_container_width=True):

            with st.spinner("🌍 Analysing image for plastic waste..."):
                annotated, detections, quality = detector.detect_from_image(image)
                summary = detector.summarise(detections)

            # Quality warning
            if quality["quality"] == "poor":
                st.markdown(
                    f'<div class="em-detect-warn">'
                    f'⚠️ {quality["message"]}</div>',
                    unsafe_allow_html=True,
                )

            if summary["found"]:
                st.markdown(
                    f'<div class="em-detect-success">'
                    f'✅ <b>{summary["message"]}</b></div>',
                    unsafe_allow_html=True,
                )
                st.image(annotated,
                         caption="Detection result with bounding boxes",
                         use_column_width=True)

                # Per-class disposal tips + confidence bands
                seen = set()
                for det in detections:
                    if det["label"] not in seen:
                        seen.add(det["label"])
                        label     = WASTE_LABELS.get(det["label"],
                                    det["label"].replace("_"," ").title())
                        conf      = det["confidence"]
                        band      = det["confidence_band"]
                        band_cls  = f"conf-{band.lower()}"
                        st.markdown(
                            f'<div class="em-tip-box">'
                            f'🇳🇬 <b>{label}</b> &nbsp;'
                            f'<span class="em-pill {band_cls}">'
                            f'{band} {conf:.0%}</span><br>'
                            f'{det["tip"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Save report
                report = save_report(
                    detections, lat=lat, lon=lon,
                    description=description,
                    reporter_name=st.session_state.user_name,
                )
                if report:
                    types_str = ", ".join(
                        WASTE_LABELS.get(t, t)
                        for t in report.get("waste_types", [])
                    )
                    st.success(
                        f"📋 **Case #{report['id']} opened!**  \n"
                        f"Detected: {types_str}  \n"
                        f"Severity: **{report['severity']}** | "
                        f"GPS: `{lat:.5f}, {lon:.5f}`"
                    )
            else:
                st.markdown(
                    '<div class="em-detect-warn">'
                    '⚠️ <b>No plastic waste detected.</b><br>'
                    'Try a clearer photo, better lighting, '
                    'or move closer to the waste item.'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.image(annotated, use_column_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — POLLUTION MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    st.markdown('<div class="em-body">', unsafe_allow_html=True)
    st.markdown("""
    <div class="em-section">
      <div class="em-section-title">🗺️ Live Pollution Map</div>
      <div style="font-size:12px;color:#888;margin-top:4px;margin-bottom:12px;">
        Heatmap weighted by severity, recurrence, and time
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("📋 Total", len(all_reports))
    col_m2.metric("🟠 Open",  len(open_r))
    col_m3.metric("✅ Resolved", len(resolved_r))

    map_filter = st.radio(
        "Show",
        ["All", "Open Only", "Resolved Only"],
        horizontal=True,
    )
    map_data = (
        open_r     if map_filter == "Open Only"     else
        resolved_r if map_filter == "Resolved Only" else
        all_reports
    )

    # Pass full dataset for recurrence calculation
    pollution_map = build_map(map_data, all_reports=all_reports)
    st_folium(pollution_map, width=None, height=500, returned_objects=[])

    # Hotspots
    if open_r:
        hotspots = get_hotspots(open_r)
        if hotspots:
            st.markdown("""
            <div class="em-section">
              <div class="em-section-title">🔥 Active Hotspots</div>
            </div>
            """, unsafe_allow_html=True)
            for i, h in enumerate(hotspots[:3], 1):
                osm = (f"https://www.openstreetmap.org/"
                       f"?mlat={h['lat']}&mlon={h['lon']}&zoom=16")
                st.markdown(
                    f"**#{i}** `{h['lat']:.3f}, {h['lon']:.3f}` — "
                    f"{h['count']} report(s), {h['items']} items  "
                    f"[📍 Map]({osm})"
                )

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LEARN
# ══════════════════════════════════════════════════════════════════════════════
with tab_learn:
    render_education_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STATS / DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_stats:
    all_reports = load_reports()
    stats       = get_report_stats(all_reports)
    hotspots    = get_hotspots(all_reports)
    render_full_dashboard(stats, hotspots, all_reports)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — OPERATOR VIEW (only visible when role = Operator)
# ══════════════════════════════════════════════════════════════════════════════
if tab_ops is not None:
    with tab_ops:
        st.markdown('<div class="em-body">', unsafe_allow_html=True)
        st.markdown("""
        <div class="em-section">
          <div class="em-section-title">🏢 Operator Dashboard</div>
          <div style="font-size:12px;color:#888;margin-top:4px;">
            Review open cases and mark them resolved
          </div>
        </div>
        """, unsafe_allow_html=True)

        open_cases     = get_open_reports()
        resolved_cases = get_resolved_reports()
        total_cases    = len(open_cases) + len(resolved_cases)

        k1, k2, k3 = st.columns(3)
        k1.metric("🟠 Open",    len(open_cases))
        k2.metric("✅ Resolved", len(resolved_cases))
        rate_pct = int(len(resolved_cases) / total_cases * 100) if total_cases else 0
        k3.metric("📈 Rate", f"{rate_pct}%")

        st.divider()

        # Filter + sort
        cf1, cf2 = st.columns([1, 2])
        with cf1:
            sev_filter = st.selectbox("Severity", ["All","HIGH","MEDIUM","LOW"])
        with cf2:
            sort_order = st.radio(
                "Sort", ["Severity (HIGH first)", "Newest first"],
                horizontal=True)

        filtered = (
            open_cases if sev_filter == "All"
            else [r for r in open_cases if r.get("severity") == sev_filter]
        )
        if sort_order == "Severity (HIGH first)":
            filtered = sorted(filtered,
                key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(
                    x.get("severity"), 3))
        else:
            filtered = sorted(filtered,
                key=lambda x: x.get("timestamp",""), reverse=True)

        st.markdown(f"#### 🟠 Open Cases ({len(filtered)})")

        if not filtered:
            st.success("✅ No open cases. Great work!")
        else:
            for r in filtered:
                sev   = r.get("severity","LOW")
                types = ", ".join(
                    WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
                icon  = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(sev,"🟢")
                osm   = (f"https://www.openstreetmap.org/"
                         f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")

                with st.expander(
                    f"{icon} #{r['id']} — {sev} — {types} — "
                    f"{r.get('date','')} {r.get('time','')}",
                    expanded=(sev=="HIGH"),
                ):
                    c1, c2 = st.columns([2,1])
                    with c1:
                        st.write(f"**Waste:** {types}")
                        st.write(f"**Items:** {r.get('item_count',0)}")
                        st.write(f"**Reporter:** {r.get('reporter','Anonymous')}")
                        if r.get("description"):
                            st.write(f"**Location:** {r['description']}")
                    with c2:
                        st.code(
                            f"{r['latitude']:.5f}\n{r['longitude']:.5f}")
                        st.markdown(f"[📍 Map]({osm})")

                    note = st.text_input(
                        f"Resolution note #{r['id']}:",
                        value="Area cleaned and waste collected.",
                        key=f"note_{r['id']}",
                    )
                    if st.button(
                        f"✅ Resolve #{r['id']}",
                        key=f"resolve_{r['id']}", type="primary"
                    ):
                        if resolve_report(
                            r["id"],
                            resolved_by=st.session_state.user_name,
                            note=note
                        ):
                            st.success(f"Case #{r['id']} resolved!")
                            st.rerun()

        st.divider()
        st.markdown(f"#### ✅ Recently Resolved ({len(resolved_cases)})")

        if not resolved_cases:
            st.info("No resolved cases yet.")
        else:
            for r in sorted(resolved_cases,
                    key=lambda x: x.get("resolved_at",""), reverse=True)[:8]:
                types = ", ".join(
                    WASTE_LABELS.get(t,t) for t in r.get("waste_types",[]))
                res_date = (r.get("resolved_at") or "")[:10]
                with st.expander(f"✅ #{r['id']} — {types} — {res_date}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**By:** {r.get('resolved_by','Operator')}")
                        st.write(f"**Note:** {r.get('resolution_note','—')}")
                    with c2:
                        st.write(f"**GPS:** {r['latitude']:.5f}, {r['longitude']:.5f}")
                        osm = (f"https://www.openstreetmap.org/"
                               f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")
                        st.markdown(f"[📍 Location]({osm})")
                    if st.button(f"↩️ Reopen #{r['id']}",
                                 key=f"reopen_{r['id']}"):
                        reopen_report(r["id"])
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:24px 16px 120px;font-size:11px;color:#bbb;'>
  🌍 <b style='color:#1a7a4a;'>EarthMender AI</b> ·
  3MTT NextGen Knowledge Showcase 2026 ·
  Environment Pillar ·
  YOLOv8 + Streamlit + OpenStreetMap
</div>
""", unsafe_allow_html=True)
