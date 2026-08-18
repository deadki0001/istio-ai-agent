
"""Flask dashboard for the AI Diagnostic Agent."""
from flask import Flask
from datetime import datetime, timezone
import threading, logging

log = logging.getLogger("dashboard")
app = Flask(__name__)
state = {"last_updated": None, "status": "MONITORING", "metrics": {}, "diagnosis": None, "history": []}
_lock = threading.Lock()

def update_metrics(metrics):
    with _lock:
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        state["metrics"] = metrics

def update_diagnosis(diagnosis, metrics):
    with _lock:
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "diagnosis": diagnosis, "metrics": metrics}
        state["diagnosis"] = entry
        state["history"].insert(0, entry)
        state["history"] = state["history"][:10]
        state["status"] = "ALERT" if diagnosis.get("issue_detected") else "OK"
        state["last_updated"] = entry["timestamp"]

def clear_alert():
    with _lock:
        state["status"] = "MONITORING"

@app.route("/")
def index():
    with _lock:
        d = state.get("diagnosis")
        metrics = state.get("metrics", {})
        status = state.get("status", "MONITORING")
        last_updated = state.get("last_updated", "Never")

    sev = ""
    sev_color = "#4ade80"
    if d:
        sev = str(d["diagnosis"].get("severity", "")).upper()
        sev_color = {"CRITICAL":"#ef4444","HIGH":"#f97316","MEDIUM":"#eab308","LOW":"#4ade80"}.get(sev, "#6b7280")

    status_color = {"ALERT":"#ef4444","OK":"#4ade80","MONITORING":"#60a5fa"}.get(status, "#60a5fa")

    metric_rows = ""
    for svc, m in metrics.items():
        er = m.get("error_rate")
        p99 = m.get("p99_ms")
        er_str = f"{er:.4f}" if er is not None else "N/A"
        p99_str = f"{p99:.1f}ms" if p99 is not None and str(p99) != "nan" else "N/A"
        er_color = "#ef4444" if (er or 0) > 0.05 else "#4ade80"
        p99_color = "#ef4444" if (p99 or 0) > 500 else "#4ade80"
        metric_rows += f'''<tr><td class="svc">{svc}</td><td style="color:{er_color}">{er_str}</td><td style="color:{p99_color}">{p99_str}</td></tr>'''

    diag_section = ""
    if d:
        diag = d["diagnosis"]
        ts = d["timestamp"]
        proposal_items = "".join(f"<li>{l.strip()}</li>" for l in (diag.get("proposal") or "").split("\n") if l.strip())
        diag_section = f'''
        <section class="card alert-card" style="border-color:{sev_color}40">
            <div class="card-header">
                <span class="badge" style="background:{sev_color}">{sev}</span>
                <span class="ts">{ts}</span>
            </div>
            <h2>{diag.get("summary","")}</h2>
            <div class="section-label">ROOT CAUSE</div>
            <p class="body-text">{diag.get("root_cause","")}</p>
            <div class="section-label">PROPOSAL <span class="pill">HUMAN APPROVAL REQUIRED</span></div>
            <ol class="proposal-list">{proposal_items}</ol>
            <div class="scope-box">
                <div class="scope-label">CANNOT DO - Authorization Scope Boundary</div>
                <p>{diag.get("cannot_do","")}</p>
                <div class="scope-label" style="margin-top:12px">REQUIRES APPROVAL FROM</div>
                <p>{diag.get("requires_approval_from","")}</p>
            </div>
        </section>'''
    else:
        diag_section = '''<section class="card healthy-card"><div class="healthy-icon">✓</div><h2>All services healthy</h2><p>Agent is monitoring.</p></section>'''

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>AI Diagnostic Agent</title>
<style>
:root{{--bg:#0a0e1a;--surface:#111827;--border:#1f2937;--text:#f9fafb;--muted:#9ca3af;--accent:#6366f1;--mono:'Courier New',monospace}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;padding:24px}}
header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border)}}
.logo{{display:flex;align-items:center;gap:12px}}
.logo-icon{{width:40px;height:40px;background:var(--accent);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px}}
.logo-text h1{{font-size:18px;font-weight:700}}
.logo-text p{{font-size:12px;color:var(--muted);font-family:var(--mono)}}
.status-badge{{display:flex;align-items:center;gap:8px;padding:6px 16px;border-radius:20px;border:1px solid {status_color}40;background:{status_color}15}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:{status_color};animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
.status-text{{font-size:13px;font-weight:600;color:{status_color}}}
.identity-bar{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-bottom:20px;font-family:var(--mono);font-size:12px;color:var(--muted);display:flex;gap:24px;flex-wrap:wrap}}
.identity-bar span{{color:var(--accent)}}
.grid{{display:grid;grid-template-columns:300px 1fr;gap:20px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}}
.card-title{{font-size:11px;font-weight:600;letter-spacing:.08em;color:var(--muted);text-transform:uppercase;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:left;padding:6px 0;border-bottom:1px solid var(--border)}}
td{{padding:10px 0;font-family:var(--mono);font-size:13px}}
.svc{{color:var(--text);font-weight:500}}
.card-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}}
.badge{{font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;color:#000}}
.ts{{font-size:11px;color:var(--muted);font-family:var(--mono)}}
h2{{font-size:16px;font-weight:600;margin-bottom:16px;line-height:1.4}}
.section-label{{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;display:flex;align-items:center;gap:8px}}
.pill{{font-size:9px;background:#f97316;color:#000;padding:2px 6px;border-radius:3px;font-weight:700}}
.body-text{{font-size:13px;line-height:1.7;color:#d1d5db;margin-bottom:20px}}
.proposal-list{{font-size:13px;line-height:1.7;color:#d1d5db;margin-bottom:20px;padding-left:20px}}
.proposal-list li{{margin-bottom:8px}}
.scope-box{{background:#0f172a;border:1px solid #ef444440;border-radius:8px;padding:16px;font-size:12px;line-height:1.6;color:#fca5a5}}
.scope-label{{font-size:10px;font-weight:700;letter-spacing:.08em;color:#ef4444;margin-bottom:6px;text-transform:uppercase}}
.healthy-card{{text-align:center;padding:48px}}
.healthy-icon{{font-size:48px;color:#4ade80;margin-bottom:16px}}
.healthy-card h2{{color:#4ade80;margin-bottom:8px}}
.healthy-card p{{color:var(--muted)}}
.footer{{margin-top:20px;font-size:11px;color:var(--muted);font-family:var(--mono);text-align:right}}
</style></head><body>
<header>
  <div class="logo"><div class="logo-icon">⬡</div><div class="logo-text"><h1>AI Diagnostic Agent</h1><p>Intern Tier · Read-Only · Istio Service Mesh</p></div></div>
  <div class="status-badge"><div class="status-dot"></div><span class="status-text">{status}</span></div>
</header>
<div class="identity-bar">
  <div>SPIFFE: <span>spiffe://cluster.local/ns/ai-agent/sa/ai-agent</span></div>
  <div>SCOPE: <span>READ-ONLY → Prometheus · Jaeger · Kiali</span></div>
  <div>DENIED: <span>lsd-payments direct calls</span></div>
  <div>UPDATED: <span>{last_updated}</span></div>
</div>
<div class="grid">
  <div><div class="card"><div class="card-title">Live Telemetry</div>
    <table><thead><tr><th>Service</th><th>Error Rate</th><th>p99</th></tr></thead>
    <tbody>{metric_rows}</tbody></table></div></div>
  <div>{diag_section}</div>
</div>
<div class="footer">Claude API · claude-sonnet-4-6 · Proposals require human approval · Never auto-executed</div>
</body></html>"""

def start(port=5000):
    log.info(f"Dashboard on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
