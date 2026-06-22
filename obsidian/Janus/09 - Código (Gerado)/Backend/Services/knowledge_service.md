---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/knowledge_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_service

## Arquivos-fonte
- `backend/app/services/knowledge_service.py`

## Dependências de código
- Repositórios
  - `knowledge_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/knowledge.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/core/kernel.py`
- `backend/app/planes/knowledge/facade.py`
- `backend/app/services/autonomy_admin_service.py`

## Símbolos
- class: `KnowledgeServiceError`
  - Base exception for knowledge service errors.
- class: `KnowledgeService`
  - Camada de serviço para o Grafo de Conhecimento.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `KnowledgeService.__init__(self, repo: KnowledgeRepository)`
- method: `KnowledgeService.get_stats(self)` -> `dict[str, Any]`
- method: `KnowledgeService.get_code_entities(self, file_path: str | None = None)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.get_entity_details(self, entity_name: str)` -> `dict[str, Any] | None`
- method: `KnowledgeService.get_entity_relationships(self, entity_name: str, rel_type: str | None = None, direction: str = 'both', max_depth: int = 1, limit: int = 20, skip: int = 0)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.get_functions_calling(self, function_name: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.get_files_importing(self, module: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.get_classes_implementing(self, protocol: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.trigger_consolidation(self, limit: int, min_score: float = 0.0)` -> `dict[str, Any]`
- method: `KnowledgeService._build_graph_path_candidates(rel_path: str)` -> `list[str]`
- method: `KnowledgeService._preferred_graph_owner_path(rel_path: str, path_candidates: list[str])` -> `str`
- method: `KnowledgeService._build_self_memory_key(rel_path: str, *, summary_version: str | None, sha_after: str | None)` -> `str`
- method: `KnowledgeService._normalize_symbol_names(raw_symbols: Any)` -> `list[str]`
- method: `KnowledgeService._repair_single_self_memory(self, *, row: dict[str, Any], is_current: bool)` -> `dict[str, int]`
- method: `KnowledgeService.repair_self_memory_graph(self, *, limit: int | None = None)` -> `dict[str, Any]`
- method: `KnowledgeService.get_self_memory_neo4j_audit(self, *, orphan_limit: int = 25)` -> `dict[str, Any]`
- method: `KnowledgeService._index_codebase_impl(self)` -> `dict[str, Any]`
- method: `KnowledgeService.index_codebase(self)` -> `dict[str, Any]`
- method: `KnowledgeService.clear_graph(self, *, user_id: str)` -> `int`
- method: `KnowledgeService.semantic_query(self, question: str, limit: int = 10)` -> `str`
- method: `KnowledgeService._extract_code_tokens(question: str)` -> `list[str]`
- method: `KnowledgeService.ask_code_with_citations(self, question: str, limit: int = 10, citation_limit: int = 8)` -> `dict[str, Any]`
- method: `KnowledgeService.consolidate_document(self, doc_id: str, limit: int = 50)` -> `dict[str, Any]`
- method: `KnowledgeService.find_related_concepts(self, concept: str, max_depth: int = 2, limit: int = 10, skip: int = 0)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.get_node_types(self)` -> `list[str]`
- method: `KnowledgeService.get_health_status(self)` -> `dict[str, Any]`
- method: `KnowledgeService.reindex_graph(self, batch_size: int = 50, labels: list[str] = None)` -> `int`
- method: `KnowledgeService.register_relationship_type(self, name: str)` -> `dict[str, Any]`
- method: `KnowledgeService.list_quarantine_items(self, limit: int = 50)` -> `list[dict[str, Any]]`
- method: `KnowledgeService.promote_quarantine_relationship(self, from_name: str, to_name: str, rel_type: str, source_experience: str)` -> `dict[str, Any]`
- function: `get_knowledge_service(request: Request)` -> `KnowledgeService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
