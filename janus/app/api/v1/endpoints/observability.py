import structlog
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.observability_service import (
    ObservabilityService,
    get_observability_service
)

router = APIRouter(tags=["Observability"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class ReleaseQuarantineRequest(BaseModel):
    message_id: str
    allow_retry: bool = False

# --- Endpoints ---

@router.get("/health/system", summary="Retorna a saúde agregada do sistema")
async def get_system_health(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a busca da saúde do sistema para o ObservabilityService."""
    # ObservabilityServiceError é tratado pelo exception handler central -> 500
    return await service.get_system_health()

@router.post("/health/check-all", summary="Força a execução de todos os health checks")
async def check_all_components(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a execução de todos os health checks para o ObservabilityService."""
    return await service.check_all_components()

@router.get("/health/components/llm_manager", summary="Health do componente LLM Manager")
async def health_llm_manager(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_llm_manager_health()

@router.get("/health/components/multi_agent_system", summary="Health do componente Multi-Agent System")
async def health_multi_agent(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_multi_agent_system_health()

@router.get("/health/components/poison_pill_handler", summary="Health do componente Poison Pill Handler")
async def health_poison_pill_handler(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_poison_pill_handler_health()

@router.get("/poison-pills/quarantined", summary="Retorna mensagens em quarentena")
async def get_quarantined_messages(
        service: ObservabilityService = Depends(get_observability_service),
        queue: Optional[str] = None
):
    """Delega a busca de mensagens em quarentena para o ObservabilityService."""
    messages = service.get_quarantined_messages(queue=queue)
    return {
        "total_quarantined": len(messages),
        "messages": [
            {
                "message_id": msg.message_id,
                "queue": msg.queue,
                "reason": msg.reason,
                "failure_count": msg.failure_record.failure_count,
                "quarantined_at": msg.quarantined_at.isoformat(),
            }
            for msg in messages
        ]
    }

@router.post("/poison-pills/release", summary="Libera uma mensagem da quarentena")
async def release_from_quarantine(
        request: ReleaseQuarantineRequest,
        service: ObservabilityService = Depends(get_observability_service)
):
    """Delega a liberação de uma mensagem para o ObservabilityService."""
    # MessageNotFoundError é tratado pelo exception handler central -> 404
    msg = service.release_from_quarantine(request.message_id, request.allow_retry)
    return {"message": "Mensagem liberada com sucesso", "message_id": msg.message_id}

@router.post("/poison-pills/cleanup", summary="Limpa mensagens expiradas da quarentena")
async def cleanup_quarantine(service: ObservabilityService = Depends(get_observability_service)):
    return service.cleanup_expired_quarantine()

@router.get("/poison-pills/stats", summary="Retorna estatísticas de poison pills")
async def get_poison_pill_stats(
        service: ObservabilityService = Depends(get_observability_service),
        queue: Optional[str] = None
):
    """Delega a busca de estatísticas de poison pills para o ObservabilityService."""
    return service.get_poison_pill_stats(queue=queue)

@router.get("/metrics/summary", summary="Retorna um resumo de métricas chave do sistema")
async def get_metrics_summary(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a geração do resumo de métricas para o ObservabilityService."""
    return service.get_metrics_summary()
