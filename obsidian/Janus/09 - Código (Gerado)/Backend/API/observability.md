---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/observability.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# observability

## Arquivos-fonte
- `backend/app/api/v1/endpoints/observability.py`

## Rotas
- `GET /activity/user`
- `GET /anomalies/predictive`
- `GET /audit/events`
- `GET /audit/export`
- `GET /audit/ledger/integrity`
- `GET /errors/taxonomy`
- `GET /graph/audit`
- `GET /graph/quarantine`
- `GET /health/components/llm_router`
- `GET /health/components/multi_agent_system`
- `GET /health/components/poison_pill_handler`
- `GET /health/system`
- `GET /incidents`
- `GET /incidents/{incident_id}/events`
- `GET /llm/usage`
- `GET /metrics/summary`
- `GET /metrics/user`
- `GET /poison-pills/quarantined`
- `GET /poison-pills/stats`
- `GET /requests/{request_id}/dashboard`
- `GET /slo/domains`
- `GET /user_summary`
- `POST /graph/quarantine/promote`
- `POST /health/check-all`
- `POST /incidents/close`
- `POST /incidents/evidence`
- `POST /incidents/open`
- `POST /metrics/ux`
- `POST /poison-pills/cleanup`
- `POST /poison-pills/release`

## Dependências de código
- Serviços
  - `observability_service`
- Repositórios
  - `audit_ledger_repository`
  - `observability_repository`

## Símbolos
- class: `ReleaseQuarantineRequest`
- function: `get_system_health(service: ObservabilityService = Depends(get_observability_service))`
  - Delega a busca da saúde do sistema para o ObservabilityService.
- function: `check_all_components(service: ObservabilityService = Depends(get_observability_service))`
  - Delega a execução de todos os health checks para o ObservabilityService.
- function: `health_llm_router(service: ObservabilityService = Depends(get_observability_service))`
- function: `health_multi_agent(service: ObservabilityService = Depends(get_observability_service))`
- function: `health_poison_pill_handler(service: ObservabilityService = Depends(get_observability_service))`
- function: `get_quarantined_messages(service: ObservabilityService = Depends(get_observability_service), queue: str | None = None)`
  - Delega a busca de mensagens em quarentena para o ObservabilityService.
- function: `release_from_quarantine(request: ReleaseQuarantineRequest, service: ObservabilityService = Depends(get_observability_service))`
  - Delega a liberação de uma mensagem para o ObservabilityService.
- function: `cleanup_quarantine(service: ObservabilityService = Depends(get_observability_service))`
- function: `get_poison_pill_stats(service: ObservabilityService = Depends(get_observability_service), queue: str | None = None)`
  - Delega a busca de estatísticas de poison pills para o ObservabilityService.
- function: `get_metrics_summary(service: ObservabilityService = Depends(get_observability_service))`
  - Delega a geração do resumo de métricas para o ObservabilityService.
- function: `domain_slo_report(window_minutes: int | None = None, min_events: int | None = None, service: ObservabilityService = Depends(get_observability_service))`
- function: `predictive_anomalies(window_hours: int | None = None, bucket_minutes: int | None = None, min_events: int | None = None, service: ObservabilityService = Depends(get_observability_service))`
- function: `llm_usage(start_ts: float | None = None, end_ts: float | None = None, service: ObservabilityService = Depends(get_observability_service))`
- function: `graph_audit(service: ObservabilityService = Depends(get_observability_service))`
  - Executa consultas de auditoria no grafo e retorna um relatório resumido.
- function: `graph_quarantine_list(limit: int = 100, service: ObservabilityService = Depends(get_observability_service))`
- class: `PromoteQuarantineRequest`
- function: `graph_quarantine_promote(request: PromoteQuarantineRequest, service: ObservabilityService = Depends(get_observability_service))`
- class: `UserSummaryResponse`
- function: `user_summary(request: Request, user_id: str | None = None)`
- class: `UserMetricsResponse`
- function: `_normalize_export_value(value: object)` -> `str`
- function: `_filter_event_fields(event: dict[str, Any], fields: list[str] | None)` -> `dict[str, Any]`
- function: `audit_events(user_id: str | None = None, tool: str | None = None, status: str | None = None, start_ts: float | None = None, end_ts: float | None = None, limit: int = 100, offset: int = 0, service: ObservabilityService = Depends(get_observability_service))`
- function: `audit_ledger_integrity(request: Request, max_errors: int = 25)`
- class: `IncidentOpenRequest`
- class: `IncidentEvidenceRequest`
- class: `IncidentCloseRequest`
- function: `_sha256_hex(value: str)` -> `str`
- function: `_generate_incident_id()` -> `str`
- function: `incident_open(payload: IncidentOpenRequest, request: Request)`
- function: `incident_add_evidence(payload: IncidentEvidenceRequest, request: Request)`
- function: `incident_close(payload: IncidentCloseRequest, request: Request)`
- function: `list_incidents(request: Request, limit: int = 100, offset: int = 0)`
- function: `incident_events(incident_id: str, request: Request, limit: int = 2000, offset: int = 0)`
- function: `error_taxonomy()`
- function: `request_pipeline_dashboard(request_id: str, limit: int = 2000, include_details: bool = False, service: ObservabilityService = Depends(get_observability_service))`
- function: `export_audit_events(user_id: str | None = None, format: str = 'csv', fields: str | None = None, tool: str | None = None, status: str | None = None, start_ts: float | None = None, end_ts: float | None = None, limit: int = 1000, offset: int = 0, service: ObservabilityService = Depends(get_observability_service))`
- function: `user_metrics(user_id: str | None = None, service: ObservabilityService = Depends(get_observability_service))`
- class: `UserActivityResponse`
- function: `user_activity(user_id: str | None = None, service: ObservabilityService = Depends(get_observability_service))`
- class: `UxMetricItem`
- function: `record_ux_metric(item: UxMetricItem, service: ObservabilityService = Depends(get_observability_service))`
  - Registra uma métrica de UX para análise de desempenho do chat.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
