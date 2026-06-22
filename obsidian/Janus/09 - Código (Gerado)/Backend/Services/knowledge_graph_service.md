---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/knowledge_graph_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_graph_service

## Arquivos-fonte
- `backend/app/services/knowledge_graph_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/admin_graph.py`
- `backend/app/core/memory/generative_memory.py`
- `backend/app/core/workers/knowledge_consolidator_worker.py`

## Símbolos
- class: `KnowledgeGraphService`
  - Serviço responsável por operações de alto nível no Knowledge Graph (Neo4j),
incluindo persistência de entidades, relacionamentos e validação via GraphGuardian.
- method: `KnowledgeGraphService.__init__(self)`
- method: `KnowledgeGraphService.get_db(self)`
- method: `KnowledgeGraphService._run_rows(self, target: Any, query: str, params: dict[str, Any] | None = None)` -> `list[dict[str, Any]]`
- method: `KnowledgeGraphService._ensure_experience_node(self, target: Any, *, experience_id: str, source_metadata: dict[str, Any])` -> `None`
- method: `KnowledgeGraphService._link_self_memory_provenance(self, target: Any, experience_id: str)` -> `None`
- method: `KnowledgeGraphService.persist_experience_node(self, experience: Experience)` -> `str | None`
  - Cria um nó de Experience no grafo e o conecta ao fluxo de memória (NEXT).
Implementa o 'Memory Stream' de Park et al. (2023).
- method: `KnowledgeGraphService.persist_extraction(self, experience_id: str, extracted_data: dict[str, Any], source_metadata: dict[str, Any])` -> `tuple[int, int]`
  - Persiste entidades e relacionamentos extraídos no Neo4j, aplicando validação e quarentena.
- method: `KnowledgeGraphService._prepare_entities_batch(self, entities: list[dict[str, Any]])` -> `list[dict[str, Any]]`
- method: `KnowledgeGraphService._is_noise_entity_name(self, value: str)` -> `bool`
- method: `KnowledgeGraphService._prepare_relationships_batch(self, relationships: list[dict[str, Any]])` -> `list[dict[str, Any]]`
- method: `KnowledgeGraphService._coerce_entity_type(self, type_str: Any)` -> `EntityType`
- method: `KnowledgeGraphService._coerce_relation_type(self, normalized_rel_type: Any)` -> `tuple[RelationType, bool]`
- method: `KnowledgeGraphService._should_quarantine(self, rel: dict[str, Any])` -> `bool`
  - Verifica se o relacionamento deve ir para quarentena.
- method: `KnowledgeGraphService._send_to_quarantine(self, rel: dict[str, Any], context_id: str, reason: str)`
  - Envia item para quarentena.
- method: `KnowledgeGraphService.get_subgraph_from_context(self, node_names: list[str], hops: int = 1)` -> `dict[str, Any]`
  - Retorna um subgrafo contendo os nós especificados e seus vizinhos até 'hops' de distância.
Otimizado para visualização contextual no frontend.
- function: `get_knowledge_graph_service()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
