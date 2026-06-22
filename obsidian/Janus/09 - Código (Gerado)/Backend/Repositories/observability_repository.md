---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/observability_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# observability_repository

## Arquivos-fonte
- `backend/app/repositories/observability_repository.py`

## Dependências de código
- Repositórios
  - `audit_ledger_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/core/kernel.py`
- `backend/app/core/memory/rag_telemetry.py`
- `backend/app/core/security/egress_policy.py`
- `backend/app/core/tools/action_module.py`
- `backend/app/core/workers/google_productivity_worker.py`
- `backend/app/repositories/knowledge_repository.py`
- `backend/app/repositories/llm_repository.py`
- `backend/app/services/chat_event_logger.py`
- `backend/app/services/data_purge_service.py`
- `backend/app/services/document_service.py`
- `backend/app/services/observability_service.py`
- `backend/app/services/scheduler_service.py`
- `backend/app/services/secret_key_rotation_service.py`
- `backend/app/services/secret_memory_service.py`
- `backend/app/services/secret_retention_service.py`
- `backend/app/services/tool_executor_service.py`
- `backend/app/services/vault_transit_rotation_service.py`

## Símbolos
- function: `_coerce_user_id(raw_user_id: Any)` -> `int | None`
- function: `_normalize_ledger_payload(event: dict[str, Any])` -> `dict[str, Any] | None`
- class: `ObservabilityRepositoryError`
  - Base exception for observability repository errors.
- class: `ObservabilityRepository`
  - Camada de Repositório para Observabilidade.
Abstrai todas as interações diretas com os monitores de saúde e handlers de poison pill.
- method: `ObservabilityRepository.__init__(self, monitor: HealthMonitor, pp_handler: PoisonPillHandler)`
- method: `ObservabilityRepository.get_system_health(self)` -> `dict[str, Any]`
- method: `ObservabilityRepository.check_all_components(self)` -> `dict[str, dict[str, Any]]`
- method: `ObservabilityRepository.get_component_health(self, component: str)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_llm_router_health(self)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_multi_agent_system_health(self)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_poison_pill_handler_health(self)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_quarantined_messages(self, queue: str | None = None)` -> `list[QuarantinedMessage]`
- method: `ObservabilityRepository.release_from_quarantine(self, message_id: str, allow_retry: bool)` -> `QuarantinedMessage`
- method: `ObservabilityRepository.cleanup_expired_quarantine(self)` -> `int`
- method: `ObservabilityRepository.get_poison_pill_stats(self, queue: str | None = None)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_metrics_summary(self)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_user_metrics(self, user_id: str)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_user_activity(self, user_id: str)` -> `dict[str, Any]`
- method: `ObservabilityRepository.get_graph_audit_report(self)` -> `dict[str, Any]`
  - Executa consultas de auditoria no Neo4j para avaliar a higiene do grafo.
- method: `ObservabilityRepository.get_graph_quarantine_items(self, limit: int = 100)` -> `list[dict[str, Any]]`
- method: `ObservabilityRepository.promote_quarantine_item(self, node_id: int)` -> `dict[str, Any]`
- method: `ObservabilityRepository.record_audit_event(self, event: dict[str, Any])` -> `None`
- method: `ObservabilityRepository.export_audit_events_json(self, sanitize: bool = True, **kwargs)` -> `str`
- method: `ObservabilityRepository.get_audit_events(self, user_id: str | None, tool: str | None, status: str | None, start_ts: float | None, end_ts: float | None, endpoint: str | None = None, limit: int = 100, offset: int = 0)` -> `list[dict[str, Any]]`
- method: `ObservabilityRepository.get_audit_events_by_trace_id(self, trace_id: str, limit: int = 2000, offset: int = 0)` -> `list[dict[str, Any]]`
- method: `ObservabilityRepository.get_audit_events_count(self, user_id: str | None, tool: str | None, status: str | None, start_ts: float | None, end_ts: float | None)` -> `int`
- method: `ObservabilityRepository.purge_old_audit_events(self, retention_days: int)` -> `int`
- function: `get_observability_repository(monitor: HealthMonitor = Depends(get_health_monitor), pp_handler: PoisonPillHandler = Depends(get_poison_pill_handler))` -> `ObservabilityRepository`
- function: `record_audit_event_direct(event: dict[str, Any] | None = None, **kwargs: Any)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
