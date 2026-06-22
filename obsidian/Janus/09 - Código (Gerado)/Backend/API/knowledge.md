---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/knowledge.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge

## Arquivos-fonte
- `backend/app/api/v1/endpoints/knowledge.py`

## Rotas
- `DELETE /clear`
- `GET /classes/implementations`
- `GET /entities`
- `GET /entity/{entity_name}/relationships`
- `GET /experimental/health`
- `GET /files/importing`
- `GET /functions/calling`
- `GET /health`
- `GET /health/detailed`
- `GET /node-types`
- `GET /quarantine`
- `GET /spaces`
- `GET /spaces/{knowledge_space_id}`
- `GET /stats`
- `POST /concepts/reindex`
- `POST /concepts/related`
- `POST /consolidate`
- `POST /consolidate/document`
- `POST /experimental/compare`
- `POST /experimental/index/build`
- `POST /health/reset-circuit-breaker`
- `POST /index`
- `POST /quarantine/promote`
- `POST /query`
- `POST /query/code`
- `POST /relationship-types/register`
- `POST /spaces`
- `POST /spaces/{knowledge_space_id}/consolidate`
- `POST /spaces/{knowledge_space_id}/documents/{doc_id}/attach`
- `POST /spaces/{knowledge_space_id}/query`

## Dependências de código
- Serviços
  - `knowledge_service`
  - `knowledge_space_service`

## Símbolos
- function: `get_knowledge_facade(request: Request)` -> `KnowledgeFacade`
- function: `_resolve_knowledge_user_id(request: Request | None, explicit_user_id: str | None)` -> `str`
- class: `IndexResponse`
- class: `KnowledgeQueryResponse`
- class: `CodeCitation`
- class: `CodeQuestionRequest`
- class: `CodeQuestionResponse`
- class: `RelatedConceptsRequest`
- class: `RelatedConceptItem`
- class: `RelatedConceptsResponse`
- class: `ReindexRequest`
- class: `ReindexResponse`
- class: `EntityRelationshipsItem`
- class: `EntityRelationshipsResponse`
- class: `ClearGraphResponse`
- class: `KnowledgeQueryRequest`
- class: `KnowledgeHealthResponse`
- class: `ExperimentalKnowledgeHealthResponse`
- class: `ExperimentalIndexBuildRequest`
- class: `ExperimentalIndexBuildResponse`
- class: `ExperimentalCompareRequest`
- class: `ConsolidationRequest`
- class: `ConsolidationResponse`
- class: `KnowledgeSpaceCreateRequest`
- class: `KnowledgeSpaceResponse`
- class: `KnowledgeSpaceStatusResponse`
- class: `KnowledgeSpaceListResponse`
- class: `AttachDocumentRequest`
- class: `KnowledgeSpaceConsolidationRequest`
- class: `KnowledgeSpaceQueryRequest`
- class: `KnowledgeSpaceQueryResponse`
- function: `trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service))`
- function: `get_knowledge_stats(service: KnowledgeService = Depends(get_knowledge_service))`
- function: `get_code_entities(file_path: str | None = Query(None, description='Filtra por caminho de arquivo.'), service: KnowledgeService = Depends(get_knowledge_service))`
- function: `get_entity_relationships(entity_name: str, rel_type: str | None = Query(None, description='Filtra pelo tipo de relacionamento'), direction: str = Query('both', pattern='^(out|in|both)$', description='Direção do relacionamento (out/in/both)'), max_depth: int = Query(1, ge=1, le=5, description='Profundidade máxima de navegação'), limit: int = Query(20, ge=1, le=100, description='Limite de resultados'), skip: int = Query(0, ge=0, description='Offset para paginação'), service: KnowledgeService = Depends(get_knowledge_service))`
- function: `clear_knowledge_graph(request: Request, service: KnowledgeService = Depends(get_knowledge_service))`
- function: `query_knowledge(request: KnowledgeQueryRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- function: `query_code_with_citations(request: CodeQuestionRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- function: `related_concepts(request: RelatedConceptsRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- function: `reindex_concepts(request: ReindexRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- class: `NodeTypesResponse`
- function: `get_node_types(service: KnowledgeService = Depends(get_knowledge_service))`
- function: `knowledge_health(service: KnowledgeService = Depends(get_knowledge_service))`
- function: `reset_circuit_breaker()`
  - Reseta o circuit breaker do Qdrant manualmente.
Útil quando o Qdrant recupera após falhas temporárias.
- function: `detailed_health_check(service: KnowledgeService = Depends(get_knowledge_service))`
  - Retorna status detalhado incluindo circuit breaker, Qdrant e métricas de saúde.
- function: `experimental_health_snapshot(knowledge: KnowledgeFacade = Depends(get_knowledge_facade))`
- function: `build_experimental_index(payload: ExperimentalIndexBuildRequest, knowledge: KnowledgeFacade = Depends(get_knowledge_facade))`
- function: `compare_experimental_retrieval(payload: ExperimentalCompareRequest, knowledge: KnowledgeFacade = Depends(get_knowledge_facade))`
- function: `publish_consolidation(request: ConsolidationRequest)`
- class: `DocConsolidationRequest`
- function: `consolidate_document(request: DocConsolidationRequest, http: Request, service: KnowledgeService = Depends(get_knowledge_service))`
- class: `RegisterRelTypeRequest`
- class: `RegisterRelTypeResponse`
- function: `register_relationship_type(request: RegisterRelTypeRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- class: `QuarantineItem`
- class: `QuarantineListResponse`
- function: `list_quarantine(limit: int = 50, service: KnowledgeService = Depends(get_knowledge_service))`
- class: `PromoteQuarantineRequest`
- class: `PromoteQuarantineResponse`
- function: `promote_quarantine(request: PromoteQuarantineRequest, service: KnowledgeService = Depends(get_knowledge_service))`
- function: `functions_calling(name: str = Query(..., description='Nome da função alvo'), service: KnowledgeService = Depends(get_knowledge_service))`
- function: `files_importing(module: str = Query(..., description='Nome do módulo ou caminho do arquivo'), service: KnowledgeService = Depends(get_knowledge_service))`
- function: `classes_implementations(protocol: str = Query(..., description='Nome do protocolo/interface'), service: KnowledgeService = Depends(get_knowledge_service))`
- function: `create_knowledge_space(payload: KnowledgeSpaceCreateRequest, request: Request, user_id: str | None = Query(None), service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`
- function: `list_knowledge_spaces(request: Request, user_id: str | None = Query(None), limit: int = 100, service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`
- function: `get_knowledge_space_status(knowledge_space_id: str, request: Request, user_id: str | None = Query(None), service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`
- function: `attach_document_to_space(knowledge_space_id: str, doc_id: str, payload: AttachDocumentRequest, request: Request, user_id: str | None = Query(None), service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`
- function: `consolidate_knowledge_space(knowledge_space_id: str, payload: KnowledgeSpaceConsolidationRequest, request: Request, user_id: str | None = Query(None), service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`
- function: `query_knowledge_space(knowledge_space_id: str, payload: KnowledgeSpaceQueryRequest, request: Request, user_id: str | None = Query(None), service: KnowledgeSpaceService = Depends(get_knowledge_space_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
