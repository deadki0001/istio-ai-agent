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
