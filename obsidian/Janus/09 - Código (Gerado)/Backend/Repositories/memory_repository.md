---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/memory_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# memory_repository

## Arquivos-fonte
- `backend/app/repositories/memory_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/core/workers/data_harvester.py`
- `backend/app/core/workers/meta_agent_worker.py`
- `backend/app/core/workers/reflexion_worker.py`
- `backend/app/services/autonomy_admin_service.py`

## Símbolos
- class: `MemoryRepository`
  - Camada de Repositório para a Memória Episódica (Qdrant).
Recebe sua dependência de banco de dados via DI.
- method: `MemoryRepository.__init__(self, db: MemoryDBProtocol)`
- method: `MemoryRepository.save_experience(self, experience: Experience)`
  - Salva uma única experiência no banco de dados vetorial.
- method: `MemoryRepository.search_experiences(self, query: str, limit: int | None = 10, min_score: float | None = None)` -> `list[dict[str, Any]]`
  - Busca por experiências no banco de dados vetorial.
- method: `MemoryRepository.search_filtered(self, query: str | None, filters: dict[str, Any], limit: int | None = 10, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryRepository.search_by_timeframe(self, query: str | None, start_ts_ms: int | None, end_ts_ms: int | None, limit: int | None = 10, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryRepository.search_recent_failures(self, limit: int | None = 10, timeframe_seconds: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryRepository.search_recent_lessons(self, limit: int | None = 10, timeframe_seconds: int | None = None, min_score: float | None = None)` -> `list[dict[str, Any]]`
- method: `MemoryRepository.update_experience_metadata(self, experience_id: str, metadata_patch: dict[str, Any])` -> `None`
- function: `get_memory_repository(db: MemoryDBProtocol = Depends(get_memory_db))` -> `MemoryRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
