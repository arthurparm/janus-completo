from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional
import structlog

from app.services.system_status_service import system_status_service

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Model (DTO) ---

class StatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str
    timestamp: Optional[str] = None
    uptime_seconds: Optional[float] = None
    system: Optional[Dict[str, Any]] = None
    process: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


# --- Endpoint ---

@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Verifica o estado da aplicação",
    tags=["System"]
)
async def get_system_status():
    """Delega a obtenção do status da aplicação para o SystemStatusService."""
    logger.info("Recebida requisição de status do sistema.")
    status_data = system_status_service.get_system_status()
    return StatusResponse(**status_data)
