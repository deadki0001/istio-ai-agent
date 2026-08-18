import logging
import os
import time
from datetime import datetime, timezone
from telemetry import collect_telemetry
from claude_client import diagnose

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("ai-agent")

POLL_INTERVAL     = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
ERROR_THRESHOLD   = float(os.environ.get("ERROR_RATE_THRESHOLD", "0.05"))
LATENCY_THRESHOLD = float(os.environ.get("LATENCY_THRESHOLD_MS", "500"))
SPIFFE_ID         = "spiffe://cluster.local/ns/ai-agent/sa/ai-agent"

def check_thresholds(telemetry):
    for svc, metrics in telemetry.get("services", {}).items():
        if (metrics.get("error_rate") or 0) > ERROR_THRESHOLD:
            logger.warning(f"[THRESHOLD BREACH] {svc} error_rate={metrics['error_rate']:.3f}")
            return True
        if (metrics.get("p99_ms") or 0) > LATENCY_THRESHOLD:
            logger.warning(f"[THRESHOLD BREACH] {svc} p99={metrics['p99_ms']:.1f}ms")
            return True
    return False

def print_report(d):
    sev = str(d.get("severity", "unknown")).upper()
    detected = "YES - ISSUE DETECTED" if d.get("issue_detected") else "NO ISSUE"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "",
        "=" * 70,
        "  AI DIAGNOSTIC AGENT - INTERN TIER REPORT",
        "=" * 70,
        f"  Timestamp : {ts}",
        f"  Identity  : {SPIFFE_ID}",
        "-" * 70,
        f"  STATUS    : {detected}",
        f"  SEVERITY  : {sev}",
        "-" * 70,
        "  SUMMARY",
        f"  {d.get('summary', 'N/A')}",
        "-" * 70,
        "  ROOT CAUSE",
    ]
    for line in (d.get("root_cause") or "N/A").split(". "):
        if line:
            lines.append(f"  {line.strip()}.")
    lines += [
        "-" * 70,
        "  PROPOSAL ONLY - requires human approval before execution",
    ]
    for line in (d.get("proposal") or "N/A").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines += [
        "-" * 70,
        "  CANNOT DO (authorization scope boundary)",
        f"  {d.get('cannot_do', 'N/A')}",
        "-" * 70,
        "  REQUIRES APPROVAL FROM",
        f"  {d.get('requires_approval_from', 'N/A')}",
        "=" * 70,
        "",
    ]
    for line in lines:
        logger.info(line)

def run():
    logger.info("AI Diagnostic Agent - Intern Tier - starting")
    logger.info(f"SPIFFE identity  : {SPIFFE_ID}")
    logger.info(f"Auth scope       : READ-ONLY - Prometheus, Jaeger, Kiali (istio-system)")
    logger.info(f"Denied           : Direct calls to lsd-payments (AuthorizationPolicy DENY)")
    logger.info(f"Poll interval    : {POLL_INTERVAL}s")

    while True:
        try:
            logger.info("Collecting telemetry snapshot...")
            telemetry = collect_telemetry()

            for svc, m in telemetry.get("services", {}).items():
                logger.info(
                    f"[METRIC] {svc} | "
                    f"error_rate={m.get('error_rate', 'N/A')} | "
                    f"p99={m.get('p99_ms', 'N/A')}ms"
                )

            if check_thresholds(telemetry):
                logger.info("Thresholds exceeded - requesting Claude diagnosis...")
                d = diagnose(telemetry)
                print_report(d)
            else:
                logger.info("All metrics within thresholds")

        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
