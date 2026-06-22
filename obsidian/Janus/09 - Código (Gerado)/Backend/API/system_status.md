---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/system_status.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# system_status

## Arquivos-fonte
- `backend/app/api/v1/endpoints/system_status.py`

## Rotas
- `GET /db/validate`
- `GET /health/services`
- `GET /status`
- `GET /status/user`
- `POST /db/migrate`

## Dependências de código
- Serviços
  - `db_migration_service`
  - `knowledge_service`
  - `llm_service`
  - `observability_service`
  - `optimization_service`
  - `system_status_service`
- Repositórios
  - `user_repository`

## Símbolos
- class: `StatusResponse`
- class: `ServiceHealthItem`
- class: `ServiceHealthResponse`
- class: `UserStatusResponse`
- function: `get_system_status()`
  - Delega a obtenção do status da aplicação para o SystemStatusService.
- function: `get_services_health(observability: ObservabilityService = Depends(get_observability_service), knowledge: KnowledgeService = Depends(get_knowledge_service), llm: LLMService = Depends(get_llm_service), optimization: OptimizationService = Depends(get_optimization_service))`
- function: `get_user_status(request: Request, user_id: int | None = None, observability: ObservabilityService = Depends(get_observability_service))`
- function: `validate_db_schema()`
- function: `migrate_db_schema()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
