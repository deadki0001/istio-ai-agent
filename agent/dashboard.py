from flask import Flask, redirect
from datetime import datetime, timezone
import threading, logging, textwrap, re

log = logging.getLogger("nexus.dashboard")
app = Flask(__name__)
state = {"last_updated": None, "status": "MONITORING", "metrics": {}, "diagnosis": None}
_lock = threading.Lock()

def update_metrics(m):
    with _lock:
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        state["metrics"] = m

def update_diagnosis(diagnosis, metrics):
    with _lock:
        state["diagnosis"] = {"timestamp": datetime.now(timezone.utc).isoformat(), "diagnosis": diagnosis, "metrics": metrics}
        state["status"] = "ALERT" if diagnosis.get("issue_detected") else "OK"
        state["last_updated"] = state["diagnosis"]["timestamp"]

def clear_alert():
    with _lock:
        state["status"] = "MONITORING"

def w(text, width=88):
    if not text: return ""
    if isinstance(text, list): text = "\n".join(str(x) for x in text)
    return "\n".join(textwrap.fill(p, width) for p in text.split("\n") if p.strip())

CSS = """
:root{--bg:#080c14;--surface:#0d1320;--surface2:#111827;--border:#1e2d42;--border2:#253448;--text:#e2e8f0;--muted:#64748b;--accent:#3b82f6;--green:#10b981;--red:#ef4444;--orange:#f97316;--mono:'Courier New',monospace;--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;font-size:15px;line-height:1.6;font-weight:400}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:0 24px;height:58px;border-bottom:1px solid var(--border);background:var(--surface)}
.brand{display:flex;align-items:center;gap:12px}
.brand-ascii{font-family:var(--mono);font-size:11px;line-height:1.2;color:var(--accent);white-space:pre;letter-spacing:0;font-weight:600}
.brand-meta{border-left:1px solid var(--border2);padding-left:12px}
.brand-name{font-family:var(--mono);font-size:16px;font-weight:700;letter-spacing:0.14em;color:var(--text)}
.brand-sub{font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:0.06em;margin-top:2px}
.status-pill{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:0.08em;padding:5px 14px;border-radius:4px;border:1px solid}
.status-dot{width:7px;height:7px;border-radius:50%;animation:blink 1.5s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
.s-monitoring{color:#60a5fa;border-color:#1e3a5f;background:#0c1e35}
.s-monitoring .status-dot{background:#60a5fa}
.s-alert{color:var(--red);border-color:#7f1d1d;background:#1c0707}
.alert-banner{background:#7f1d1d;color:#fecaca;font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:0.1em;padding:8px 24px;text-align:center;animation:alertpulse 1s ease-in-out infinite;border-bottom:2px solid #ef4444}
@keyframes alertpulse{0%,100%{background:#7f1d1d;color:#fecaca}50%{background:#ef4444;color:#000}}
.s-alert .status-dot{background:var(--red)}
.s-ok{color:var(--green);border-color:#064e3b;background:#022c22}
.s-ok .status-dot{background:var(--green)}
.id-strip{display:flex;align-items:center;border-bottom:1px solid var(--border);background:var(--surface);overflow-x:auto}
.id-item{display:flex;align-items:center;gap:8px;padding:9px 20px;border-right:1px solid var(--border);white-space:nowrap}
.id-lbl{font-family:var(--mono);font-size:9px;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted)}
.id-val{font-family:var(--mono);font-size:12px;color:#60a5fa;font-weight:500}
.id-val.denied{color:#f87171}.id-val.scope{color:#34d399}
.main{display:grid;grid-template-columns:270px 1fr;min-height:calc(100vh - 110px)}
.sidebar{border-right:1px solid var(--border);background:var(--surface)}
.sb-sec{padding:14px 16px;border-bottom:1px solid var(--border)}
.sb-lbl{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px}
.sb-lbl::after{content:'';flex:1;height:1px;background:var(--border)}
.mrow{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--border)}
.mrow:last-child{border-bottom:none}
.msvc{font-family:var(--mono);font-size:13px;color:var(--text);font-weight:600}
.mvals{display:flex;flex-direction:column;align-items:flex-end;gap:2px}
.mval{font-family:var(--mono);font-size:12px;display:flex;align-items:center;gap:5px}
.mk{font-size:9px;color:var(--muted);letter-spacing:0.05em}
.ok{color:var(--green)}.warn{color:var(--red)}.na{color:var(--muted)}
.content{background:var(--bg);padding:24px}
.healthy{display:flex;flex-direction:column;align-items:center;justify-content:center;height:340px;gap:16px}
.h-ascii{font-family:var(--mono);font-size:11px;line-height:1.3;color:var(--green);white-space:pre;text-align:center}
.h-txt{font-size:13px;color:var(--muted)}
.acard{border:1px solid var(--border2);border-radius:6px;background:var(--surface);overflow:hidden}
.ahead{display:flex;align-items:center;justify-content:space-between;padding:11px 16px;border-bottom:1px solid var(--border);background:var(--surface2)}
.sbadge{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:0.12em;padding:3px 10px;border-radius:3px}
.sHIGH{background:#7c2d12;color:#fed7aa}.sCRITICAL{background:#7f1d1d;color:#fecaca}
.sMEDIUM{background:#78350f;color:#fde68a}.sLOW{background:#14532d;color:#bbf7d0}
.ats{font-family:var(--mono);font-size:10px;color:var(--muted)}
.abody{padding:20px}
.asum{font-size:15px;font-weight:500;line-height:1.6;color:var(--text);margin-bottom:20px;max-width:820px;white-space:pre-wrap;word-wrap:break-word}
.rsec{margin-bottom:20px}
.rlbl{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;display:flex;align-items:center;gap:8px}
.pill{font-size:8px;background:var(--orange);color:#000;padding:1px 6px;border-radius:2px;font-weight:700}
.rtxt{font-size:13px;line-height:1.8;color:#94a3b8;max-width:820px;white-space:pre-wrap;word-wrap:break-word}
.plist{list-style:none;display:flex;flex-direction:column;gap:8px}
.pitem{display:flex;gap:10px;font-size:13px;line-height:1.7;color:#94a3b8;max-width:820px}
.pnum{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--accent);background:#0c1e35;border:1px solid #1e3a5f;width:20px;height:20px;border-radius:3px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px}
.sbox{background:#120a0a;border:1px solid #3b0d0d;border-radius:4px;padding:14px 16px;max-width:820px}
.slbl{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#f87171;margin-bottom:6px}
.stxt{font-size:12px;line-height:1.7;color:#fca5a5;white-space:pre-wrap;word-wrap:break-word}
.albl{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#34d399;margin-top:12px;margin-bottom:6px}
.atxt{font-size:12px;color:#6ee7b7;white-space:pre-wrap;word-wrap:break-word}
.footer{padding:9px 24px;border-top:1px solid var(--border);background:var(--surface);display:flex;align-items:center;justify-content:space-between}
.fl{font-family:var(--mono);font-size:10px;color:var(--muted);display:flex;align-items:center;gap:16px}
.fr{font-family:var(--mono);font-size:10px;color:var(--muted)}
"""

@app.route("/")
def index():
    with _lock:
        d = state.get("diagnosis")
        metrics = state.get("metrics", {})
        status = state.get("status", "MONITORING")
        last_updated = state.get("last_updated", "Never")
    sev = ""
    sc = "sLOW"
    sev_border = "#1a3a1a"
    if d:
        sev = str(d["diagnosis"].get("severity","")).upper()
        sc = f"s{sev}"
        sev_border = {"CRITICAL":"#3b0d0d","HIGH":"#3b1a0d","MEDIUM":"#3b2e0d","LOW":"#0d3b1a"}.get(sev,"#1e2d42")
    scls = {"ALERT":"s-alert","OK":"s-ok","MONITORING":"s-monitoring"}.get(status,"s-monitoring")
    mrows = ""
    for svc, m in metrics.items():
        er = m.get("error_rate")
        p99 = m.get("p99_ms")
        ers = f"{er:.4f}" if er is not None else "N/A"
        p99s = f"{p99:.1f}ms" if p99 is not None and str(p99)!="nan" else "N/A"
        ec = "warn" if (er or 0)>0.05 else "ok"
        pc = "warn" if (p99 or 0)>500 else ("na" if p99s=="N/A" else "ok")
        mrows += f'''<div class="mrow"><span class="msvc">{svc}</span><div class="mvals"><span class="mval"><span class="mk">ERR</span><span class="{ec}">{ers}</span></span><span class="mval"><span class="mk">P99</span><span class="{pc}">{p99s}</span></span></div></div>'''
    if d:
        diag = d["diagnosis"]
        ts = d["timestamp"]
        pitems = ""
        num = 1
        prop = diag.get("proposal") or ""
        if isinstance(prop, list): prop = "\n".join(str(x) for x in prop)
        for line in prop.split("\n"):
            line = re.sub(r"^\d+\.\s*","",line.strip())
            if line:
                pitems += f'''<li class="pitem"><span class="pnum">{num}</span><span>{w(line,84)}</span></li>'''
                num += 1
        body = f'''<div class="acard" style="border-color:{sev_border}"><div class="ahead"><div style="display:flex;align-items:center;gap:10px"><span class="sbadge {sc}">{sev}</span><span style="font-family:var(--mono);font-size:11px;color:var(--muted)">ISSUE DETECTED</span></div><span class="ats">{ts}</span></div><div class="abody"><p class="asum">{w(diag.get("summary",""),88)}</p><div class="rsec"><div class="rlbl">Root Cause</div><p class="rtxt">{w(diag.get("root_cause",""),88)}</p></div><div class="rsec"><div class="rlbl">Proposal <span class="pill">Human approval required</span></div><ol class="plist">{pitems}</ol></div><div class="sbox"><div class="slbl">Cannot Do - Authorization Scope Boundary</div><p class="stxt">{w(diag.get("cannot_do",""),88)}</p><div class="albl">Requires Approval From</div><p class="atxt">{w(diag.get("requires_approval_from",""),88)}</p></div><div style="display:flex;gap:12px;margin-top:20px;padding-top:16px;border-top:1px solid #1e2d42"><form method="POST" action="/auto-remediate"><button type="submit" style="font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:0.08em;padding:10px 20px;border-radius:4px;border:none;background:#3b82f6;color:#fff;cursor:pointer;">NEXUS AI - Auto-Remediate</button></form><form method="POST" action="/approve"><button type="submit" style="font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:0.08em;padding:10px 20px;border-radius:4px;border:none;background:#10b981;color:#000;cursor:pointer;">Escalate to Senior Support Engineer</button></form><form method="POST" action="/dismiss"><button type="submit" style="font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:0.08em;padding:10px 20px;border-radius:4px;border:1px solid #1e2d42;background:transparent;color:#64748b;cursor:pointer;">Dismiss</button></form></div></div></div>'''
    else:
        body = '''<div class="healthy"><pre class="h-ascii"> _   _  ___ _  ___  _   _  ___\n| \ | || __|| |/ __|| | | |/ __|\n|  \| || _| | |\\__ \| |_| |\\__ \\\n|_|\\__||___||_||___/ \___/ |___/</pre><p class="h-txt">All services within thresholds - monitoring active</p></div>'''
    alert_banner = f'''<div class="alert-banner">NEXUS ALERT - {sev} - ISSUE DETECTED - {datetime.now(timezone.utc).strftime("%H:%M:%S UTC")}</div>''' if status == "ALERT" else ""

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta http-equiv="refresh" content="15"><title>NEXUS - Mesh Intelligence Hub</title><style>{CSS}</style></head><body><div class="topbar"><div class="brand"><pre class="brand-ascii"> _  _ _____  ___  _   _  ___\n| \\| || __\\ \\/ / || | | |/ __|\n| .` || _|  >  < | |_| |\\__ \\\n|_|\\_||___/_/\\_\\\\___/ _\\___|</pre><div class="brand-meta"><div class="brand-name">NEXUS</div><div class="brand-sub">Mesh Intelligence Hub - Istio Service Mesh - Intern Tier</div></div></div><div class="status-pill {scls}"><div class="status-dot"></div><span>{status}</span></div></div>{alert_banner}
<div class="id-strip"><div class="id-item"><span class="id-lbl">SPIFFE</span><span class="id-val">spiffe://cluster.local/ns/ai-agent/sa/ai-agent</span></div><div class="id-item"><span class="id-lbl">Scope</span><span class="id-val scope">READ-ONLY - Prometheus - Jaeger - Kiali</span></div><div class="id-item"><span class="id-lbl">Denied</span><span class="id-val denied">lsd-payments direct calls (AuthorizationPolicy)</span></div><div class="id-item"><span class="id-lbl">Updated</span><span class="id-val">{last_updated}</span></div></div><div class="main"><div class="sidebar"><div class="sb-sec"><div class="sb-lbl">Live Telemetry</div>{mrows}</div></div><div class="content">{body}</div></div><div class="footer"><div class="fl"><span>Claude API - claude-sonnet-4-6</span><span>Proposals require human approval</span><span>Never auto-executed</span></div><div class="fr">Auto-refresh 15s</div></div></body></html>"""


@app.route("/auto-remediate", methods=["POST"])
def auto_remediate():
    import notifier, subprocess
    with _lock:
        d = state.get("diagnosis")
    if d:
        notifier.notify_auto_remediate(d["diagnosis"], d["metrics"])
        with _lock:
            state["status"] = "REMEDIATING"
        try:
            subprocess.run([
                "kubectl", "delete", "networkchaos", "--all",
                "-n", "lsd-payments"
            ], timeout=30, capture_output=True)
            subprocess.run([
                "kubectl", "delete", "httpchaos", "--all",
                "-n", "lsd-payments"
            ], timeout=30, capture_output=True)
            log.info("Auto-remediation: chaos faults deleted")
        except Exception as e:
            log.error(f"Auto-remediation kubectl failed: {e}")
    return redirect("/")


@app.route("/approve", methods=["POST"])
def approve():
    import notifier
    with _lock:
        d = state.get("diagnosis")
    if d:
        notifier.notify_escalation(d["diagnosis"], d["metrics"])
        state["status"] = "ESCALATED"
    from flask import redirect
    return redirect("/")

@app.route("/dismiss", methods=["POST"])
def dismiss():
    clear_alert()
    from flask import redirect
    return redirect("/")

def start(port=5000):
    log.info(f"NEXUS dashboard on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
