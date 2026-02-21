# Domain SLOs and Alerts (OQ-002)

Date: 2026-02-21  
Scope: `chat`, `rag`, `tools`, `workers`

## What was implemented

- Domain-level HTTP metrics in Prometheus:
  - `janus_domain_requests_total{domain,outcome}`
  - `janus_domain_request_latency_seconds{domain}`
- SLO evaluation endpoint:
  - `GET /api/v1/observability/slo/domains`
- Prometheus alert rules:
  - `janus/prometheus/alerts/janus-slo-rules.yml`
- Grafana dashboard:
  - `janus/grafana/dashboards/janus-slo-domains-overview.json`

## Default SLO thresholds

- `chat`: error rate <= 5%, p95 <= 3500ms
- `rag`: error rate <= 5%, p95 <= 4500ms
- `tools`: error rate <= 3%, p95 <= 2500ms
- `workers`: error rate <= 3%, p95 <= 4000ms

All thresholds are configurable in `janus/app/config.py` via `OQ_SLO_*`.

## API usage

```bash
curl "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20"
```

Response includes:
- overall status (`ok`, `degraded`, `insufficient_data`)
- per-domain SLI values
- per-domain breaches
- active alerts list

## Prometheus and Docker

Prometheus now loads alert rules from:
- `/etc/prometheus/alerts/*.yml`

In local Docker, this is mounted from:
- `./janus/prometheus/alerts:/etc/prometheus/alerts:ro`

## Grafana

Dashboard folder `Janus` includes:
- `Janus - Domain SLO Overview`

Panels:
- error rate by domain
- p95 latency by domain
- request throughput by domain
- active firing SLO alerts
