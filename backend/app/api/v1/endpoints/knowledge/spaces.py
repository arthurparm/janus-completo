from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.services.knowledge_space_service import (
    KnowledgeSpaceService,
    get_knowledge_space_service,
)

from .deps import resolve_knowledge_user_id
from .models import (
    AttachDocumentRequest,
    ConsolidationResponse,
    KnowledgeSpaceConsolidationRequest,
    KnowledgeSpaceCreateRequest,
    KnowledgeSpaceListResponse,
    KnowledgeSpaceQueryRequest,
    KnowledgeSpaceQueryResponse,
    KnowledgeSpaceResponse,
    KnowledgeSpaceStatusResponse,
)
from .ops import KnowledgeOpsService, get_knowledge_ops_service

router = APIRouter(prefix="/spaces")


@router.post(
    "",
    response_model=KnowledgeSpaceResponse,
    summary="Cria um knowledge space isolado por obra/coleção",
)
async def create_knowledge_space(
    payload: KnowledgeSpaceCreateRequest,
    request: Request,
    user_id: str | None = Query(None),
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    row = service.create_space(
        user_id=resolve_knowledge_user_id(request, user_id),
        name=payload.name,
        source_type=payload.source_type,
        source_id=payload.source_id,
        edition_or_version=payload.edition_or_version,
        language=payload.language,
        parent_collection_id=payload.parent_collection_id,
        description=payload.description,
    )
    return KnowledgeSpaceResponse(**row)


@router.get(
    "",
    response_model=KnowledgeSpaceListResponse,
    summary="Lista knowledge spaces do usuário",
)
async def list_knowledge_spaces(
    request: Request,
    user_id: str | None = Query(None),
    limit: int = 100,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    rows = service.list_spaces(user_id=resolve_knowledge_user_id(request, user_id), limit=limit)
    return KnowledgeSpaceListResponse(items=[KnowledgeSpaceResponse(**row) for row in rows])


@router.get(
    "/{knowledge_space_id}",
    response_model=KnowledgeSpaceStatusResponse,
    summary="Retorna status e progresso de um knowledge space",
)
async def get_knowledge_space_status(
    knowledge_space_id: str,
    request: Request,
    user_id: str | None = Query(None),
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    row = service.get_space_status(
        knowledge_space_id=knowledge_space_id,
        user_id=resolve_knowledge_user_id(request, user_id),
    )
    return KnowledgeSpaceStatusResponse(**row)


@router.post(
    "/{knowledge_space_id}/documents/{doc_id}/attach",
    response_model=dict[str, Any],
    summary="Associa um documento existente a um knowledge space",
)
async def attach_document_to_space(
    knowledge_space_id: str,
    doc_id: str,
    payload: AttachDocumentRequest,
    request: Request,
    user_id: str | None = Query(None),
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    row = await service.attach_document(
        knowledge_space_id=knowledge_space_id,
        doc_id=doc_id,
        user_id=resolve_knowledge_user_id(request, user_id),
        source_type=payload.source_type,
        source_id=payload.source_id,
        doc_role=payload.doc_role,
        edition_or_version=payload.edition_or_version,
        language=payload.language,
        parent_collection_id=payload.parent_collection_id,
    )
    return {"status": "ok", "document": row}


@router.post(
    "/{knowledge_space_id}/consolidate",
    response_model=ConsolidationResponse,
    summary="Consolida estruturalmente um knowledge space",
)
async def consolidate_knowledge_space(
    knowledge_space_id: str,
    payload: KnowledgeSpaceConsolidationRequest,
    request: Request,
    user_id: str | None = Query(None),
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
    ops: KnowledgeOpsService = Depends(get_knowledge_ops_service),
):
    resolved_user_id = resolve_knowledge_user_id(request, user_id)
    service.mark_consolidation_requested(
        knowledge_space_id=knowledge_space_id,
        user_id=resolved_user_id,
    )
    stats = await ops.publish_consolidation(
        {
            "mode": "knowledge_space",
            "knowledge_space_id": knowledge_space_id,
            "user_id": resolved_user_id,
            "limit_docs": payload.limit_docs,
        },
        correlation_id=knowledge_space_id,
    )
    stats["status_url"] = f"/api/v1/knowledge/spaces/{knowledge_space_id}?user_id={resolved_user_id}"
    return ConsolidationResponse(message="Consolidação estrutural publicada.", stats=stats)


@router.post(
    "/{knowledge_space_id}/query",
    response_model=KnowledgeSpaceQueryResponse,
    summary="Consulta knowledge space com fallback canônico para chunk_only",
)
async def query_knowledge_space(
    knowledge_space_id: str,
    payload: KnowledgeSpaceQueryRequest,
    request: Request,
    user_id: str | None = Query(None),
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    result = await service.query_space(
        knowledge_space_id=knowledge_space_id,
        user_id=resolve_knowledge_user_id(request, user_id),
        question=payload.question,
        mode=payload.mode,
        limit=payload.limit,
    )
    return KnowledgeSpaceQueryResponse(**result)
