import structlog
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.tool_service import (
    tool_service,
    ToolServiceError,
    ToolNotFoundError,
    ToolCreationError,
    ProtectedToolError
)
from app.core.tools import ToolCategory, PermissionLevel

router = APIRouter(prefix="/tools", tags=["Tools"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    permission_level: str
    rate_limit_per_minute: Optional[int]
    requires_confirmation: bool
    tags: List[str]

class ToolListResponse(BaseModel):
    total: int
    tools: List[ToolInfo]

class ToolStatsResponse(BaseModel):
    total_tools_registered: int
    total_calls: int
    successful_calls: int
    success_rate: float
    tool_usage: Dict[str, Dict[str, Any]]

class CreateToolFromFunctionRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    function_name: str = Field(default="execute")
    category: str = Field(default="custom")
    permission_level: str = Field(default="safe")
    rate_limit_per_minute: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


# --- Endpoints ---

@router.get("/", response_model=ToolListResponse, summary="Lista todas as ferramentas disponíveis")
async def list_tools(
        category: Optional[str] = None,
        permission_level: Optional[str] = None,
        tags: Optional[str] = None
):
    """Delega a listagem e filtragem de ferramentas para o ToolService."""
    try:
        cat_filter = ToolCategory(category.lower()) if category else None
        perm_filter = PermissionLevel(permission_level.lower()) if permission_level else None
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        tools_metadata = tool_service.list_tools(cat_filter, perm_filter, tag_list)

        tool_infos = [ToolInfo(
            name=meta.name,
            description=meta.description,
            category=meta.category.value,
            permission_level=meta.permission_level.value,
            rate_limit_per_minute=meta.rate_limit_per_minute,
            requires_confirmation=meta.requires_confirmation,
            tags=meta.tags
        ) for meta in tools_metadata]

        return ToolListResponse(total=len(tool_infos), tools=tool_infos)
    except ValueError as e:  # Erro de conversão de enum
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Filtro inválido: {e}")
    except ToolServiceError as e:
        logger.error("Erro no serviço de ferramentas ao listar", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tool_name}", response_model=ToolInfo, summary="Obtém detalhes de uma ferramenta")
async def get_tool_details(tool_name: str):
    """Delega a busca de detalhes de uma ferramenta para o ToolService."""
    try:
        metadata = tool_service.get_tool_details(tool_name)
        return ToolInfo(**metadata.dict())
    except ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats/usage", response_model=ToolStatsResponse, summary="Estatísticas de uso de ferramentas")
async def get_tool_statistics():
    """Delega a busca de estatísticas para o ToolService."""
    try:
        return tool_service.get_statistics()
    except ToolServiceError as e:
        logger.error("Erro no serviço de ferramentas ao buscar estatísticas", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/create/from-function", response_model=ToolInfo, status_code=status.HTTP_201_CREATED,
             summary="Cria ferramenta a partir de código Python")
async def create_tool_from_function(request: CreateToolFromFunctionRequest):
    """Delega a criação de uma ferramenta a partir de código para o ToolService."""
    try:
        new_tool_metadata = tool_service.create_tool_from_function(request.dict())
        return ToolInfo(**new_tool_metadata.dict())
    except ToolCreationError as e:
        logger.error("Erro de criação de ferramenta no serviço", exc_info=e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Erro inesperado ao criar ferramenta", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Erro interno ao criar ferramenta.")


@router.delete("/{tool_name}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove uma ferramenta dinâmica")
async def delete_tool(tool_name: str):
    """Delega a remoção de uma ferramenta para o ToolService."""
    try:
        tool_service.delete_tool(tool_name)
    except ProtectedToolError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ToolServiceError as e:
        logger.error("Erro no serviço de ferramentas ao remover", tool_name=tool_name, exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/categories/list", summary="Lista todas as categorias de ferramentas")
async def list_categories():
    return {"categories": tool_service.list_categories()}


@router.get("/permissions/list", summary="Lista todos os níveis de permissão")
async def list_permissions():
    return {"permission_levels": tool_service.list_permissions()}
