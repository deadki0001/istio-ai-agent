import os, requests, logging

log = logging.getLogger('notifier')
DISCORD_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
SLACK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
SEV_COLORS = {'critical':0xef4444,'high':0xf97316,'medium':0xeab308,'low':0x10b981}
SEV_EMOJI = {'critical':':red_circle:','high':':orange_circle:','medium':':yellow_circle:','low':':green_circle:'}

def _discord(diagnosis, metrics):
    if not DISCORD_URL:
        return
    sev = str(diagnosis.get('severity','unknown')).lower()
    lines = [f"`{s}` error={m.get('error_rate','N/A')} p99={m.get('p99_ms','N/A')}ms" for s,m in metrics.items()]
    payload = {
        'username': 'NEXUS',
        'embeds': [{
            'title': f"{SEV_EMOJI.get(sev,':white_circle:')} NEXUS ALERT - {sev.upper()}",
            'description': diagnosis.get('summary',''),
            'color': SEV_COLORS.get(sev,0x6b7280),
            'fields': [
                {'name':'Telemetry','value':'\n'.join(lines) or 'N/A'},
                {'name':'Root Cause','value':(diagnosis.get('root_cause') or 'N/A')[:900]},
                {'name':'Proposal (human approval required)','value':(diagnosis.get('proposal') or 'N/A')[:900]},
                {'name':'Cannot Do','value':(diagnosis.get('cannot_do') or 'N/A')[:400]},
                {'name':'Requires Approval From','value':diagnosis.get('requires_approval_from','N/A')},
            ],
            'footer': {'text': 'NEXUS - Intern Tier - Never auto-executed'}
        }]
    }
    try:
        r = requests.post(DISCORD_URL, json=payload, timeout=10)
        log.info(f"Discord: {r.status_code}")
    except Exception as e:
        log.error(f"Discord error: {e}")

def _slack(diagnosis, metrics):
    if not SLACK_URL:
        return
    sev = str(diagnosis.get('severity','unknown')).lower()
    lines = [f"`{s}` error={m.get('error_rate','N/A')} p99={m.get('p99_ms','N/A')}ms" for s,m in metrics.items()]
    payload = {
        'text': f"{SEV_EMOJI.get(sev,'')} *NEXUS ALERT - {sev.upper()}*\n{diagnosis.get('summary','')}",
        'blocks': [
            {'type':'header','text':{'type':'plain_text','text':f"NEXUS ALERT - {sev.upper()}"}},
            {'type':'section','text':{'type':'mrkdwn','text':f"*Summary*\n{diagnosis.get('summary','')}"}},
            {'type':'section','text':{'type':'mrkdwn','text':f"*Telemetry*\n"+'\n'.join(lines)}},
            {'type':'section','text':{'type':'mrkdwn','text':f"*Root Cause*\n{(diagnosis.get('root_cause') or '')[:600]}"}},
            {'type':'section','text':{'type':'mrkdwn','text':f"*Proposal*\n{(diagnosis.get('proposal') or '')[:600]}"}},
            {'type':'section','text':{'type':'mrkdwn','text':f"*Cannot Do*\n{diagnosis.get('cannot_do','N/A')}"}},
            {'type':'context','elements':[{'type':'mrkdwn','text':'NEXUS - Never auto-executed'}]}
        ]
    }
    try:
        r = requests.post(SLACK_URL, json=payload, timeout=10)
        log.info(f"Slack: {r.status_code}")
    except Exception as e:
        log.error(f"Slack error: {e}")

def notify(diagnosis, metrics):
    if not diagnosis.get('issue_detected'):
        return
    _discord(diagnosis, metrics)
    _slack(diagnosis, metrics)
    notify_grafana_irm(diagnosis, metrics)


def notify_escalation(diagnosis, metrics):
    """Fire escalation notification - human approved the proposal."""
    if not DISCORD_URL:
        return
    sev = str(diagnosis.get("severity","unknown")).lower()
    payload = {
        "username": "NEXUS",
        "embeds": [{
            "title": ":white_check_mark: ESCALATION APPROVED - Senior Agent Requested",
            "description": f"A human operator has approved escalation for the following issue:\n\n**{diagnosis.get('summary','')}**",
            "color": 0x10b981,
            "fields": [
                {"name": "Severity", "value": sev.upper()},
                {"name": "Approved Proposal", "value": (str(diagnosis.get("proposal","")) or "N/A")[:800]},
                {"name": "Authorized By", "value": diagnosis.get("requires_approval_from","N/A")},
                {"name": "Status", "value": "Senior Agent executing remediation..."},
            ],
            "footer": {"text": "NEXUS - Human-approved escalation - Intern tier -> Senior tier handoff"}
        }]
    }
    try:
        r = requests.post(DISCORD_URL, json=payload, timeout=10)
        log.info(f"Escalation Discord: {r.status_code}")
    except Exception as e:
        log.error(f"Escalation Discord error: {e}")


def notify_auto_remediate(diagnosis, metrics):
    """NEXUS Senior Agent auto-remediation notification."""
    if not DISCORD_URL:
        return
    payload = {
        "username": "NEXUS Senior Agent",
        "embeds": [{
            "title": ":robot: NEXUS AI AGENT - Auto-Remediation Executed",
            "description": f"Automated remediation executing for:\n\n**{diagnosis.get('summary','')}**",
            "color": 0x3b82f6,
            "fields": [
                {"name": "Severity", "value": str(diagnosis.get("severity","")).upper()},
                {"name": "Action", "value": "NEXUS AI deleted Chaos Mesh fault injection - service restoring to normal"},
                {"name": "Authorization", "value": "Operator-approved via NEXUS dashboard"},
                {"name": "Status", "value": ":white_check_mark: Chaos fault deleted - error rate should return to 0 within 60 seconds"},
            ],
            "footer": {"text": "NEXUS AI Agent - Auto-remediation - Chaos fault deleted - Intern tier autonomous action"}
        }]
    }
    try:
        r = requests.post(DISCORD_URL, json=payload, timeout=10)
        log.info(f"Auto-remediate Discord: {r.status_code}")
    except Exception as e:
        log.error(f"Auto-remediate Discord error: {e}")


GRAFANA_IRM_URL = os.environ.get("GRAFANA_IRM_WEBHOOK_URL", "")

def notify_grafana_irm(diagnosis: dict, metrics: dict):
    """Send alert to Grafana IRM - triggers on-call, SMS and phone call."""
    if not GRAFANA_IRM_URL:
        return
    sev = str(diagnosis.get("severity", "unknown")).lower()
    payload = {
        "title": f"NEXUS ALERT - {sev.upper()} - {diagnosis.get('summary','')[:100]}",
        "message": diagnosis.get("root_cause", "")[:500],
        "state": "alerting",
        "tags": {
            "severity": sev,
            "service": "lsd-backend",
            "agent": "nexus-intern-tier",
            "spiffe": "spiffe://cluster.local/ns/ai-agent/sa/ai-agent"
        }
    }
    try:
        r = requests.post(GRAFANA_IRM_URL, json=payload, timeout=10)
        log.info(f"Grafana IRM: {r.status_code}")
    except Exception as e:
        log.error(f"Grafana IRM error: {e}")


def notify_recovery(metrics: dict):
    """Fire recovery notification when all metrics return to normal."""
    if not DISCORD_URL:
        return
    lines = [f"`{s}` error={m.get('error_rate','N/A'):.4f} p99={m.get('p99_ms','N/A')}ms" for s,m in metrics.items() if m.get('error_rate') is not None]
    payload = {
        "username": "NEXUS",
        "embeds": [{
            "title": ":white_check_mark: NEXUS RECOVERED - All Services Healthy",
            "description": "All monitored services have returned to normal thresholds.",
            "color": 0x10b981,
            "fields": [{"name": "Telemetry", "value": "\n".join(lines) or "N/A"}],
            "footer": {"text": "NEXUS - Mesh Intelligence Hub - Istio Service Mesh"}
        }]
    }
    try:
        r = requests.post(DISCORD_URL, json=payload, timeout=10)
        log.info(f"Recovery Discord: {r.status_code}")
    except Exception as e:
        log.error(f"Recovery Discord error: {e}")
