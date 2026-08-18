import logging
import os
import time
import threading
from datetime import datetime, timezone
from telemetry import collect_telemetry
from claude_client import diagnose
import dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
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

def run():
    logger.info("AI Diagnostic Agent - Intern Tier - starting")
    logger.info(f"SPIFFE identity  : {SPIFFE_ID}")
    logger.info(f"Auth scope       : READ-ONLY - Prometheus, Jaeger, Kiali (istio-system)")
    logger.info(f"Denied           : Direct calls to lsd-payments (AuthorizationPolicy DENY)")
    logger.info(f"Poll interval    : {POLL_INTERVAL}s")
    logger.info(f"Dashboard        : http://0.0.0.0:5000")

    t = threading.Thread(target=dashboard.start, kwargs={"port": 5000}, daemon=True)
    t.start()

    while True:
        try:
            logger.info("Collecting telemetry snapshot...")
            telemetry = collect_telemetry()
            for svc, m in telemetry.get("services", {}).items():
                logger.info(f"[METRIC] {svc} | error_rate={m.get('error_rate', 'N/A')} | p99={m.get('p99_ms', 'N/A')}ms")
            dashboard.update_metrics(telemetry.get("services", {}))
            if check_thresholds(telemetry):
                logger.info("Thresholds exceeded - requesting Claude diagnosis...")
                d = diagnose(telemetry)
                dashboard.update_diagnosis(d, telemetry.get("services", {}))
                logger.info(f"[DIAGNOSIS] severity={d.get('severity','?').upper()} | {d.get('summary','')[:120]}")
                logger.info(f"[CANNOT DO] {d.get('cannot_do','')[:120]}")
                logger.info(f"[APPROVAL]  {d.get('requires_approval_from','')}")
                logger.info("Dashboard updated - open http://localhost:5000")
            else:
                logger.info("All metrics within thresholds")
                dashboard.clear_alert()
        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
