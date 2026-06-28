from fastapi import APIRouter, Depends, HTTPException

from app.planes.knowledge import KnowledgeFacade

from .deps import get_knowledge_facade
from .models import (
    ExperimentalCompareRequest,
    ExperimentalIndexBuildRequest,
    ExperimentalIndexBuildResponse,
    ExperimentalKnowledgeHealthResponse,
)

router = APIRouter(prefix="/experimental")


@router.get(
    "/health",
    response_model=ExperimentalKnowledgeHealthResponse,
    summary="Health snapshot do backend experimental de retrieval",
)
async def experimental_health_snapshot(knowledge: KnowledgeFacade = Depends(get_knowledge_facade)):
    return ExperimentalKnowledgeHealthResponse(**knowledge.health_snapshot())


@router.post(
    "/index/build",
    response_model=ExperimentalIndexBuildResponse,
    summary="Build ou dry-run do índice experimental de retrieval",
)
async def build_experimental_index(
    payload: ExperimentalIndexBuildRequest,
    knowledge: KnowledgeFacade = Depends(get_knowledge_facade),
):
    result = await knowledge.build_experimental_index(
        domain=payload.domain,
        user_id=payload.user_id,
        knowledge_space_id=payload.knowledge_space_id,
        doc_id=payload.doc_id,
        rebuild_full=payload.rebuild_full,
        since_ts=payload.since_ts,
        dry_run=payload.dry_run,
    )
    return ExperimentalIndexBuildResponse(
        dry_run=result.dry_run,
        output_dir=result.output_dir,
        manifest=result.manifest.__dict__,
    )


@router.post("/compare", summary="Compara baseline Qdrant com retrieval experimental")
async def compare_experimental_retrieval(
    payload: ExperimentalCompareRequest,
    knowledge: KnowledgeFacade = Depends(get_knowledge_facade),
):
    if payload.operation not in {
        "search_documents",
        "search_user_chat",
        "search_user_memory",
    }:
        raise HTTPException(status_code=422, detail="operation inválida para compare endpoint")

    return await knowledge.compare_retrieval(
        operation=payload.operation,
        query=payload.query,
        limit=payload.limit,
        min_score=payload.min_score,
        session_id=payload.session_id,
        role=payload.role,
        memory_type=payload.memory_type,
        origin=payload.origin,
        doc_id=payload.doc_id,
        knowledge_space_id=payload.knowledge_space_id,
        start_ts=payload.start_ts,
        end_ts=payload.end_ts,
        exclude_duplicate=payload.exclude_duplicate,
    )
