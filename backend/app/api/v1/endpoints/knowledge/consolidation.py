from fastapi import APIRouter, Depends, Request

from app.services.knowledge_service import KnowledgeService, get_knowledge_service

from .deps import resolve_knowledge_user_id
from .models import (
    ConsolidationRequest,
    ConsolidationResponse,
    DocConsolidationRequest,
)
from .ops import KnowledgeOpsService, get_knowledge_ops_service

router = APIRouter()


@router.post(
    "/consolidate",
    response_model=ConsolidationResponse,
    summary="Dispara consolidação de conhecimento via fila",
)
async def publish_consolidation(
    request: ConsolidationRequest,
    ops: KnowledgeOpsService = Depends(get_knowledge_ops_service),
):
    result = await ops.publish_consolidation(request.model_dump())
    return ConsolidationResponse(message="Tarefa de consolidação publicada.", stats=result)


@router.post(
    "/consolidate/document",
    response_model=ConsolidationResponse,
    summary="Consolida conhecimento a partir de um documento (doc_id) do usuário",
)
async def consolidate_document(
    request: DocConsolidationRequest,
    http: Request,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    stats = await service.consolidate_document(
        user_id=resolve_knowledge_user_id(http, None),
        doc_id=request.doc_id,
        limit=request.limit,
    )
    return ConsolidationResponse(message="Consolidação de documento concluída.", stats=stats)
