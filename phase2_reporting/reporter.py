"""
EarthMender AI — Phase 2: Waste Report Logger
===============================================
Handles GPS capture via browser and manages the
full report lifecycle: OPEN → RESOLVED.

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


# ─── GPS CAPTURE ──────────────────────────────────────────────────────────────
def render_gps_capture():
    """
    Injects JavaScript to read browser GPS coordinates.
    User copies the result into the lat/lon fields.
    Works on desktop and mobile browsers.
    """
    gps_js = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    var lat = pos.coords.latitude.toFixed(6);
                    var lon = pos.coords.longitude.toFixed(6);
                    var acc = pos.coords.accuracy.toFixed(0);
                    document.getElementById("gps-status").innerHTML =
                        "📍 <b>GPS captured!</b><br>" +
                        "Latitude: <b>" + lat + "</b><br>" +
                        "Longitude: <b>" + lon + "</b><br>" +
                        "Accuracy: ±" + acc + " metres<br>" +
                        "<small>Copy these values into the fields below.</small>";
                    document.getElementById("gps-status").style.background = "#e8f5e9";
                },
                function(err) {
                    document.getElementById("gps-status").innerHTML =
                        "⚠️ GPS error: " + err.message +
                        "<br><small>Switch to Manual Entry mode.</small>";
                    document.getElementById("gps-status").style.background = "#fff3e0";
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        } else {
            document.getElementById("gps-status").innerHTML =
                "❌ Geolocation not supported. Use Manual Entry.";
        }
    }
    getLocation();
    </script>
    <div id="gps-status" style="padding:12px; background:#e3f2fd;
         border-radius:8px; font-size:13px; color:#1a237e; line-height:1.8;">
        ⏳ Requesting GPS location from your device...
    </div>
    """
    components.html(gps_js, height=120)


def get_manual_location():
    """Fallback manual coordinate entry. Default = Lagos Island."""
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Latitude",  value=6.524400, format="%.6f",
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
                description: str = "", image_name: str = ""):
    """
    Create and persist a new OPEN waste report.
    Returns report dict, or None if no detections.
    """
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
    """Mark an open case as RESOLVED."""
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
    """Reopen a resolved case."""
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


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────
def _calculate_severity(detections: list):
    """
    Weighted severity scoring.
    LOW: ≤3 | MEDIUM: ≤7 | HIGH: >7
    disposable = weight 2, waste_container = weight 4
    """
    total_weight = sum(d.get("severity_weight", 1) for d in detections)
    if total_weight <= 3:   return "LOW"
    elif total_weight <= 7: return "MEDIUM"
    else:                   return "HIGH"


def _write(reports: list):
    with open(REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)


# ─── STANDALONE TEST ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    fake = [
        {"label": "plastic_bottle", "confidence": 0.91,
         "bbox": [10, 20, 100, 200], "severity_weight": 1},
        {"label": "polythene_bag",  "confidence": 0.87,
         "bbox": [110, 20, 200, 150], "severity_weight": 1},
        {"label": "disposable",     "confidence": 0.78,
         "bbox": [210, 30, 310, 160], "severity_weight": 2},
    ]
    r = save_report(fake, lat=6.5244, lon=3.3792,
                    description="Near Ojota bus stop")
    print(f"✅ Report saved: #{r['id']} | Severity: {r['severity']}")
    stats = get_report_stats(load_reports())
    print(f"📊 Stats: {stats}")
