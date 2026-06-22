---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/observability_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# observability_service

## Arquivos-fonte
- `backend/app/services/observability_service.py`

## Dependências de código
- Repositórios
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/auto_analysis.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/productivity.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/core/kernel.py`
- `backend/app/services/scheduler_service.py`
- `backend/app/services/trace_service.py`

## Símbolos
- function: `_get_or_create_counter(name: str, documentation: str, labelnames: list[str])` -> `PromCounter`
- function: `_get_or_create_histogram(name: str, documentation: str, labelnames: list[str], *, buckets: tuple[float, ...] | None = None)` -> `PromHistogram`
- class: `ObservabilityServiceError`
  - Base exception for observability service errors.
- class: `MessageNotFoundError`
  - Raised when a message is not found in quarantine.
- class: `ObservabilityService`
  - Camada de serviço para observabilidade, saúde do sistema e resiliência.
Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
- method: `ObservabilityService.__init__(self, repo: ObservabilityRepository)`
- method: `ObservabilityService._observe_operation_start(operation: str, **_attrs: Any)` -> `float`
- method: `ObservabilityService._observe_operation_success(operation: str, start_ts: float, **_attrs: Any)` -> `None`
- method: `ObservabilityService._observe_operation_failure(operation: str, start_ts: float, error: Exception, **_attrs: Any)` -> `None`
- method: `ObservabilityService._observe_result_size(operation: str, kind: str, size: int)` -> `None`
- method: `ObservabilityService._span_context(span_name: str)`
- method: `ObservabilityService._set_span_attrs(span: Any, **attrs: Any)` -> `None`
- method: `ObservabilityService.get_system_health(self)` -> `dict[str, Any]`
- method: `ObservabilityService.check_all_components(self)` -> `dict[str, dict[str, Any]]`
- method: `ObservabilityService.get_llm_router_health(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_multi_agent_system_health(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_poison_pill_handler_health(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_quarantined_messages(self, queue: str | None = None)` -> `list[QuarantinedMessage]`
- method: `ObservabilityService.release_from_quarantine(self, message_id: str, allow_retry: bool)` -> `QuarantinedMessage`
- method: `ObservabilityService.cleanup_expired_quarantine(self)` -> `dict[str, Any]`
- method: `ObservabilityService.purge_old_audit_events(self, retention_days: int)` -> `dict[str, Any]`
- method: `ObservabilityService.get_poison_pill_stats(self, queue: str | None = None)` -> `dict[str, Any]`
- method: `ObservabilityService.get_metrics_summary(self)` -> `dict[str, Any]`
- method: `ObservabilityService._safe_float(value: Any)` -> `float | None`
- method: `ObservabilityService._percentile(values: list[float], p: float)` -> `float`
- method: `ObservabilityService._status_is_error(status: Any)` -> `bool`
- method: `ObservabilityService._classify_event_domain(event: dict[str, Any])` -> `str`
- method: `ObservabilityService._get_domain_slo_thresholds()` -> `dict[str, dict[str, float]]`
- method: `ObservabilityService.get_domain_slo_report(self, *, window_minutes: int | None = None, min_events: int | None = None)` -> `dict[str, Any]`
- method: `ObservabilityService.get_predictive_anomaly_report(self, *, window_hours: int | None = None, bucket_minutes: int | None = None, min_events: int | None = None)` -> `dict[str, Any]`
- method: `ObservabilityService.get_user_metrics(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_user_activity(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_graph_audit_report(self)` -> `dict[str, Any]`
- method: `ObservabilityService.get_graph_quarantine_items(self, limit: int = 100)` -> `list[dict[str, Any]]`
- method: `ObservabilityService.promote_quarantine_item(self, node_id: int)` -> `dict[str, Any]`
- method: `ObservabilityService.record_audit_event(self, event: dict[str, Any])` -> `None`
- method: `ObservabilityService.get_audit_events(self, user_id: str | None, tool: str | None, status: str | None, start_ts: float | None, end_ts: float | None, endpoint: str | None = None, limit: int = 100, offset: int = 0)` -> `list[dict[str, Any]]`
- method: `ObservabilityService.get_audit_events_count(self, user_id: str | None, tool: str | None, status: str | None, start_ts: float | None, end_ts: float | None)` -> `int`
- method: `ObservabilityService.get_llm_usage_summary(self, start_ts: float | None, end_ts: float | None)` -> `dict[str, Any]`
- method: `ObservabilityService._normalize_counter_key(value: Any)` -> `str`
- method: `ObservabilityService._parse_details_payload(details_json: Any)` -> `dict[str, Any] | None`
- method: `ObservabilityService.get_request_pipeline_dashboard(self, request_id: str, limit: int = 2000, include_details: bool = False)` -> `dict[str, Any]`
- function: `observe_ux_metric_record(*, outcome: str, provider: str | None, ttft_ms: float | None, latency_ms: float | None)` -> `None`
- function: `get_observability_service(request: Request)` -> `ObservabilityService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
