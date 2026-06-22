---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/meta_agent_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# meta_agent_service

## Arquivos-fonte
- `backend/app/services/meta_agent_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/meta_agent.py`
- `backend/app/api/v1/endpoints/reflexion.py`
- `backend/app/services/autonomy_admin_service.py`

## Símbolos
- class: `MetaAgentServiceError`
  - Base exception for meta-agent service errors.
- class: `MetaAgentService`
  - Camada de serviço para o Meta-Agente de Auto-Otimização.
Abstrai a lógica de controle do ciclo de vida do meta-agente da camada de API.
- method: `MetaAgentService._get_agent(self)` -> `MetaAgent`
- method: `MetaAgentService.run_analysis_cycle(self)` -> `StateReport`
- method: `MetaAgentService.get_latest_report(self)` -> `StateReport | None`
- method: `MetaAgentService.start_heartbeat(self, interval_minutes: int)` -> `bool`
- method: `MetaAgentService.stop_heartbeat(self)`
- method: `MetaAgentService.get_heartbeat_status(self)` -> `dict[str, Any]`
- method: `MetaAgentService.get_health_status(self)` -> `dict[str, Any]`
- function: `get_meta_agent_service()` -> `MetaAgentService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
