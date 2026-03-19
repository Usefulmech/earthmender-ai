"""
EarthMender AI — Phase 3: Pollution Map Builder
=================================================
Builds interactive Folium maps with:
  - Colour-coded severity pins (green/orange/red)
  - Open vs Resolved status markers
  - Pollution heatmap overlay
  - Clickable popups with case details
  - OpenStreetMap link per report

Final 5-class system:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container

Install: pip install folium
Test:    python phase3_map/mapper.py
"""

import folium
from folium.plugins import HeatMap, MarkerCluster

DEFAULT_CENTER = [6.5244, 3.3792]   # Lagos Island
DEFAULT_ZOOM   = 12

SEVERITY_COLORS = {
    "HIGH":   "red",
    "MEDIUM": "orange",
    "LOW":    "green",
}

STATUS_ICONS = {
    "OPEN":     "exclamation-sign",
    "RESOLVED": "ok-sign",
}

WASTE_EMOJIS = {
    "plastic_bottle":  "🍶",
    "water_sachet":    "💧",
    "polythene_bag":   "🛍️",
    "disposable":      "🥤",
    "waste_container": "🛢️",
}


def build_map(reports: list, center=None, zoom=DEFAULT_ZOOM):
    """
    Build the full interactive pollution map.
    Returns a folium.Map object — render with st_folium() in Streamlit.
    """
    if not reports:
        center = center or DEFAULT_CENTER
        m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")
        folium.Marker(
            center,
            popup="No reports yet. Be the first to report!",
            icon=folium.Icon(color="gray", icon="info-sign")
        ).add_to(m)
        return m

    lats   = [r["latitude"]  for r in reports]
    lons   = [r["longitude"] for r in reports]
    center = center or [sum(lats) / len(lats), sum(lons) / len(lons)]

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    # ── HEATMAP — open cases only ─────────────────────────────────────────────
    open_reports = [r for r in reports if r.get("status") == "OPEN"]
    if open_reports:
        heat_data = []
        for r in open_reports:
            weight = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}.get(
                r.get("severity", "LOW"), 0.3)
            heat_data.append([r["latitude"], r["longitude"], weight])

        HeatMap(
            heat_data,
            radius=25, blur=18, max_zoom=13,
            name="🔥 Pollution Heatmap",
            gradient={"0.3": "blue", "0.6": "orange", "1.0": "red"},
        ).add_to(m)

    # ── MARKER CLUSTER ────────────────────────────────────────────────────────
    cluster = MarkerCluster(name="📍 Waste Reports").add_to(m)

    for r in reports:
        severity = r.get("severity", "LOW")
        status   = r.get("status",   "OPEN")
        color    = SEVERITY_COLORS[severity] if status == "OPEN" else "blue"
        icon     = STATUS_ICONS.get(status, "exclamation-sign")
        types    = r.get("waste_types", [])
        emojis   = " ".join(WASTE_EMOJIS.get(t, "🗑️") for t in types)
        count    = r.get("item_count", 0)
        osm_url  = (f"https://www.openstreetmap.org/"
                    f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")

        resolved_html = ""
        if status == "RESOLVED":
            resolved_html = (
                f"<br><span style='color:#1a7a4a;'>"
                f"✅ Resolved: {r.get('resolved_at','')[:10]}<br>"
                f"By: {r.get('resolved_by','Operator')}<br>"
                f"Note: {r.get('resolution_note','')}</span>"
            )

        popup_html = f"""
        <div style='font-family:Arial;min-width:200px;font-size:13px;'>
            <b style='color:#1a7a4a;'>♻️ EarthMender AI — Case #{r.get('id','')}</b>
            <hr style='margin:4px 0;'>
            <b>Status:</b>
            <span style='color:{"#e53935" if status=="OPEN" else "#1a7a4a"}'>
                {status}</span><br>
            <b>Waste:</b> {emojis}<br>
            <b>Items:</b> {count} | <b>Severity:</b> {severity}<br>
            <b>Date:</b> {r.get('date','')} {r.get('time','')}<br>
            <b>GPS:</b> {r['latitude']:.4f}, {r['longitude']:.4f}<br>
            {f"<b>Note:</b> {r.get('description','')}<br>" if r.get('description') else ""}
            {resolved_html}
            <br><a href='{osm_url}' target='_blank'>📍 Open in OpenStreetMap</a>
        </div>
        """

        folium.Marker(
            location=[r["latitude"], r["longitude"]],
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=(f"{'🟠 OPEN' if status=='OPEN' else '✅ RESOLVED'} | "
                     f"{severity} | {r.get('date','')}"),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(cluster)

    # ── LEGEND ────────────────────────────────────────────────────────────────
    legend_html = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:14px;border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,0.2);font-family:Arial;font-size:13px;'>
        <b style='color:#1a7a4a;'>🌍 EarthMender AI</b><br><br>
        <b>Severity (Open):</b><br>
        🔴 High &nbsp; 🟡 Medium &nbsp; 🟢 Low<br><br>
        <b>Status:</b><br>
        🔵 Resolved case
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(m)
    return m


def get_hotspots(reports: list, top_n: int = 5):
    """Top N active pollution hotspot zones — open reports only, ~1km grid."""
    if not reports:
        return []

    open_reports = [r for r in reports if r.get("status") == "OPEN"]
    grid = {}
    for r in open_reports:
        key = (round(r["latitude"], 2), round(r["longitude"], 2))
        if key not in grid:
            grid[key] = {"lat": key[0], "lon": key[1], "count": 0, "items": 0}
        grid[key]["count"] += 1
        grid[key]["items"] += r.get("item_count", 0)

    return sorted(grid.values(), key=lambda x: x["count"], reverse=True)[:top_n]


# ─── STANDALONE TEST ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    fake_reports = [
        {"id": "A1B2", "latitude": 6.5244, "longitude": 3.3792,
         "date": "2025-03-15", "time": "10:30",
         "waste_types": ["polythene_bag", "water_sachet"],
         "item_count": 5, "severity": "MEDIUM", "status": "OPEN",
         "description": "Near Ojota motor park",
         "resolved_at": None, "resolved_by": None, "resolution_note": None},

        {"id": "C3D4", "latitude": 6.5310, "longitude": 3.3850,
         "date": "2025-03-15", "time": "14:00",
         "waste_types": ["waste_container", "disposable"],
         "item_count": 2, "severity": "HIGH", "status": "OPEN",
         "description": "By Ketu bridge",
         "resolved_at": None, "resolved_by": None, "resolution_note": None},

        {"id": "E5F6", "latitude": 6.5190, "longitude": 3.3720,
         "date": "2025-03-14", "time": "09:15",
         "waste_types": ["plastic_bottle", "polythene_bag"],
         "item_count": 6, "severity": "HIGH", "status": "RESOLVED",
         "resolved_at": "2025-03-16T08:00:00",
         "resolved_by": "LAWMA Team A",
         "resolution_note": "Area swept and bagged."},
    ]
    m = build_map(fake_reports)
    m.save("test_map.html")
    print("✅ Map saved — open test_map.html in Chrome.")
    print("Hotspots:", get_hotspots(fake_reports))
