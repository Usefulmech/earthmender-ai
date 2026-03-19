"""
EarthMender AI — Phase 4: Analytics Dashboard
===============================================
Three-level intelligence system:

  Level 1 — Operational        : Live KPIs, waste breakdown, hotspots
  Level 2 — Trends & Intel     : Monthly history, recurrence, type trends
  Level 3 — Data Export        : CSV + JSON for NGOs and data partners

Final 5-class system:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import streamlit as st
from datetime import datetime
from collections import defaultdict
import json

# Human-readable labels for all 5 classes
LABEL_MAP = {
    "plastic_bottle":  "🍶 Plastic Bottle",
    "water_sachet":    "💧 Water Sachet",
    "polythene_bag":   "🛍️ Polythene Bag",
    "disposable":      "🥤 Disposable",
    "waste_container": "🛢️ Waste Container",
}


# ─── LEVEL 1: OPERATIONAL ─────────────────────────────────────────────────────

def render_stats_row(stats: dict):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total Reports",  stats.get("total",    0))
    c2.metric("🟠 Open Cases",     stats.get("open",     0))
    c3.metric("✅ Resolved",        stats.get("resolved", 0))
    c4.metric("🗑️ Items Detected", stats.get("items",    0))
    total = stats.get("total", 0)
    res   = stats.get("resolved", 0)
    rate  = f"{int(res / total * 100)}%" if total > 0 else "0%"
    c5.metric("📈 Resolution Rate", rate)


def render_waste_breakdown(stats: dict):
    types = stats.get("types", {})
    if not types:
        st.info("No detection data yet.")
        return

    st.subheader("🛍️ Waste Type Breakdown")
    total = sum(types.values()) or 1
    for waste_type, count in sorted(types.items(), key=lambda x: -x[1]):
        label   = LABEL_MAP.get(waste_type, waste_type)
        percent = count / total
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(percent, text=label)
        with col2:
            st.write(f"**{count}** reports")


def render_severity_chart(stats: dict):
    severity = stats.get("severity", {})
    if not any(severity.values()):
        return

    st.subheader("⚠️ Severity Distribution")
    cols = st.columns(3)
    config = [
        ("LOW",    "🟢", "#4caf50"),
        ("MEDIUM", "🟡", "#ff9800"),
        ("HIGH",   "🔴", "#f44336"),
    ]
    for i, (level, icon, color) in enumerate(config):
        with cols[i]:
            count = severity.get(level, 0)
            st.markdown(
                f"<div style='text-align:center;padding:16px;"
                f"background:{color}22;border-radius:10px;"
                f"border:2px solid {color};'>"
                f"<div style='font-size:28px;'>{icon}</div>"
                f"<div style='font-size:24px;font-weight:bold;color:{color};'>{count}</div>"
                f"<div style='font-size:13px;color:#555;'>{level}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_open_vs_resolved(stats: dict):
    total    = stats.get("total", 0)
    open_c   = stats.get("open", 0)
    resolved = stats.get("resolved", 0)
    if total == 0:
        return

    st.subheader("📊 Open vs Resolved")
    col1, col2 = st.columns(2)
    with col1:
        st.progress(open_c / total,   text=f"🟠 Open: {open_c}")
    with col2:
        st.progress(resolved / total, text=f"✅ Resolved: {resolved}")


def render_hotspot_table(hotspots: list):
    if not hotspots:
        st.info("No active hotspot data yet.")
        return

    st.subheader("🔥 Top Active Hotspots")
    st.caption("Areas with highest density of open reports (~1km grid)")
    rows = []
    for i, h in enumerate(hotspots, 1):
        rows.append({
            "Rank":         f"#{i}",
            "Location":     f"{h['lat']:.3f}, {h['lon']:.3f}",
            "Open Reports":  h["count"],
            "Items Found":   h["items"],
        })
    st.table(rows)


def render_recent_reports(reports: list, n: int = 5):
    if not reports:
        st.info("No reports submitted yet.")
        return

    st.subheader("🕐 Recent Reports")
    recent = sorted(reports, key=lambda x: x.get("timestamp", ""), reverse=True)[:n]

    for r in recent:
        severity = r.get("severity", "LOW")
        status   = r.get("status",   "OPEN")
        sev_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "🟢")
        sta_icon = "🟠" if status == "OPEN" else "✅"
        types    = ", ".join(LABEL_MAP.get(t, t) for t in r.get("waste_types", []))

        with st.expander(
            f"{sev_icon} {sta_icon} Case #{r.get('id','')} — "
            f"{types} — {r.get('date','')} {r.get('time','')}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Waste:** {types}")
                st.write(f"**Items:** {r.get('item_count', 0)}")
                st.write(f"**Severity:** {severity}")
                st.write(f"**Status:** {status}")
            with col2:
                st.write(f"**GPS:** {r.get('latitude', 0):.4f}, "
                         f"{r.get('longitude', 0):.4f}")
                st.write(f"**Date:** {r.get('date','')} at {r.get('time','')}")
                if r.get("description"):
                    st.write(f"**Location:** {r['description']}")
                if status == "RESOLVED":
                    st.write(f"**Resolved by:** {r.get('resolved_by', '')}")


# ─── LEVEL 2: TREND INTELLIGENCE ──────────────────────────────────────────────

def _compute_monthly_trends(reports: list):
    """ALL reports by month — open + resolved. Data never disappears."""
    monthly = defaultdict(lambda: {"reported": 0, "resolved": 0})
    for r in reports:
        month = r.get("date", "")[:7]
        if month:
            monthly[month]["reported"] += 1
            if r.get("status") == "RESOLVED":
                monthly[month]["resolved"] += 1
    return dict(sorted(monthly.items()))


def _compute_recurrence(reports: list):
    """Zones reported multiple times — includes both open and resolved."""
    grid = defaultdict(list)
    for r in reports:
        key = (round(r["latitude"], 2), round(r["longitude"], 2))
        grid[key].append(r)

    recurrent = []
    for (lat, lon), zone_reports in grid.items():
        resolved_count = sum(1 for r in zone_reports if r.get("status") == "RESOLVED")
        open_count     = sum(1 for r in zone_reports if r.get("status") == "OPEN")
        total          = len(zone_reports)
        if total >= 2:
            recurrent.append({
                "lat":              lat,
                "lon":              lon,
                "total":            total,
                "resolved":         resolved_count,
                "open":             open_count,
                "recurrence_score": round(total / max(resolved_count, 1), 1),
            })
    return sorted(recurrent, key=lambda x: -x["recurrence_score"])


def _compute_waste_type_trends(reports: list):
    """Monthly count per waste type."""
    trends = defaultdict(lambda: defaultdict(int))
    for r in reports:
        month = r.get("date", "")[:7]
        for wtype in r.get("waste_types", []):
            if month:
                trends[wtype][month] += 1
    return {k: dict(v) for k, v in trends.items()}


def render_historical_trends(reports: list):
    if not reports:
        st.info("No historical data yet.")
        return

    st.subheader("📅 Monthly Report Volume")
    st.caption(
        "All reports — open AND resolved. Resolved cases still count here. "
        "This is your permanent environmental record."
    )

    monthly = _compute_monthly_trends(reports)
    if not monthly:
        return

    max_val = max((v["reported"] for v in monthly.values()), default=1) or 1

    for month, data in monthly.items():
        r_count  = data["reported"]
        v_count  = data["resolved"]
        res_rate = int(v_count / r_count * 100) if r_count > 0 else 0
        color    = "green" if res_rate >= 70 else "orange" if res_rate >= 40 else "red"

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            st.write(f"**{month}**")
        with col2:
            st.progress(min(r_count / max_val, 1.0), text=f"📋 {r_count} reported")
        with col3:
            st.progress(min(v_count / max_val, 1.0), text=f"✅ {v_count} resolved")
        with col4:
            st.markdown(
                f"<span style='color:{color};font-weight:bold;font-size:15px;'>"
                f"{res_rate}%</span>",
                unsafe_allow_html=True,
            )


def render_recurrence_analysis(reports: list):
    st.subheader("🔁 Recurrence Analysis")
    st.caption(
        "Locations reported multiple times — even after resolution. "
        "High recurrence = root cause not addressed. Key metric for NGOs."
    )

    recurrent = _compute_recurrence(reports)
    if not recurrent:
        st.info("Not enough data yet. Recurrence patterns appear as more reports come in.")
        return

    for i, zone in enumerate(recurrent[:6], 1):
        score = zone["recurrence_score"]
        color = "#f44336" if score >= 3 else "#ff9800" if score >= 2 else "#4caf50"
        label = "🔴 High Risk" if score >= 3 else "🟡 Medium Risk" if score >= 2 else "🟢 Low Risk"
        osm   = (f"https://www.openstreetmap.org/"
                 f"?mlat={zone['lat']}&mlon={zone['lon']}&zoom=16")

        st.markdown(
            f"<div style='border-left:4px solid {color};padding:12px 16px;"
            f"background:{color}11;border-radius:6px;margin-bottom:10px;'>"
            f"<b>Zone #{i}</b> — {zone['lat']:.3f}, {zone['lon']:.3f} &nbsp;"
            f"<a href='{osm}' target='_blank' style='font-size:12px;'>📍 Map</a><br>"
            f"Total: <b>{zone['total']}</b> &nbsp;|&nbsp; "
            f"Resolved: <b>{zone['resolved']}</b> &nbsp;|&nbsp; "
            f"Open: <b>{zone['open']}</b><br>"
            f"Recurrence risk: <b style='color:{color};'>{label}</b> (score: {score})"
            f"</div>",
            unsafe_allow_html=True,
        )


def render_waste_type_trend(reports: list):
    st.subheader("📈 Waste Type Trends")
    st.caption("Which waste types are rising? Use this to prioritise campaigns.")

    trends = _compute_waste_type_trends(reports)
    if not trends:
        st.info("No trend data yet.")
        return

    for wtype, monthly_counts in sorted(trends.items()):
        if not monthly_counts:
            continue
        label  = LABEL_MAP.get(wtype, wtype)
        months = sorted(monthly_counts.keys())
        counts = [monthly_counts[m] for m in months]
        latest = counts[-1] if counts else 0
        prev   = counts[-2] if len(counts) >= 2 else counts[0]
        delta  = latest - prev
        arrow  = "⬆️" if delta > 0 else "⬇️" if delta < 0 else "➡️"
        d_color= "red" if delta > 0 else "green" if delta < 0 else "gray"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{label}** — {sum(counts)} total")
            for m, c in zip(months, counts):
                st.caption(f"{m}: {c} report(s)")
        with col2:
            st.markdown(
                f"<div style='text-align:center;padding:12px;"
                f"border-radius:8px;background:#f9f9f9;'>"
                f"<div style='font-size:22px;'>{arrow}</div>"
                f"<div style='font-size:12px;color:{d_color};'>"
                f"{'▲' if delta > 0 else '▼' if delta < 0 else '—'}"
                f" {abs(delta)} vs prev month</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.write("")


# ─── LEVEL 3: DATA EXPORT ─────────────────────────────────────────────────────

def render_data_export(reports: list):
    st.subheader("📤 Export Environmental Dataset")
    st.caption(
        "Full anonymised waste report log — for NGO impact reports, "
        "academic research, and environmental data partnerships."
    )

    if not reports:
        st.info("No data to export yet.")
        return

    dates = [r.get("date", "") for r in reports if r.get("date")]
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Records", len(reports))
    col2.metric("📍 Unique Zones",
                len({(round(r["latitude"], 2), round(r["longitude"], 2))
                     for r in reports}))
    col3.metric("🗓️ Date Range",
                f"{min(dates)} → {max(dates)}" if dates else "—")

    st.write("")

    lines = [
        "report_id,date,time,latitude,longitude,waste_types,"
        "item_count,severity,status,resolved_date,description"
    ]
    for r in sorted(reports, key=lambda x: x.get("timestamp", "")):
        waste_types   = "|".join(r.get("waste_types", []))
        resolved_date = (r.get("resolved_at") or "")[:10]
        description   = r.get("description", "").replace(",", ";")
        lines.append(
            f"{r.get('id','')},{r.get('date','')},{r.get('time','')},"
            f"{r.get('latitude', 0):.6f},{r.get('longitude', 0):.6f},"
            f"{waste_types},{r.get('item_count', 0)},"
            f"{r.get('severity','')},"
            f"{r.get('status','')},"
            f"{resolved_date},"
            f"{description}"
        )

    st.download_button(
        label="⬇️ Download Full Dataset (CSV)",
        data="\n".join(lines),
        file_name=f"earthmender_waste_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    summary = {
        "exported_at":    datetime.now().isoformat(),
        "total_reports":  len(reports),
        "open_cases":     sum(1 for r in reports if r.get("status") == "OPEN"),
        "resolved_cases": sum(1 for r in reports if r.get("status") == "RESOLVED"),
        "waste_type_totals": {},
        "date_range": {
            "from": min(dates, default=""),
            "to":   max(dates, default=""),
        },
    }
    for r in reports:
        for wt in r.get("waste_types", []):
            summary["waste_type_totals"][wt] = \
                summary["waste_type_totals"].get(wt, 0) + 1

    st.download_button(
        label="⬇️ Download Summary Statistics (JSON)",
        data=json.dumps(summary, indent=2),
        file_name=f"earthmender_summary_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

    st.write("")
    st.info(
        "💡 **For NGOs & Partners:** Dataset includes all historical reports — "
        "open and resolved. Use for funding proposals, impact measurement, "
        "and identifying communities needing long-term intervention."
    )


# ─── MASTER RENDER ────────────────────────────────────────────────────────────

def render_full_dashboard(stats: dict, hotspots: list, reports: list):
    """Master render — called from Dashboard tab in app.py."""
    st.markdown("## 📊 Environmental Analytics Dashboard")
    st.caption("Three-level intelligence: Operational · Trends · Data Export")
    st.divider()

    render_stats_row(stats)
    st.divider()

    lvl1, lvl2, lvl3 = st.tabs([
        "⚡ Level 1 — Operational",
        "📅 Level 2 — Trends & Intelligence",
        "📤 Level 3 — Data Export",
    ])

    with lvl1:
        st.caption("Live snapshot for daily operator and community use.")
        st.write("")
        col1, col2 = st.columns(2)
        with col1:
            render_waste_breakdown(stats)
        with col2:
            render_severity_chart(stats)
        st.divider()
        render_open_vs_resolved(stats)
        st.divider()
        render_hotspot_table(hotspots)
        st.divider()
        render_recent_reports(reports)

    with lvl2:
        st.caption(
            "Historical patterns — resolved cases still count here. "
            "Data never disappears and grows in value over time."
        )
        st.write("")
        render_historical_trends(reports)
        st.divider()
        render_recurrence_analysis(reports)
        st.divider()
        render_waste_type_trend(reports)

    with lvl3:
        st.caption(
            "Export anonymised datasets for NGO reports, research, "
            "and environmental data products."
        )
        st.write("")
        render_data_export(reports)
