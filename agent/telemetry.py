import requests
import logging

logger = logging.getLogger(__name__)

PROMETHEUS_URL = "http://prometheus.istio-system:9090"
JAEGER_URL     = "http://tracing.istio-system:80"
KIALI_URL      = "http://kiali.istio-system:20001"

def get_error_rate(service: str, namespace: str = "lsd-payments") -> dict:
    query = f'rate(istio_requests_total{{destination_service_name="{service}",destination_service_namespace="{namespace}",response_code=~"5.."}}[5m])'
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", [])
        return {"error_rate": float(result[0]["value"][1]) if result else 0.0}
    except Exception as e:
        logger.error(f"Prometheus error rate query failed: {e}")
        return {"error_rate": None, "error": str(e)}

def get_p99_latency(service: str, namespace: str = "lsd-payments") -> dict:
    query = f'histogram_quantile(0.99, rate(istio_request_duration_milliseconds_bucket{{destination_service_name="{service}",destination_service_namespace="{namespace}"}}[5m]))'
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", [])
        return {"p99_ms": float(result[0]["value"][1]) if result else 0.0}
    except Exception as e:
        logger.error(f"Prometheus latency query failed: {e}")
        return {"p99_ms": None, "error": str(e)}

def get_recent_traces(service: str = "lsd-backend.lsd-payments", limit: int = 5) -> list:
    try:
        r = requests.get(
            f"{JAEGER_URL}/jaeger/api/traces",
            params={"service": service, "limit": limit, "lookback": "5m"},
            timeout=5
        )
        r.raise_for_status()
        return [
            {
                "traceID": t["traceID"],
                "spans": len(t.get("spans", [])),
                "duration_ms": t.get("spans", [{}])[0].get("duration", 0) / 1000
            }
            for t in r.json().get("data", [])
        ]
    except Exception as e:
        logger.error(f"Jaeger query failed: {e}")
        return []

def get_namespace_health() -> dict:
    try:
        r = requests.get(
            f"{KIALI_URL}/kiali/api/namespaces",
            timeout=5
        )
        r.raise_for_status()
        namespaces = r.json()
        lsd = next((n for n in namespaces if n["name"] == "lsd-payments"), {})
        return {"namespace": "lsd-payments", "found": bool(lsd), "labels": lsd.get("labels", {})}
    except Exception as e:
        logger.error(f"Kiali namespace query failed: {e}")
        return {"error": str(e)}

def collect_telemetry(services: list = None) -> dict:
    if services is None:
        services = ["lsd-backend", "lsd-frontend"]
    snapshot = {
        "services": {},
        "traces": get_recent_traces(),
        "namespace_health": get_namespace_health()
    }
    for svc in services:
        snapshot["services"][svc] = {
            "service": svc,
            **get_error_rate(svc),
            **get_p99_latency(svc)
        }
    return snapshot
