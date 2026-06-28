
import structlog
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.core.security.request_guard import require_admin_actor
from app.services.config_service import ConfigService, get_config_service

router = APIRouter(tags=["Admin"])
logger = structlog.get_logger(__name__)


class ConfigUpdateRequest(BaseModel):
    """Modelo flexível para atualização de configuração."""
    # Usamos dict genérico para permitir atualizar qualquer campo suportado pelo AppSettings
    updates: dict[str, str | int | float | bool | list | dict] = Field(
        ..., description="Dicionário com chaves e novos valores para configuração"
    )


class ConfigUpdateResponse(BaseModel):
    message: str
    updated_keys: list[str]


@router.patch(
    "/admin/config",
    response_model=ConfigUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualiza configurações do sistema em tempo de execução (Hot-Reload)"
)
async def update_config(
    config_request: ConfigUpdateRequest,
    request: Request,
    service: ConfigService = Depends(get_config_service)
):
    require_admin_actor(request)
    await service.update_config(config_request.updates)
    
    return ConfigUpdateResponse(
        message="Configuração atualizada e propagada com sucesso.",
        updated_keys=list(config_request.updates.keys())
    )
