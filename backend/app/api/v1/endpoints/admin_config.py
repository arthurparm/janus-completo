
import structlog
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

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
    request: ConfigUpdateRequest,
    service: ConfigService = Depends(get_config_service)
):
    """
    Recebe atualizações de configuração e as propaga via Redis Pub/Sub 
    para todas as instâncias do serviço.
    
    Atenção: As mudanças são aplicadas em memória e perdidas no restart 
    se não forem persistidas externamente (env vars ou secrets).
    """
    await service.update_config(request.updates)

    return ConfigUpdateResponse(
        message="Configuração atualizada e propagada com sucesso.",
        updated_keys=list(request.updates.keys())
    )
