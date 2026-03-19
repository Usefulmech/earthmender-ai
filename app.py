"""
EarthMender AI — Main Application
===================================
Run: streamlit run app.py

5 Tabs:
  1. 🔍 Detect & Report  — YOLOv8 detection + citizen waste report
  2. 🗺️ Pollution Map    — Live interactive map + heatmap
  3. 📚 Learn            — Sorting guide, recycling tips, quiz
  4. 📊 Dashboard        — 3-level analytics intelligence
  5. 🏢 Operator View    — Open cases, resolve workflow

Final 5-Class System:
  plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from phase1_detection.detector  import PlasticDetector
from phase2_reporting.reporter  import (
    load_reports, save_report, resolve_report, reopen_report,
    get_open_reports, get_resolved_reports, get_report_stats,
    render_gps_capture, get_manual_location,
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

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { text-align:center;color:#1a7a4a;font-size:2.6rem;font-weight:800;margin-bottom:0; }
    .sub-title  { text-align:center;color:#666;font-size:1rem;margin-bottom:1.5rem; }
    .detect-box { background:#e8f5e9;border-left:5px solid #1a7a4a;padding:16px;border-radius:8px;margin:12px 0; }
    .warn-box   { background:#fff3e0;border-left:5px solid #ff9800;padding:16px;border-radius:8px;margin:12px 0; }
    .tip-box    { background:#e3f2fd;border-left:5px solid #1565c0;padding:12px;border-radius:6px;font-size:14px;margin:6px 0; }
    div[data-testid="stMetric"] { background:#f9f9f9;border-radius:8px;padding:12px;border:1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🌍 EarthMender AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">'
    'Detect · Report · Learn · Act — '
    'Powered by YOLOv8 + Community Reporting + OpenStreetMap'
    '</p>',
    unsafe_allow_html=True,
)

# ─── LOAD MODEL ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_detector():
    return PlasticDetector()

detector = get_detector()

# ─── WASTE TYPE LABELS (used across all tabs) ─────────────────────────────────
WASTE_LABELS = {
    "plastic_bottle":  "🍶 Plastic Bottle",
    "water_sachet":    "💧 Water Sachet",
    "polythene_bag":   "🛍️ Polythene Bag",
    "disposable":      "🥤 Disposable",
    "waste_container": "🛢️ Waste Container",
}

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Detect & Report",
    "🗺️ Pollution Map",
    "📚 Learn",
    "📊 Dashboard",
    "🏢 Operator View",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DETECT & REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📸 Detect Plastic Waste")
    st.caption(
        "Upload a photo or use your camera. The AI identifies the waste type "
        "and logs a geo-tagged community report."
    )

    col_upload, col_preview = st.columns([1, 1])
    image = None

    with col_upload:
        input_mode = st.radio(
            "Input source:",
            ["📁 Upload Image", "📷 Use Camera"],
            horizontal=True,
        )
        if input_mode == "📁 Upload Image":
            uploaded = st.file_uploader(
                "Choose an image...",
                type=["jpg", "jpeg", "png", "webp"],
            )
            if uploaded:
                image = Image.open(uploaded).convert("RGB")
        else:
            captured = st.camera_input("Point camera at the waste")
            if captured:
                image = Image.open(captured).convert("RGB")

    with col_preview:
        if image:
            st.image(image, caption="Your image", use_column_width=True)
        else:
            st.info("Upload or capture an image to get started.")

    if image:
        st.divider()
        st.markdown("#### 📍 Location")
        loc_mode = st.radio(
            "Location source:",
            ["🌐 Auto GPS (browser)", "✏️ Manual Entry"],
            horizontal=True,
        )
        lat, lon = 6.5244, 3.3792  # Lagos default

        if loc_mode == "🌐 Auto GPS (browser)":
            render_gps_capture()
            st.caption("Copy the coordinates shown above into these fields:")
            col_lat, col_lon = st.columns(2)
            with col_lat:
                lat_in = st.text_input("Latitude:",  placeholder="e.g. 6.524400")
            with col_lon:
                lon_in = st.text_input("Longitude:", placeholder="e.g. 3.379200")
            if lat_in and lon_in:
                try:
                    lat, lon = float(lat_in), float(lon_in)
                except ValueError:
                    st.warning("⚠️ Invalid coordinates — Lagos default will be used.")
        else:
            lat, lon = get_manual_location()

        description = st.text_area(
            "📝 Describe the location (optional):",
            placeholder="e.g. Near Ojota bus stop, beside the main drainage",
            max_chars=200,
        )

        st.divider()
        if st.button("🔍 Detect & Submit Report", type="primary",
                     use_container_width=True):
            with st.spinner("Running YOLOv8 detection..."):
                annotated, detections = detector.detect_from_image(image)
                summary = detector.summarise(detections)

            if summary["found"]:
                st.markdown(
                    f'<div class="detect-box"><b>✅ {summary["message"]}</b></div>',
                    unsafe_allow_html=True,
                )
                st.image(annotated, caption="Detection result with bounding boxes",
                         use_column_width=True)

                # Disposal tip per unique detected class
                seen = set()
                for det in detections:
                    if det["label"] not in seen:
                        seen.add(det["label"])
                        label = WASTE_LABELS.get(det["label"],
                                det["label"].replace("_", " ").title())
                        st.markdown(
                            f'<div class="tip-box">'
                            f'🇳🇬 <b>{label} — Disposal Tip:</b><br>'
                            f'{det["tip"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                report = save_report(
                    detections, lat=lat, lon=lon,
                    description=description,
                )
                if report:
                    types_str = ", ".join(
                        WASTE_LABELS.get(t, t)
                        for t in report.get("waste_types", [])
                    )
                    st.success(
                        f"📋 **Case #{report['id']} opened!**  \n"
                        f"Detected: **{types_str}**  \n"
                        f"Severity: **{report['severity']}** | "
                        f"Status: **OPEN** | "
                        f"GPS: `{lat:.5f}, {lon:.5f}`  \n"
                        f"Visible on the Pollution Map and Operator Dashboard."
                    )
            else:
                st.markdown(
                    '<div class="warn-box">'
                    '⚠️ <b>No plastic waste detected.</b><br>'
                    'Try a clearer photo, better lighting, or move closer to the waste.'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.image(annotated, caption="No detections found",
                         use_column_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — POLLUTION MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    all_reports = load_reports()
    open_r      = get_open_reports()
    resolved_r  = get_resolved_reports()

    st.markdown("### 🗺️ Live Pollution Map")
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 Total Reports", len(all_reports))
    c2.metric("🟠 Open Cases",    len(open_r))
    c3.metric("✅ Resolved",       len(resolved_r))

    map_filter = st.radio(
        "Show reports:",
        ["All Reports", "Open Only", "Resolved Only"],
        horizontal=True,
    )
    map_data = (
        open_r     if map_filter == "Open Only"     else
        resolved_r if map_filter == "Resolved Only" else
        all_reports
    )

    pollution_map = build_map(map_data)
    st_folium(pollution_map, width=None, height=520, returned_objects=[])

    if open_r:
        hotspots = get_hotspots(open_r)
        if hotspots:
            st.markdown("#### 🔥 Active Hotspot Zones")
            for i, h in enumerate(hotspots[:3], 1):
                osm = (f"https://www.openstreetmap.org/"
                       f"?mlat={h['lat']}&mlon={h['lon']}&zoom=16")
                st.markdown(
                    f"**#{i}** `{h['lat']:.3f}, {h['lon']:.3f}` — "
                    f"{h['count']} open report(s), {h['items']} items  "
                    f"[📍 View on map]({osm})"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LEARN
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    render_education_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    all_reports = load_reports()
    stats       = get_report_stats(all_reports)
    hotspots    = get_hotspots(all_reports)
    render_full_dashboard(stats, hotspots, all_reports)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — OPERATOR VIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 🏢 Waste Operator Dashboard")
    st.caption(
        "Open cases from citizen reports. Review each location and mark "
        "resolved once your team has cleaned the area."
    )

    open_cases     = get_open_reports()
    resolved_cases = get_resolved_reports()
    total_cases    = len(open_cases) + len(resolved_cases)

    k1, k2, k3 = st.columns(3)
    k1.metric("🟠 Open Cases",  len(open_cases))
    k2.metric("✅ Resolved",     len(resolved_cases))
    rate = int(len(resolved_cases) / total_cases * 100) if total_cases > 0 else 0
    k3.metric("📈 Resolution Rate", f"{rate}%")

    st.divider()

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        sev_filter = st.selectbox(
            "Filter by severity:", ["All", "HIGH", "MEDIUM", "LOW"])
    with col_f2:
        sort_order = st.radio(
            "Sort by:", ["Severity (HIGH first)", "Date (newest first)"],
            horizontal=True,
        )

    filtered = (
        open_cases if sev_filter == "All"
        else [r for r in open_cases if r.get("severity") == sev_filter]
    )
    if sort_order == "Severity (HIGH first)":
        filtered = sorted(
            filtered,
            key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(
                x.get("severity"), 3),
        )
    else:
        filtered = sorted(
            filtered, key=lambda x: x.get("timestamp", ""), reverse=True)

    # ── Open Cases ────────────────────────────────────────────────────────────
    st.markdown(f"#### 🟠 Open Cases ({len(filtered)})")

    if not filtered:
        st.success("✅ No open cases for this filter.")
    else:
        for r in filtered:
            sev   = r.get("severity", "LOW")
            types = ", ".join(
                WASTE_LABELS.get(t, t) for t in r.get("waste_types", []))
            icon  = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "🟢")
            osm   = (f"https://www.openstreetmap.org/"
                     f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")

            with st.expander(
                f"{icon} Case #{r['id']} — {sev} — {types} — "
                f"{r.get('date','')} {r.get('time','')}",
                expanded=(sev == "HIGH"),
            ):
                col_info, col_action = st.columns([2, 1])
                with col_info:
                    st.write(f"**Waste Types:** {types}")
                    st.write(f"**Items Detected:** {r.get('item_count', 0)}")
                    st.write(f"**Severity:** {sev}")
                    st.write(f"**Reported:** {r.get('date','')} at {r.get('time','')}")
                    if r.get("description"):
                        st.write(f"**Location Note:** {r['description']}")
                with col_action:
                    st.write("**GPS Coordinates:**")
                    st.code(f"{r['latitude']:.5f}\n{r['longitude']:.5f}")
                    st.markdown(f"[📍 View on OpenStreetMap]({osm})")

                st.write("")
                note = st.text_input(
                    f"Resolution note for #{r['id']}:",
                    value="Area cleaned and waste collected.",
                    key=f"note_{r['id']}",
                )
                if st.button(
                    f"✅ Mark Case #{r['id']} as Resolved",
                    key=f"resolve_{r['id']}",
                    type="primary",
                ):
                    if resolve_report(r["id"], resolved_by="Operator", note=note):
                        st.success(f"✅ Case #{r['id']} resolved!")
                        st.rerun()

    # ── Resolved Cases ────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"#### ✅ Recently Resolved ({len(resolved_cases)})")

    if not resolved_cases:
        st.info("No resolved cases yet.")
    else:
        recent_resolved = sorted(
            resolved_cases,
            key=lambda x: x.get("resolved_at", ""),
            reverse=True,
        )[:10]

        for r in recent_resolved:
            types = ", ".join(
                WASTE_LABELS.get(t, t) for t in r.get("waste_types", []))
            resolved_date = (r.get("resolved_at") or "")[:10]
            with st.expander(
                f"✅ Case #{r['id']} — {types} — Resolved {resolved_date}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Resolved by:** {r.get('resolved_by', 'Operator')}")
                    st.write(f"**Note:** {r.get('resolution_note', '—')}")
                    st.write(f"**Originally reported:** "
                             f"{r.get('date','')} at {r.get('time','')}")
                with col2:
                    st.write(f"**GPS:** {r['latitude']:.5f}, {r['longitude']:.5f}")
                    st.write(f"**Severity was:** {r.get('severity', '—')}")
                    osm = (f"https://www.openstreetmap.org/"
                           f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")
                    st.markdown(f"[📍 View location]({osm})")

                if st.button(f"↩️ Reopen Case #{r['id']}",
                             key=f"reopen_{r['id']}"):
                    reopen_report(r["id"])
                    st.warning(f"Case #{r['id']} has been reopened.")
                    st.rerun()


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center;font-size:13px;color:#aaa;'>"
    "🌍 <b>EarthMender AI</b> · 3MTT NextGen Knowledge Showcase 2025 · "
    "Environment Pillar · Built with YOLOv8 + Streamlit + OpenStreetMap"
    "</p>",
    unsafe_allow_html=True,
)
