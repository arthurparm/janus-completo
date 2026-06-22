---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/knowledge_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_repository

## Arquivos-fonte
- `backend/app/repositories/knowledge_repository.py`

## Dependências de código
- Repositórios
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/code_hybrid_search_service.py`
- `backend/app/services/data_retention_service.py`
- `backend/app/services/dedupe_service.py`
- `backend/app/services/knowledge_service.py`

## Símbolos
- class: `KnowledgeRepository`
  - Camada de RepositÃ³rio para o Grafo de Conhecimento.
Usa Enums para todas as constantes do grafo, evitando "magic strings".
- method: `KnowledgeRepository.__init__(self, db: GraphDatabase)`
- method: `KnowledgeRepository._is_retryable_transient(exc: Exception)` -> `bool`
- method: `KnowledgeRepository.get_node_and_relationship_stats(self)` -> `dict[str, list]`
- method: `KnowledgeRepository.find_code_entities(self, file_path: str | None = None)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.find_entity_details(self, entity_name: str)` -> `dict[str, Any] | None`
- method: `KnowledgeRepository.save_code_structure(self, parser: CodeParser)`
- method: `KnowledgeRepository.clear_all_data(self)` -> `int`
- method: `KnowledgeRepository.delete_user_data(self, user_id: str)` -> `int`
- method: `KnowledgeRepository.clear_code_entities(self)`
- method: `KnowledgeRepository.bulk_merge_calls(self, calls: list[dict[str, Any]])`
- method: `KnowledgeRepository._dedupe_calls(calls: list[dict[str, Any]])` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.dedupe_functions_and_classes(self)` -> `dict[str, int]`
  - Deduplica nÃ³s Function/Class mantendo relacionamentos chave.
- method: `KnowledgeRepository.dedupe_concepts(self)` -> `dict[str, int]`
  - Deduplica conceitos por nome e mantÃ©m RELATES_TO.
- method: `KnowledgeRepository.dedupe_files(self)` -> `dict[str, int]`
  - Deduplica arquivos por path e mantÃ©m RELATES_TO.
- method: `KnowledgeRepository.find_related_concepts(self, concept: str, max_depth: int = 2, limit: int = 10, skip: int = 0)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.find_entity_relationships(self, entity_name: str, rel_type: str | None = None, direction: str = 'both', max_depth: int = 1, limit: int = 20, skip: int = 0)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.get_node_types(self)` -> `list[str]`
- method: `KnowledgeRepository.find_functions_calling(self, function_name: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.find_files_importing(self, module: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.find_classes_implementing(self, protocol: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.find_code_citations(self, tokens: list[str], limit: int = 10)` -> `list[dict[str, Any]]`
- method: `KnowledgeRepository.merge_experience_mentions(self, experience: dict[str, Any], concepts: list[str])` -> `None`
- function: `get_knowledge_repository(db: GraphDatabase = Depends(get_graph_db))` -> `'KnowledgeRepository'`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
