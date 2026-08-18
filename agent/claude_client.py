import anthropic
import json
import logging
import os

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are an AI diagnostic agent - Intern tier - operating inside an Istio service mesh.

Your SPIFFE identity: spiffe://cluster.local/ns/ai-agent/sa/ai-agent
Your authorization scope: READ-ONLY access to Prometheus, Jaeger, Kiali in istio-system.
You CANNOT call lsd-payments services directly. You CANNOT execute any commands. You CANNOT modify any resource.

Analyse the telemetry and respond ONLY with valid JSON using these keys:
- issue_detected: bool
- severity: "low" | "medium" | "high" | "critical"
- summary: one sentence describing the issue
- root_cause: detailed explanation based on the metrics
- proposal: specific remediation steps (marked as proposal only, not executed)
- cannot_do: what exceeds your authorization scope
- requires_approval_from: role that should approve and execute the fix
"""

def diagnose(telemetry: dict) -> dict:
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Analyse this telemetry and diagnose any issues:\n\n{json.dumps(telemetry, indent=2)}"
            }]
        )
        raw = message.content[0].text
        logger.info(f"Claude raw response: {raw[:500]}")
        # Strip markdown code blocks if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, raw: {raw[:200]}")
            return {"raw_response": raw, "parse_error": True}
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return {"error": str(e)}
