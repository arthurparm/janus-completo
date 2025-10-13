import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.observability_service import (
    observability_service,
    ObservabilityServiceError,
    MessageNotFoundError
)

router = APIRouter(prefix="/observability", tags=["Observability"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class ReleaseQuarantineRequest(BaseModel):
    message_id: str
    allow_retry: bool = False

# --- Endpoints ---

@router.get("/health/system", summary="Retorna a saúde agregada do sistema")
async def get_system_health():
    """Delega a busca da saúde do sistema para o ObservabilityService."""
    try:
        return await observability_service.get_system_health()
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço de observabilidade ao buscar saúde do sistema", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/health/check-all", summary="Força a execução de todos os health checks")
async def check_all_components():
    """Delega a execução de todos os health checks para o ObservabilityService."""
    try:
        return await observability_service.check_all_components()
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço de observabilidade ao executar health checks", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/poison-pills/quarantined", summary="Retorna mensagens em quarentena")
async def get_quarantined_messages(queue: Optional[str] = None):
    """Delega a busca de mensagens em quarentena para o ObservabilityService."""
    try:
        messages = observability_service.get_quarantined_messages(queue=queue)
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
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço ao buscar mensagens em quarentena", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/poison-pills/release", summary="Libera uma mensagem da quarentena")
async def release_from_quarantine(request: ReleaseQuarantineRequest):
    """Delega a liberação de uma mensagem para o ObservabilityService."""
    try:
        msg = observability_service.release_from_quarantine(request.message_id, request.allow_retry)
        return {"message": "Mensagem liberada com sucesso", "message_id": msg.message_id}
    except MessageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço ao liberar mensagem", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/poison-pills/stats", summary="Retorna estatísticas de poison pills")
async def get_poison_pill_stats(queue: Optional[str] = None):
    """Delega a busca de estatísticas de poison pills para o ObservabilityService."""
    try:
        return observability_service.get_poison_pill_stats(queue=queue)
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço ao buscar estatísticas de poison pills", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/metrics/summary", summary="Retorna um resumo de métricas chave do sistema")
async def get_metrics_summary():
    """Delega a geração do resumo de métricas para o ObservabilityService."""
    try:
        return observability_service.get_metrics_summary()
    except ObservabilityServiceError as e:
        logger.error("Erro no serviço ao gerar resumo de métricas", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
