---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/memory_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# memory_service

## Arquivos-fonte
- `backend/app/services/memory_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/memory.py`
- `backend/app/api/v1/endpoints/rag.py`
- `backend/app/api/v1/endpoints/reflexion.py`
- `backend/app/core/autonomy/goal_manager.py`
- `backend/app/core/kernel.py`
- `backend/app/core/optimization/reflexion_core.py`
- `backend/app/core/workers/life_cycle_worker.py`
- `backend/app/core/workers/meta_agent_worker.py`
- `backend/app/core/workers/reflexion_worker.py`
- `backend/app/planes/knowledge/facade.py`
- `backend/app/repositories/reflexion_repository.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- class: `MemoryServiceError`
  - Base exception for memory service errors.
- class: `MemoryService`
  - Camada de serviÃ§o para operaÃ§Ãµes relacionadas Ã  memÃ³ria episÃ³dica.
Orquestra a lÃ³gica de negÃ³cio, recebendo suas dependÃªncias via DI.
- method: `MemoryService.__init__(self, repo: MemoryRepositoryProtocol)`
- method: `MemoryService._emit_step_telemetry(self, *, step: str, started_at: float, confidence: float | None, error_code: str | None = None, extra: dict[str, Any] | None = None)` -> `dict[str, Any]`
- method: `MemoryService.add_experience(self, type: str, content: str, metadata: dict[str, Any])` -> `Experience`
  - Cria uma nova experiÃªncia e a delega para o repositÃ³rio salvar.
- method: `MemoryService.recall_experiences(self, query: str, limit: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
  - Delega a busca por experiÃªncias para o repositÃ³rio.
- method: `MemoryService.recall_filtered(self, query: str | None, filters: dict[str, Any], limit: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryService.recall_by_timeframe(self, query: str | None, start_ts_ms: int | None, end_ts_ms: int | None, limit: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryService.recall_recent_failures(self, limit: int | None = 10, timeframe_seconds: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryService.recall_recent_lessons(self, limit: int | None = 10, timeframe_seconds: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryService.index_interaction(self, content: str, session_id: str, role: str)` -> `None`
  - Indexa uma interaÃ§Ã£o de chat (async) no Qdrant.
- function: `get_memory_service(request: Request)` -> `MemoryService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
