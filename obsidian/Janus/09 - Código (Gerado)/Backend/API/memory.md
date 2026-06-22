---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/memory.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# memory

## Arquivos-fonte
- `backend/app/api/v1/endpoints/memory.py`

## Rotas
- `GET /generative`
- `GET /preferences`
- `GET /secrets`
- `GET /timeline`
- `POST /generative`
- `POST /secrets`

## Dependências de código
- Serviços
  - `memory_service`
  - `secret_memory_service`
  - `user_preference_memory_service`

## Símbolos
- class: `MemoryTimelineItem`
- class: `UserPreferenceMemoryItem`
- class: `SecretMemoryCreateRequest`
- class: `SecretMemoryItem`
- function: `_parse_iso_to_ms(value: str | None)` -> `int | None`
- function: `_coerce_ts_ms(value: Any | None)` -> `int | None`
- function: `_experience_to_item(exp: ScoredExperience)` -> `MemoryTimelineItem`
- function: `_point_to_item(point: Any)` -> `MemoryTimelineItem`
- function: `get_knowledge_facade(request: Request)`
- function: `_sort_and_dedupe_timeline(items: list[MemoryTimelineItem], limit: int)` -> `list[MemoryTimelineItem]`
- function: `get_memories_timeline(request: Request, start_date: str | None = Query(None, description='Start date (ISO 8601), inclusive'), end_date: str | None = Query(None, description='End date (ISO 8601), inclusive'), query: str | None = Query(None, description='Semantic text query to filter memories'), limit: int = Query(10, ge=1, le=100), min_score: float | None = Query(None, ge=0.0, le=1.0), conversation_id: str | None = Query(None, description='Conversation ID for scoped timeline'), service: MemoryService = Depends(get_memory_service), knowledge = Depends(get_knowledge_facade))`
  - Retrieves memories within a specific timeframe ("Time Travel").
Allows semantic filtering via `query`.
- function: `get_generative_memories(request: Request, query: str = Query(..., description='Query for memory retrieval'), limit: int = Query(10, ge=1, le=100), type: str | None = Query(None, description='Filter by memory type (episodic|semantic|procedural)'), conversation_id: str | None = Query(None, description='Filter by conversation_id'))`
  - Retrieves memories using the Generative Agents scoring (Recency * Importance * Relevance).
- function: `add_generative_memory(request: Request, content: str, importance: float | None = Query(None, ge=0.0, le=10.0), type: str = 'episodic', conversation_id: str | None = Query(None, description='Conversation ID to bind memory'), session_id: str | None = Query(None, description='Session ID alias (defaults to conversation_id)'))`
  - Adds a memory to the Generative Stream (calculates importance if missing).
- function: `get_user_preferences(request: Request, conversation_id: str | None = Query(None, description='Optional conversation filter'), query: str | None = Query(None, description='Optional semantic query'), limit: int = Query(20, ge=1, le=100), active_only: bool = Query(True))`
- function: `get_user_secrets(request: Request, conversation_id: str | None = Query(None, description='Optional conversation filter'), query: str | None = Query(None, description='Optional semantic query'), limit: int = Query(20, ge=1, le=100), active_only: bool = Query(True))`
- function: `add_user_secret(request: Request, body: SecretMemoryCreateRequest)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
