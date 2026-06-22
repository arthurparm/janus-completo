---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/code_hybrid_search_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# code_hybrid_search_service

## Arquivos-fonte
- `backend/app/services/code_hybrid_search_service.py`

## Dependências de código
- Repositórios
  - `knowledge_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/rag.py`
- `backend/app/services/autonomy_admin_service.py`

## Símbolos
- function: `_question_tokens(query: str)` -> `list[str]`
- function: `_coerce_score(value: Any)` -> `float`
- function: `_primary_source(sources: set[str])` -> `str`
- class: `_AggregateCandidate`
- method: `_AggregateCandidate.__post_init__(self)` -> `None`
- method: `_AggregateCandidate.add(self, *, source: str, rrf_score: float, raw_item: dict[str, Any], preferred_content: str | None = None, file_path: str | None = None, line: int | None = None, concept: str | None = None, relationship: str | None = None)` -> `None`
- method: `_AggregateCandidate.source_count(self)` -> `int`
- method: `_AggregateCandidate.fused_score(self)` -> `float`
- method: `_AggregateCandidate.primary_source(self)` -> `str`
- class: `CodeHybridSearchService`
- method: `CodeHybridSearchService.__init__(self, *, graph_db_getter: Callable[[], Awaitable[Any]] = get_graph_db, memory_db_getter: Callable[[], Awaitable[Any]] = get_memory_db, knowledge_repo_factory: type[KnowledgeRepository] = KnowledgeRepository)` -> `None`
- method: `CodeHybridSearchService.search(self, *, query: str, limit: int = 5, min_score: float | None = None, user_id: str | None = None, route_decision: RouteDecision | None = None)` -> `dict[str, Any]`
- method: `CodeHybridSearchService._merge_lexical_rows(self, aggregates: dict[str, _AggregateCandidate], rows: list[dict[str, Any]])` -> `None`
- method: `CodeHybridSearchService._merge_vector_rows(self, aggregates: dict[str, _AggregateCandidate], rows: list[dict[str, Any]])` -> `None`
- method: `CodeHybridSearchService._merge_graph_rows(self, aggregates: dict[str, _AggregateCandidate], rows: list[dict[str, Any]])` -> `None`
- function: `get_code_hybrid_search_service()` -> `CodeHybridSearchService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
