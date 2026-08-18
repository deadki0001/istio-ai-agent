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

def check_thresholds(telemetry: dict) -> bool:
    for svc, metrics in telemetry.get("services", {}).items():
        if (metrics.get("error_rate") or 0) > ERROR_THRESHOLD:
            logger.warning(f"[THRESHOLD BREACH] {svc} error_rate={metrics['error_rate']:.3f}")
            return True
        if (metrics.get("p99_ms") or 0) > LATENCY_THRESHOLD:
            logger.warning(f"[THRESHOLD BREACH] {svc} p99={metrics['p99_ms']:.1f}ms")
            return True
    return False

def run():
    logger.info("AI Diagnostic Agent - Intern Tier - starting")
    logger.info(f"SPIFFE identity  : {SPIFFE_ID}")
    logger.info(f"Auth scope       : READ-ONLY - Prometheus, Jaeger, Kiali (istio-system)")
    logger.info(f"Denied           : Direct calls to lsd-payments (AuthorizationPolicy DENY)")
    logger.info(f"Poll interval    : {POLL_INTERVAL}s")

    while True:
        try:
            logger.info("Collecting telemetry...")
            telemetry = collect_telemetry()

            for svc, m in telemetry.get("services", {}).items():
                logger.info(
                    f"[METRIC] {svc} | "
                    f"error_rate={m.get('error_rate', 'N/A')} | "
                    f"p99={m.get('p99_ms', 'N/A')}ms"
                )

            if check_thresholds(telemetry):
                logger.info("Requesting Claude diagnosis...")
                d = diagnose(telemetry)
                logger.info("=" * 60)
                logger.info("AGENT DIAGNOSIS REPORT")
                logger.info(f"Timestamp          : {datetime.now(timezone.utc).isoformat()}")
                logger.info(f"Agent identity     : {SPIFFE_ID}")
                logger.info(f"Issue detected     : {d.get('issue_detected')}")
                logger.info(f"Severity           : {str(d.get('severity','')).upper()}")
                logger.info(f"Summary            : {d.get('summary', 'N/A')}")
                logger.info(f"Root cause         : {d.get('root_cause', 'N/A')}")
                logger.info(f"PROPOSAL ONLY      : {d.get('proposal', 'N/A')}")
                logger.info(f"CANNOT DO          : {d.get('cannot_do', 'N/A')}")
                logger.info(f"Approve/execute    : {d.get('requires_approval_from', 'N/A')}")
                logger.info("=" * 60)
            else:
                logger.info("All metrics within thresholds")

        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
