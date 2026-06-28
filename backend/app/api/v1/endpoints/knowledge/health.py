from fastapi import APIRouter, Depends

from app.services.knowledge_service import KnowledgeService, get_knowledge_service

from .models import KnowledgeHealthResponse
from .ops import KnowledgeOpsService, get_knowledge_ops_service

router = APIRouter()


@router.get(
    "/health",
    response_model=KnowledgeHealthResponse,
    summary="Health check da memória semântica",
)
async def knowledge_health(service: KnowledgeService = Depends(get_knowledge_service)):
    return KnowledgeHealthResponse(**(await service.get_health_status()))


@router.post("/health/reset-circuit-breaker", summary="Reseta o circuit breaker do Qdrant")
async def reset_circuit_breaker(ops: KnowledgeOpsService = Depends(get_knowledge_ops_service)):
    return await ops.reset_circuit_breaker()


@router.get("/health/detailed", summary="Status detalhado do sistema de memória")
async def detailed_health_check(ops: KnowledgeOpsService = Depends(get_knowledge_ops_service)):
    return await ops.get_detailed_health_status()
