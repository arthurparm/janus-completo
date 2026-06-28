from fastapi import APIRouter, Depends, Query, Request

from app.models.knowledge import CodeEntity
from app.services.knowledge_service import KnowledgeService, get_knowledge_service

from .deps import resolve_knowledge_user_id
from .models import (
    ClearGraphResponse,
    CodeCitation,
    CodeQuestionRequest,
    CodeQuestionResponse,
    EntityRelationshipsItem,
    EntityRelationshipsResponse,
    IndexResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    NodeTypesResponse,
    PromoteQuarantineRequest,
    PromoteQuarantineResponse,
    QuarantineItem,
    QuarantineListResponse,
    RegisterRelTypeRequest,
    RegisterRelTypeResponse,
    RelatedConceptItem,
    RelatedConceptsRequest,
    RelatedConceptsResponse,
    ReindexRequest,
    ReindexResponse,
)

router = APIRouter()


@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código")
async def trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.index_codebase()


@router.get("/stats", summary="Estatísticas do grafo")
async def get_knowledge_stats(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.get_stats()


@router.get("/entities", response_model=list[CodeEntity], summary="Lista entidades de código")
async def get_code_entities(
    file_path: str | None = Query(None, description="Filtra por caminho de arquivo."),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return await service.get_code_entities(file_path)


@router.get(
    "/entity/{entity_name}/relationships",
    response_model=EntityRelationshipsResponse,
    summary="Navega relacionamentos de uma entidade",
)
async def get_entity_relationships(
    entity_name: str,
    rel_type: str | None = Query(None, description="Filtra pelo tipo de relacionamento"),
    direction: str = Query(
        "both",
        pattern=r"^(out|in|both)$",
        description="Direção do relacionamento (out/in/both)",
    ),
    max_depth: int = Query(1, ge=1, le=5, description="Profundidade máxima de navegação"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    skip: int = Query(0, ge=0, description="Offset para paginação"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_entity_relationships(
        entity_name=entity_name,
        rel_type=rel_type,
        direction=direction,
        max_depth=max_depth,
        limit=limit,
        skip=skip,
    )
    items = [EntityRelationshipsItem(**row) for row in rows]
    return EntityRelationshipsResponse(results=items)


@router.delete("/clear", response_model=ClearGraphResponse, summary="Limpa o grafo do usuário autenticado")
async def clear_knowledge_graph(
    request: Request,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    remaining_nodes = await service.clear_graph(user_id=resolve_knowledge_user_id(request, None))
    return {
        "status": "success",
        "message": "Grafo de conhecimento limpo com sucesso",
        "remaining_nodes": remaining_nodes,
    }


@router.post(
    "/query",
    response_model=KnowledgeQueryResponse,
    summary="Consulta o grafo de conhecimento (Graph RAG)",
)
async def query_knowledge(
    request: KnowledgeQueryRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    answer = await service.semantic_query(request.query, limit=request.limit)
    return KnowledgeQueryResponse(answer=answer)


@router.post(
    "/query/code",
    response_model=CodeQuestionResponse,
    summary="Pergunta sobre codigo com citacoes de arquivo e linha",
)
async def query_code_with_citations(
    request: CodeQuestionRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    result = await service.ask_code_with_citations(
        question=request.question,
        limit=request.limit,
        citation_limit=request.citation_limit,
    )
    citations = [CodeCitation(**row) for row in result.get("citations", [])]
    answer = result.get("answer", "")
    if not citations:
        answer = (
            "Nao encontrei citacoes rastreaveis para responder com seguranca sobre codigo. "
            "Reformule a pergunta ou indexe/reindexe a base."
        )
    return CodeQuestionResponse(answer=answer, citations=citations)


@router.post(
    "/concepts/related",
    response_model=RelatedConceptsResponse,
    summary="Busca conceitos relacionados",
)
async def related_concepts(
    request: RelatedConceptsRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    results = await service.find_related_concepts(
        concept=request.concept,
        max_depth=request.max_depth,
        limit=request.limit,
        skip=request.skip,
    )
    items = [RelatedConceptItem(**row) for row in results]
    return RelatedConceptsResponse(results=items)


@router.post(
    "/concepts/reindex",
    response_model=ReindexResponse,
    summary="Reindexa (gera embeddings) para conceitos que ainda não possuem",
    description="Útil após migrações ou inserções em massa. Processa em lotes.",
)
async def reindex_concepts(
    request: ReindexRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    count = await service.reindex_graph(batch_size=request.batch_size, labels=request.labels)
    return ReindexResponse(status="success", updated_count=count)


@router.get(
    "/node-types",
    response_model=NodeTypesResponse,
    summary="Lista tipos de nós presentes no grafo",
)
async def get_node_types(service: KnowledgeService = Depends(get_knowledge_service)):
    types = await service.get_node_types()
    return NodeTypesResponse(types=types)


@router.post(
    "/relationship-types/register",
    response_model=RegisterRelTypeResponse,
    summary="Registra um tipo canônico de relacionamento",
)
async def register_relationship_type(
    request: RegisterRelTypeRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return RegisterRelTypeResponse(**(await service.register_relationship_type(request.name)))


@router.get(
    "/quarantine",
    response_model=QuarantineListResponse,
    summary="Lista itens em quarentena no grafo",
)
async def list_quarantine(
    limit: int = 50,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.list_quarantine_items(limit=limit)
    return QuarantineListResponse(items=[QuarantineItem(**row) for row in rows])


@router.post(
    "/quarantine/promote",
    response_model=PromoteQuarantineResponse,
    summary="Promove um item de quarentena a relacionamento no grafo",
)
async def promote_quarantine(
    request: PromoteQuarantineRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    res = await service.promote_quarantine_relationship(
        from_name=request.from_name,
        to_name=request.to_name,
        rel_type=request.type,
        source_experience=request.source_experience,
    )
    return PromoteQuarantineResponse(
        status=res.get("status"),
        from_name=request.from_name,
        to_name=request.to_name,
        type=request.type,
    )


@router.get(
    "/functions/calling",
    response_model=list[CodeEntity],
    summary="Lista funções que chamam a função informada",
)
async def functions_calling(
    name: str = Query(..., description="Nome da função alvo"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_functions_calling(function_name=name)
    return [CodeEntity(**row) for row in rows]


@router.get(
    "/files/importing",
    response_model=list[CodeEntity],
    summary="Lista arquivos que importam o módulo/arquivo informado",
)
async def files_importing(
    module: str = Query(..., description="Nome do módulo ou caminho do arquivo"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_files_importing(module=module)
    return [CodeEntity(**row) for row in rows]


@router.get(
    "/classes/implementations",
    response_model=list[CodeEntity],
    summary="Lista classes que implementam o protocolo/interface informado",
)
async def classes_implementations(
    protocol: str = Query(..., description="Nome do protocolo/interface"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_classes_implementing(protocol=protocol)
    return [CodeEntity(**row) for row in rows]
