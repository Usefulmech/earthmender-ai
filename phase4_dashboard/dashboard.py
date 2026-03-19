"""
EarthMender AI — Phase 4: Analytics Dashboard (Dark Final)
"""

import streamlit as st
from datetime import datetime
from collections import defaultdict
import json

LABEL_MAP = {
    "plastic_bottle":  "🍶 Plastic Bottle",
    "water_sachet":    "💧 Water Sachet",
    "polythene_bag":   "🛍️ Polythene Bag",
    "disposable":      "🥤 Disposable",
    "waste_container": "🛢️ Waste Container",
}

DASH_CSS = """
<style>
.dsh{background:#080f0a;padding:0 14px 20px}
.dsh-title{font-size:15px;font-weight:900;color:#eee;
  font-family:'Inter',sans-serif;letter-spacing:-0.2px}
.dsh-sub{font-size:11px;color:#444;margin-top:3px;font-family:'Inter',sans-serif}
.dsh-kgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-bottom:14px}
.dsh-k{background:#111c14;border-radius:12px;padding:13px;
  border:0.5px solid rgba(255,255,255,0.05);text-align:center}
.dsh-kv{font-size:22px;font-weight:900;color:#eee;font-family:'Inter',sans-serif}
.dsh-kl{font-size:9px;color:#444;margin-top:4px;text-transform:uppercase;
  letter-spacing:0.6px;font-family:'Inter',sans-serif}
.dsh-sh{font-size:13px;font-weight:800;color:#ddd;
  font-family:'Inter',sans-serif;margin:14px 0 10px;letter-spacing:-0.1px}
.dsh-bar-row{display:flex;align-items:center;gap:9px;margin-bottom:9px}
.dsh-bar-lbl{font-size:11px;color:#888;font-family:'Inter',sans-serif;
  min-width:130px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dsh-bar-tr{flex:1;background:rgba(255,255,255,0.06);border-radius:3px;height:5px}
.dsh-bar-fi{height:5px;border-radius:3px;background:#4caf50}
.dsh-bar-n{font-size:10px;color:#444;min-width:24px;text-align:right;
  font-family:'Inter',sans-serif}
.dsh-sg{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}
.dsh-sc{border-radius:11px;padding:13px 6px;text-align:center;border:0.5px solid}
.dsh-sv{font-size:22px;font-weight:900;font-family:'Inter',sans-serif}
.dsh-sl{font-size:9px;margin-top:3px;text-transform:uppercase;
  letter-spacing:0.5px;font-family:'Inter',sans-serif}
.dsh-pr{display:flex;align-items:center;gap:8px;margin:5px 0}
.dsh-pl{font-size:11px;color:#888;font-family:'Inter',sans-serif;min-width:90px}
.dsh-pt{flex:1;background:rgba(255,255,255,0.06);border-radius:3px;height:7px;overflow:hidden}
.dsh-pf{height:7px;border-radius:3px;transition:width 0.3s}
.dsh-rz{border-left:3px solid;padding:11px 13px;border-radius:10px;margin-bottom:9px}
.dsh-rzt{font-size:12px;font-weight:700;color:#eee;font-family:'Inter',sans-serif}
.dsh-rzm{font-size:10px;color:#777;margin-top:3px;font-family:'Inter',sans-serif}
.dsh-tr{background:#111c14;border-radius:11px;padding:13px 14px;
  margin-bottom:7px;display:flex;align-items:center;
  justify-content:space-between;border:0.5px solid rgba(255,255,255,0.04)}
.dsh-trl{font-size:12px;font-weight:700;color:#eee;font-family:'Inter',sans-serif}
.dsh-trs{font-size:10px;color:#444;margin-top:2px;font-family:'Inter',sans-serif}
</style>
"""


# ── LEVEL 1 ───────────────────────────────────────────────────────────────────

def render_stats_row(stats):
    total = stats.get("total", 0)
    res   = stats.get("resolved", 0)
    rate  = f"{int(res/total*100)}%" if total > 0 else "0%"
    st.markdown(DASH_CSS, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="dsh-kgrid">
      <div class="dsh-k">
        <div class="dsh-kv">{stats.get('total',0)}</div>
        <div class="dsh-kl">📋 Total</div>
      </div>
      <div class="dsh-k">
        <div class="dsh-kv" style="color:#ffb74d;">{stats.get('open',0)}</div>
        <div class="dsh-kl">🟠 Open</div>
      </div>
      <div class="dsh-k">
        <div class="dsh-kv" style="color:#81c784;">{stats.get('resolved',0)}</div>
        <div class="dsh-kl">✅ Resolved</div>
      </div>
      <div class="dsh-k">
        <div class="dsh-kv">{rate}</div>
        <div class="dsh-kl">📈 Rate</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_waste_breakdown(stats):
    types = stats.get("types", {})
    if not types:
        st.info("No detection data yet.")
        return
    st.markdown('<div class="dsh-sh">🛍️ Waste Breakdown</div>', unsafe_allow_html=True)
    total = sum(types.values()) or 1
    for wt, count in sorted(types.items(), key=lambda x: -x[1]):
        lbl = LABEL_MAP.get(wt, wt)
        pct = count / total * 100
        st.markdown(f"""
        <div class="dsh-bar-row">
          <div class="dsh-bar-lbl">{lbl}</div>
          <div class="dsh-bar-tr">
            <div class="dsh-bar-fi" style="width:{pct:.0f}%;"></div>
          </div>
          <div class="dsh-bar-n">{count}</div>
        </div>""", unsafe_allow_html=True)


def render_severity_chart(stats):
    severity = stats.get("severity", {})
    if not any(severity.values()):
        return
    st.markdown('<div class="dsh-sh">⚠️ Severity</div>', unsafe_allow_html=True)
    cfg = [("LOW","#4caf50","rgba(76,175,80,0.1)"),
           ("MEDIUM","#ff9800","rgba(255,152,0,0.1)"),
           ("HIGH","#f44336","rgba(244,67,54,0.1)")]
    cards = ""
    for lv, col, bg in cfg:
        cnt = severity.get(lv, 0)
        cards += (f'<div class="dsh-sc" '
                  f'style="background:{bg};border-color:{col}35;">'
                  f'<div class="dsh-sv" style="color:{col};">{cnt}</div>'
                  f'<div class="dsh-sl" style="color:{col}80;">{lv}</div>'
                  f'</div>')
    st.markdown(f'<div class="dsh-sg">{cards}</div>', unsafe_allow_html=True)


def render_open_vs_resolved(stats):
    total = stats.get("total", 0)
    if total == 0:
        return
    oc = stats.get("open", 0)
    rc = stats.get("resolved", 0)
    st.markdown('<div class="dsh-sh">📊 Open vs Resolved</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="dsh-pr">
      <div class="dsh-pl" style="color:#ffb74d;">Open {oc}</div>
      <div class="dsh-pt">
        <div class="dsh-pf" style="width:{oc/total*100:.0f}%;background:#ff9800;"></div>
      </div>
    </div>
    <div class="dsh-pr">
      <div class="dsh-pl" style="color:#81c784;">Resolved {rc}</div>
      <div class="dsh-pt">
        <div class="dsh-pf" style="width:{rc/total*100:.0f}%;background:#4caf50;"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def render_hotspot_table(hotspots):
    if not hotspots:
        st.info("No active hotspot data yet.")
        return
    st.markdown('<div class="dsh-sh">🔥 Top Hotspots</div>', unsafe_allow_html=True)
    rows = [{"Rank": f"#{i}", "Location": f"{h['lat']:.3f}, {h['lon']:.3f}",
             "Reports": h["count"], "Items": h["items"]}
            for i, h in enumerate(hotspots, 1)]
    st.table(rows)


def render_recent_reports(reports, n=5):
    if not reports:
        st.info("No reports yet.")
        return
    st.markdown('<div class="dsh-sh">🕐 Recent Reports</div>', unsafe_allow_html=True)
    recent = sorted(reports, key=lambda x: x.get("timestamp",""), reverse=True)[:n]
    for r in recent:
        sev  = r.get("severity","LOW")
        sta  = r.get("status","OPEN")
        si   = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(sev,"🟢")
        xi   = "🟠" if sta=="OPEN" else "✅"
        typs = ", ".join(LABEL_MAP.get(t,t) for t in r.get("waste_types",[]))
        with st.expander(f"{si} {xi} #{r.get('id','')} — {typs} — {r.get('date','')}"):
            c1,c2 = st.columns(2)
            with c1:
                st.write(f"**Waste:** {typs}")
                st.write(f"**Items:** {r.get('item_count',0)}")
            with c2:
                st.write(f"**GPS:** {r.get('latitude',0):.4f},{r.get('longitude',0):.4f}")
                st.write(f"**{r.get('date','')} {r.get('time','')}**")


# ── LEVEL 2 ───────────────────────────────────────────────────────────────────

def _monthly(reports):
    m = defaultdict(lambda: {"reported":0,"resolved":0})
    for r in reports:
        mo = r.get("date","")[:7]
        if mo:
            m[mo]["reported"] += 1
            if r.get("status") == "RESOLVED":
                m[mo]["resolved"] += 1
    return dict(sorted(m.items()))


def _recurrence(reports):
    g = defaultdict(list)
    for r in reports:
        g[(round(r["latitude"],2),round(r["longitude"],2))].append(r)
    out = []
    for (lat,lon),zr in g.items():
        rc = sum(1 for r in zr if r.get("status")=="RESOLVED")
        oc = sum(1 for r in zr if r.get("status")=="OPEN")
        t  = len(zr)
        if t >= 2:
            out.append({"lat":lat,"lon":lon,"total":t,
                        "resolved":rc,"open":oc,
                        "score":round(t/max(rc,1),1)})
    return sorted(out, key=lambda x:-x["score"])


def _trends(reports):
    tr = defaultdict(lambda: defaultdict(int))
    for r in reports:
        mo = r.get("date","")[:7]
        for wt in r.get("waste_types",[]):
            if mo: tr[wt][mo] += 1
    return {k:dict(v) for k,v in tr.items()}


def render_historical_trends(reports):
    if not reports:
        st.info("No historical data yet.")
        return
    st.markdown('<div class="dsh-sh">📅 Monthly Volume</div>', unsafe_allow_html=True)
    st.caption("All reports including resolved — data never disappears.")
    monthly = _monthly(reports)
    if not monthly:
        return
    mx = max((v["reported"] for v in monthly.values()), default=1) or 1
    for mo, d in monthly.items():
        rc = d["reported"]; vc = d["resolved"]
        rr = int(vc/rc*100) if rc > 0 else 0
        col= "#4caf50" if rr>=70 else "#ff9800" if rr>=40 else "#f44336"
        c1,c2,c3,c4 = st.columns([2,2,2,1])
        with c1: st.write(f"**{mo}**")
        with c2: st.progress(min(rc/mx,1.0), text=f"📋 {rc}")
        with c3: st.progress(min(vc/mx,1.0), text=f"✅ {vc}")
        with c4: st.markdown(f"<span style='color:{col};font-weight:800;'>"
                             f"{rr}%</span>", unsafe_allow_html=True)


def render_recurrence_analysis(reports):
    st.markdown('<div class="dsh-sh">🔁 Recurrence</div>', unsafe_allow_html=True)
    st.caption("Zones reported multiple times — high = systemic issue.")
    rec = _recurrence(reports)
    if not rec:
        st.info("Not enough data yet.")
        return
    for i, z in enumerate(rec[:5],1):
        sc  = z["score"]
        col = "#f44336" if sc>=3 else "#ff9800" if sc>=2 else "#4caf50"
        rsk = "🔴 High" if sc>=3 else "🟡 Medium" if sc>=2 else "🟢 Low"
        osm = f"https://www.openstreetmap.org/?mlat={z['lat']}&mlon={z['lon']}&zoom=16"
        st.markdown(f"""
        <div class="dsh-rz" style="border-color:{col};background:{col}0c;">
          <div class="dsh-rzt">Zone #{i} — {z['lat']:.3f},{z['lon']:.3f}
            &nbsp;<a href="{osm}" target="_blank"
            style="font-size:10px;color:#4caf50;">📍</a>
          </div>
          <div class="dsh-rzm">
            Reports: {z['total']} · Resolved: {z['resolved']} ·
            Open: {z['open']} ·
            <span style="color:{col};font-weight:800;">{rsk}</span>
          </div>
        </div>""", unsafe_allow_html=True)


def render_waste_type_trend(reports):
    st.markdown('<div class="dsh-sh">📈 Waste Trends</div>', unsafe_allow_html=True)
    st.caption("Rising types = where campaigns should focus.")
    tr = _trends(reports)
    if not tr:
        st.info("No trend data yet.")
        return
    for wt, mc in sorted(tr.items()):
        if not mc: continue
        lbl    = LABEL_MAP.get(wt, wt)
        months = sorted(mc.keys())
        counts = [mc[m] for m in months]
        latest = counts[-1] if counts else 0
        prev   = counts[-2] if len(counts)>=2 else counts[0]
        delta  = latest - prev
        arrow  = "⬆️" if delta>0 else "⬇️" if delta<0 else "➡️"
        dcol   = "#f44336" if delta>0 else "#4caf50" if delta<0 else "#666"
        st.markdown(f"""
        <div class="dsh-tr">
          <div>
            <div class="dsh-trl">{lbl}</div>
            <div class="dsh-trs">{sum(counts)} total · {months[-1]}</div>
          </div>
          <div style="text-align:center;">
            <div style="font-size:18px;">{arrow}</div>
            <div style="font-size:10px;color:{dcol};font-family:'Inter',sans-serif;
                 font-weight:800;">
              {'▲' if delta>0 else '▼' if delta<0 else '—'}{abs(delta)}
            </div>
          </div>
        </div>""", unsafe_allow_html=True)


# ── LEVEL 3 ───────────────────────────────────────────────────────────────────

def render_data_export(reports):
    st.markdown('<div class="dsh-sh">📤 Export Dataset</div>', unsafe_allow_html=True)
    st.caption("Anonymised log for NGO reports, research and data partnerships.")
    if not reports:
        st.info("No data to export yet.")
        return
    dates = [r.get("date","") for r in reports if r.get("date")]
    c1,c2,c3 = st.columns(3)
    c1.metric("Records",      len(reports))
    c2.metric("Unique Zones",
              len({(round(r["latitude"],2),round(r["longitude"],2)) for r in reports}))
    c3.metric("Range",
              f"{min(dates)[:7]}→{max(dates)[:7]}" if dates else "—")
    st.write("")
    lines = ["report_id,date,time,latitude,longitude,waste_types,"
             "item_count,severity,status,resolved_date,description"]
    for r in sorted(reports, key=lambda x: x.get("timestamp","")):
        lines.append(
            f"{r.get('id','')},{r.get('date','')},{r.get('time','')},"
            f"{r.get('latitude',0):.6f},{r.get('longitude',0):.6f},"
            f"{'|'.join(r.get('waste_types',[]))},"
            f"{r.get('item_count',0)},{r.get('severity','')},"
            f"{r.get('status','')},"
            f"{(r.get('resolved_at') or '')[:10]},"
            f"{r.get('description','').replace(',',';')}")
    st.download_button("⬇️ Download CSV",
        data="\n".join(lines),
        file_name=f"earthmender_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv", use_container_width=True)
    summary = {
        "exported_at": datetime.now().isoformat(),
        "total_reports": len(reports),
        "open_cases": sum(1 for r in reports if r.get("status")=="OPEN"),
        "resolved_cases": sum(1 for r in reports if r.get("status")=="RESOLVED"),
        "waste_type_totals": {},
        "date_range": {"from": min(dates,default=""), "to": max(dates,default="")},
    }
    for r in reports:
        for wt in r.get("waste_types",[]):
            summary["waste_type_totals"][wt] = summary["waste_type_totals"].get(wt,0)+1
    st.download_button("⬇️ Download JSON",
        data=json.dumps(summary,indent=2),
        file_name=f"earthmender_summary_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json", use_container_width=True)
    st.info("💡 For NGOs: includes all historical data — open and resolved.")


# ── MASTER ────────────────────────────────────────────────────────────────────

def render_full_dashboard(stats, hotspots, reports):
    st.markdown(DASH_CSS, unsafe_allow_html=True)
    st.markdown('<div class="dsh">', unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:14px 0 10px;">
      <div style="font-size:15px;font-weight:900;color:#eee;
           font-family:'Inter',sans-serif;letter-spacing:-0.2px;">
        📊 Analytics Dashboard
      </div>
      <div style="font-size:11px;color:#444;margin-top:3px;
           font-family:'Inter',sans-serif;">
        Operational · Trends · Export
      </div>
    </div>""", unsafe_allow_html=True)

    render_stats_row(stats)

    lvl1, lvl2, lvl3 = st.tabs(["⚡ Operational", "📅 Trends", "📤 Export"])

    with lvl1:
        st.write("")
        render_waste_breakdown(stats)
        render_severity_chart(stats)
        render_open_vs_resolved(stats)
        render_hotspot_table(hotspots)
        render_recent_reports(reports)

    with lvl2:
        st.write("")
        render_historical_trends(reports)
        render_recurrence_analysis(reports)
        render_waste_type_trend(reports)

    with lvl3:
        st.write("")
        render_data_export(reports)

    st.markdown("</div>", unsafe_allow_html=True)
