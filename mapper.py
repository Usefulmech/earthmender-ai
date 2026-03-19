"""
EarthMender AI — Phase 3: Pollution Map Builder
=================================================
Enhanced heatmap with:
  - Time decay: recent reports glow hotter than old ones
  - Recurrence multiplier: zones re-reported after cleanup glow brighter
  - Auto-center on densest active hotspot (not Lagos Island default)
  - Cluster bubble view toggle
  - Smoother gradient and better radius/blur settings

Final 5-class system:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime, timedelta
import math

DEFAULT_CENTER = [6.5244, 3.3792]
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


def _time_decay_weight(report: dict) -> float:
    """
    Reports from the last 7 days = full weight (1.0).
    Reports older than 30 days = minimum weight (0.2).
    Smooth exponential decay in between.
    """
    try:
        report_date = datetime.fromisoformat(report.get("timestamp", ""))
        days_old    = (datetime.now() - report_date).days
    except (ValueError, TypeError):
        days_old = 7   # fallback: treat as week-old

    # Exponential decay — halves every 14 days
    decay = math.exp(-0.05 * days_old)
    return max(0.2, min(1.0, decay))


def _recurrence_multiplier(lat: float, lon: float, all_reports: list) -> float:
    """
    Zones with multiple reports get a multiplier (max 2.0).
    This makes chronic hotspots glow visibly brighter.
    """
    key        = (round(lat, 2), round(lon, 2))
    zone_count = sum(
        1 for r in all_reports
        if (round(r["latitude"], 2), round(r["longitude"], 2)) == key
    )
    return min(2.0, 1.0 + (zone_count - 1) * 0.25)


def _auto_center(open_reports: list):
    """
    Auto-center on the densest active hotspot instead of
    defaulting to Lagos Island every time.
    """
    if not open_reports:
        return DEFAULT_CENTER, DEFAULT_ZOOM

    # Find grid cell with most open reports
    grid = {}
    for r in open_reports:
        key = (round(r["latitude"], 2), round(r["longitude"], 2))
        grid[key] = grid.get(key, 0) + 1

    if not grid:
        return DEFAULT_CENTER, DEFAULT_ZOOM

    best_key = max(grid, key=grid.get)
    zoom     = 14 if grid[best_key] >= 3 else 13
    return list(best_key), zoom


def build_map(reports: list, center=None, zoom=None, all_reports=None):
    """
    Build the full interactive pollution map.
    
    Args:
        reports:     reports to display (may be filtered)
        center:      override auto-center
        zoom:        override auto-zoom
        all_reports: full dataset for recurrence calculation
    """
    all_reports = all_reports or reports

    if not reports:
        c = center or DEFAULT_CENTER
        m = folium.Map(location=c, zoom_start=zoom or DEFAULT_ZOOM,
                       tiles="OpenStreetMap")
        folium.Marker(
            c,
            popup="No reports yet. Be the first to report!",
            icon=folium.Icon(color="gray", icon="info-sign")
        ).add_to(m)
        return m

    open_reports = [r for r in reports if r.get("status") == "OPEN"]

    # Auto-center on densest hotspot
    if center is None or zoom is None:
        auto_center, auto_zoom = _auto_center(open_reports)
        center = center or auto_center
        zoom   = zoom   or auto_zoom

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    # ── ENHANCED HEATMAP ──────────────────────────────────────────────────────
    if open_reports:
        heat_data = []
        sev_weights = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

        for r in open_reports:
            sev_w   = sev_weights.get(r.get("severity", "LOW"), 0.3)
            time_w  = _time_decay_weight(r)
            recur_w = _recurrence_multiplier(
                r["latitude"], r["longitude"], all_reports)
            weight  = min(1.0, sev_w * time_w * recur_w)
            heat_data.append([r["latitude"], r["longitude"], weight])

        HeatMap(
            heat_data,
            radius=30,
            blur=20,
            max_zoom=15,
            name="🔥 Pollution Heatmap",
            gradient={
                "0.0": "blue",
                "0.3": "cyan",
                "0.5": "lime",
                "0.7": "orange",
                "1.0": "red",
            },
            min_opacity=0.3,
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
        reporter = r.get("reporter", "Anonymous")
        osm_url  = (f"https://www.openstreetmap.org/"
                    f"?mlat={r['latitude']}&mlon={r['longitude']}&zoom=17")

        # Time decay display
        try:
            report_dt = datetime.fromisoformat(r.get("timestamp", ""))
            days_old  = (datetime.now() - report_dt).days
            age_str   = (
                "Today" if days_old == 0 else
                "Yesterday" if days_old == 1 else
                f"{days_old} days ago"
            )
        except (ValueError, TypeError):
            age_str = r.get("date", "")

        resolved_html = ""
        if status == "RESOLVED":
            resolved_html = (
                f"<br><span style='color:#1a7a4a;'>"
                f"✅ Resolved: {(r.get('resolved_at') or '')[:10]}<br>"
                f"By: {r.get('resolved_by','Operator')}<br>"
                f"Note: {r.get('resolution_note','')}</span>"
            )

        popup_html = f"""
        <div style='font-family:Arial;min-width:210px;font-size:13px;'>
          <b style='color:#1a7a4a;'>♻️ EarthMender AI — #{r.get('id','')}</b>
          <hr style='margin:4px 0;'>
          <b>Status:</b>
          <span style='color:{"#e53935" if status=="OPEN" else "#1a7a4a"}'>{status}</span><br>
          <b>Waste:</b> {emojis}<br>
          <b>Items:</b> {count} | <b>Severity:</b> {severity}<br>
          <b>Reported:</b> {age_str} by {reporter}<br>
          <b>GPS:</b> {r['latitude']:.4f}, {r['longitude']:.4f}<br>
          {f"<b>Location:</b> {r.get('description','')}<br>" if r.get('description') else ""}
          {resolved_html}
          <br><a href='{osm_url}' target='_blank'>📍 Open in OpenStreetMap</a>
        </div>
        """

        folium.Marker(
            location=[r["latitude"], r["longitude"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=(
                f"{'🟠' if status=='OPEN' else '✅'} "
                f"{severity} | {emojis} | {age_str}"
            ),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(cluster)

    # ── LEGEND ────────────────────────────────────────────────────────────────
    legend_html = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:14px;border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,0.2);font-family:Arial;font-size:12px;'>
      <b style='color:#1a7a4a;'>🌍 EarthMender AI</b><br><br>
      <b>Severity (Open):</b><br>
      🔴 High &nbsp; 🟡 Medium &nbsp; 🟢 Low<br><br>
      <b>Heatmap:</b><br>
      Red = recent + recurring<br>
      Blue = older / single report<br><br>
      <b>Status:</b><br>
      🔵 Resolved case
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(m)
    return m


def get_hotspots(reports: list, top_n: int = 5):
    """Top N active hotspot zones with recurrence count."""
    if not reports:
        return []

    open_reports = [r for r in reports if r.get("status") == "OPEN"]
    grid = {}
    for r in open_reports:
        key = (round(r["latitude"], 2), round(r["longitude"], 2))
        if key not in grid:
            grid[key] = {"lat": key[0], "lon": key[1],
                         "count": 0, "items": 0}
        grid[key]["count"] += 1
        grid[key]["items"] += r.get("item_count", 0)

    return sorted(grid.values(), key=lambda x: x["count"], reverse=True)[:top_n]
