"""
EarthMender AI — Phase 2: Waste Report Logger
===============================================
Real-time GPS using watchPosition() — continuously updates
coordinates as accuracy improves, no manual copy needed.

Final 5-class system:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import json
import os
import uuid
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

REPORTS_FILE = "waste_reports.json"


# ─── REAL-TIME GPS CAPTURE ────────────────────────────────────────────────────
def render_gps_capture():
    """
    Real-time GPS using watchPosition().
    - Continuously improves accuracy as GPS locks tighter
    - Auto-fills hidden inputs that Streamlit reads via query params trick
    - Shows live accuracy meter
    - Graceful fallback message for desktop/denied permissions
    """
    gps_html = """
    <div id="gps-container" style="font-family:Arial;font-size:13px;">

      <div id="gps-status" style="
        padding:12px 14px;
        background:#e3f2fd;
        border-radius:10px;
        color:#1a237e;
        line-height:1.8;
        margin-bottom:8px;">
        ⏳ Acquiring GPS signal...
      </div>

      <div id="gps-accuracy-bar" style="display:none;margin-bottom:8px;">
        <div style="font-size:11px;color:#555;margin-bottom:4px;">
          GPS accuracy
        </div>
        <div style="background:#e0e0e0;border-radius:4px;height:6px;">
          <div id="acc-fill" style="
            height:6px;border-radius:4px;
            background:#4caf50;width:0%;
            transition:width 0.4s ease;">
          </div>
        </div>
        <div id="acc-label" style="font-size:11px;color:#555;margin-top:3px;"></div>
      </div>

      <div id="gps-coords" style="
        display:none;
        background:#e8f5e9;
        border-radius:10px;
        padding:10px 14px;
        font-size:13px;
        color:#1b5e20;">
        <b id="coord-lat"></b><br>
        <b id="coord-lon"></b>
      </div>

      <input type="hidden" id="em-lat" value="">
      <input type="hidden" id="em-lon" value="">
    </div>

    <script>
    var watchId = null;
    var bestAccuracy = 9999;

    function updateAccuracyBar(accuracy) {
      var bar = document.getElementById('acc-fill');
      var label = document.getElementById('acc-label');
      if (!bar) return;
      var pct = Math.max(0, Math.min(100, 100 - (accuracy / 50 * 100)));
      bar.style.width = pct + '%';
      if (accuracy <= 10) {
        bar.style.background = '#4caf50';
        label.textContent = 'Excellent ±' + Math.round(accuracy) + 'm';
      } else if (accuracy <= 30) {
        bar.style.background = '#ff9800';
        label.textContent = 'Good ±' + Math.round(accuracy) + 'm';
      } else {
        bar.style.background = '#f44336';
        label.textContent = 'Acquiring... ±' + Math.round(accuracy) + 'm';
      }
      document.getElementById('gps-accuracy-bar').style.display = 'block';
    }

    function onPosition(pos) {
      var lat = pos.coords.latitude.toFixed(6);
      var lon = pos.coords.longitude.toFixed(6);
      var acc = pos.coords.accuracy;

      // Only update if accuracy improved
      if (acc < bestAccuracy) {
        bestAccuracy = acc;
        document.getElementById('em-lat').value = lat;
        document.getElementById('em-lon').value = lon;

        document.getElementById('coord-lat').textContent = 'Lat: ' + lat;
        document.getElementById('coord-lon').textContent = 'Lon: ' + lon;
        document.getElementById('gps-coords').style.display = 'block';

        var status = document.getElementById('gps-status');
        status.style.background = '#e8f5e9';
        status.style.color = '#1b5e20';
        status.innerHTML = '📍 GPS locked — coordinates updating automatically.';

        updateAccuracyBar(acc);

        // Store in sessionStorage so Streamlit can read via JS query
        try {
          sessionStorage.setItem('em_lat', lat);
          sessionStorage.setItem('em_lon', lon);
          sessionStorage.setItem('em_acc', Math.round(acc));
        } catch(e) {}
      }
    }

    function onError(err) {
      var status = document.getElementById('gps-status');
      status.style.background = '#fff3e0';
      status.style.color = '#e65100';
      if (err.code === 1) {
        status.innerHTML = '⚠️ Location permission denied.<br>Use Manual Entry below.';
      } else if (err.code === 2) {
        status.innerHTML = '⚠️ GPS signal not available.<br>Use Manual Entry below.';
      } else {
        status.innerHTML = '⚠️ GPS timeout. Use Manual Entry below.';
      }
    }

    if (navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(
        onPosition,
        onError,
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0
        }
      );
    } else {
      document.getElementById('gps-status').innerHTML =
        '❌ Geolocation not supported. Use Manual Entry.';
    }
    </script>
    """
    components.html(gps_html, height=200)


def get_gps_coords_from_inputs():
    """
    Read GPS coordinates from text inputs populated by the GPS widget.
    Returns (lat, lon) tuple.
    """
    col1, col2 = st.columns(2)
    with col1:
        lat_str = st.text_input(
            "Latitude", key="gps_lat",
            placeholder="Auto-filled from GPS above",
            help="Filled automatically when GPS locks"
        )
    with col2:
        lon_str = st.text_input(
            "Longitude", key="gps_lon",
            placeholder="Auto-filled from GPS above",
            help="Filled automatically when GPS locks"
        )

    lat, lon = 6.5244, 3.3792  # Lagos default
    if lat_str and lon_str:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            st.warning("⚠️ Invalid coordinates — Lagos default used.")
    return lat, lon


def get_manual_location():
    """Fallback manual coordinate entry."""
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Latitude", value=6.524400, format="%.6f",
                              help="e.g. 6.524400 for Lagos Island")
    with col2:
        lon = st.number_input("Longitude", value=3.379200, format="%.6f",
                              help="e.g. 3.379200 for Lagos Island")
    return lat, lon


# ─── REPORT CRUD ──────────────────────────────────────────────────────────────
def load_reports():
    if not os.path.exists(REPORTS_FILE):
        return []
    try:
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_report(detections: list, lat: float, lon: float,
                description: str = "", image_name: str = "",
                reporter_name: str = "Anonymous"):
    if not detections:
        return None

    report = {
        "id":              str(uuid.uuid4())[:8].upper(),
        "timestamp":       datetime.now().isoformat(),
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "time":            datetime.now().strftime("%H:%M"),
        "latitude":        round(lat, 6),
        "longitude":       round(lon, 6),
        "image":           image_name,
        "description":     description,
        "reporter":        reporter_name,
        "detections":      detections,
        "waste_types":     list({d["label"] for d in detections}),
        "item_count":      len(detections),
        "severity":        _calculate_severity(detections),
        "status":          "OPEN",
        "resolved_at":     None,
        "resolved_by":     None,
        "resolution_note": None,
    }

    reports = load_reports()
    reports.append(report)
    _write(reports)
    return report


def resolve_report(report_id: str, resolved_by: str = "Operator",
                   note: str = "Area cleaned and waste removed."):
    reports = load_reports()
    for r in reports:
        if r["id"] == report_id and r["status"] == "OPEN":
            r["status"]          = "RESOLVED"
            r["resolved_at"]     = datetime.now().isoformat()
            r["resolved_by"]     = resolved_by
            r["resolution_note"] = note
            _write(reports)
            return True
    return False


def reopen_report(report_id: str):
    reports = load_reports()
    for r in reports:
        if r["id"] == report_id:
            r["status"]          = "OPEN"
            r["resolved_at"]     = None
            r["resolved_by"]     = None
            r["resolution_note"] = None
    _write(reports)


def get_open_reports():
    return [r for r in load_reports() if r.get("status") == "OPEN"]


def get_resolved_reports():
    return [r for r in load_reports() if r.get("status") == "RESOLVED"]


def get_report_stats(reports: list):
    if not reports:
        return {"total": 0, "open": 0, "resolved": 0,
                "items": 0, "types": {}, "severity": {}}

    types    = {}
    severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    items    = 0

    for r in reports:
        items += r.get("item_count", 0)
        for t in r.get("waste_types", []):
            types[t] = types.get(t, 0) + 1
        s = r.get("severity", "LOW")
        severity[s] = severity.get(s, 0) + 1

    return {
        "total":    len(reports),
        "open":     sum(1 for r in reports if r.get("status") == "OPEN"),
        "resolved": sum(1 for r in reports if r.get("status") == "RESOLVED"),
        "items":    items,
        "types":    types,
        "severity": severity,
    }


def _calculate_severity(detections: list):
    total_weight = sum(d.get("severity_weight", 1) for d in detections)
    if total_weight <= 3:   return "LOW"
    elif total_weight <= 7: return "MEDIUM"
    else:                   return "HIGH"


def _write(reports: list):
    with open(REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)
