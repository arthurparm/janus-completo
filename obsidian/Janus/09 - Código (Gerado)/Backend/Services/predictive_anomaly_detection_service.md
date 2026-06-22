---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/predictive_anomaly_detection_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# predictive_anomaly_detection_service

## Arquivos-fonte
- `backend/app/services/predictive_anomaly_detection_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/observability_service.py`

## Símbolos
- class: `PredictiveAnomalyDetectionService`
- method: `PredictiveAnomalyDetectionService.analyze(self, *, events: list[dict[str, Any]], queue_snapshots: list[dict[str, Any]], start_ts: float, end_ts: float, bucket_minutes: int, min_events: int)` -> `dict[str, Any]`
- method: `PredictiveAnomalyDetectionService._normalize_events(self, *, events: list[dict[str, Any]], start_ts: float, end_ts: float)` -> `list[dict[str, Any]]`
- method: `PredictiveAnomalyDetectionService._build_buckets(self, *, events: list[dict[str, Any]], start_ts: float, end_ts: float, bucket_seconds: int)` -> `list[dict[str, Any]]`
- method: `PredictiveAnomalyDetectionService._extract_series(self, buckets: list[dict[str, Any]])` -> `dict[str, list[float]]`
- method: `PredictiveAnomalyDetectionService._detect_series_anomaly(self, *, metric_name: str, current: float, history: list[float], threshold: float, reason: str, recommendation: str)` -> `dict[str, Any] | None`
- method: `PredictiveAnomalyDetectionService._summarize_queues(self, queue_snapshots: list[dict[str, Any]])` -> `dict[str, Any]`
- method: `PredictiveAnomalyDetectionService._risk_from_signals(self, *, anomalies: list[dict[str, Any]], current_error_rate: float, queue_backlog_total: int)` -> `dict[str, Any]`
- method: `PredictiveAnomalyDetectionService._backlog_risk(self, total_backlog: int)` -> `int`
- method: `PredictiveAnomalyDetectionService._risk_level(self, score: int | float)` -> `str`
- method: `PredictiveAnomalyDetectionService._forecast_next(self, values: list[float], step_count: int)` -> `float | None`
- method: `PredictiveAnomalyDetectionService._forecast_backlog(self, backlog_total: int)` -> `int`
- method: `PredictiveAnomalyDetectionService._robust_zscore(self, *, current: float, values: list[float])` -> `float`
- method: `PredictiveAnomalyDetectionService._safe_median(values: list[float])` -> `float`
- method: `PredictiveAnomalyDetectionService._safe_float(value: Any, default: float = 0.0)` -> `float`
- method: `PredictiveAnomalyDetectionService._percentile(values: list[float], percentile: float)` -> `float`
- function: `get_predictive_anomaly_detection_service()` -> `PredictiveAnomalyDetectionService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
