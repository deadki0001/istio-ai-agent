# Istio AI Diagnostic Agent

An AI agent operating as an identity-bound, authorization-scoped workload inside an Istio service mesh.
Demonstrates security-first AI/ML production engineering for Forward Deployed Engineer roles.

## Concept

Intern-tier agent per the Cloud Security Alliance AI Agent Maturity Framework. Observes only. Never acts.

- SPIFFE identity : spiffe://cluster.local/ns/ai-agent/sa/ai-agent
- Auth scope      : READ-ONLY - Prometheus, Jaeger, Kiali (istio-system)
- Denied          : Direct calls to lsd-payments (enforced by mesh, not code)

## Demo

1. Apply Chaos Mesh latency fault: kubectl apply -f k8s/chaos/latency-fault.yaml
2. Agent detects p99 > 500ms threshold
3. Agent calls Claude with full telemetry snapshot
4. Claude returns structured diagnosis with root cause and remediation proposal
5. Agent logs proposal - marked PROPOSAL ONLY
6. Agent is blocked if it tries to call lsd-payments directly (mesh-enforced DENY)

## Deploy

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/peer-auth.yaml
kubectl apply -f k8s/authz-policy.yaml
kubectl apply -f k8s/deployment.yaml

## Watch agent logs

kubectl logs -n ai-agent deployment/ai-agent -f
