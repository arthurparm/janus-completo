import structlog
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.services.tool_service import ToolService, get_tool_service
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
        service: ToolService = Depends(get_tool_service),
        category: Optional[str] = None,
        permission_level: Optional[str] = None,
        tags: Optional[str] = None
):
    """Delega a listagem e filtragem de ferramentas para o ToolService."""
    try:
        cat_filter = ToolCategory(category.lower()) if category else None
        perm_filter = PermissionLevel(permission_level.lower()) if permission_level else None
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        tools_metadata = service.list_tools(cat_filter, perm_filter, tag_list)
        
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
    except ValueError as e:  # Erro de conversão de enum é uma validação de input -> 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Filtro inválido: {e}")

@router.get("/{tool_name}", response_model=ToolInfo, summary="Obtém detalhes de uma ferramenta")
async def get_tool_details(tool_name: str, service: ToolService = Depends(get_tool_service)):
    """Delega a busca de detalhes de uma ferramenta para o ToolService."""
    # ToolNotFoundError é tratado pelo exception handler central -> 404
    metadata = service.get_tool_details(tool_name)
    return ToolInfo(**metadata.dict())

@router.get("/stats/usage", response_model=ToolStatsResponse, summary="Estatísticas de uso de ferramentas")
async def get_tool_statistics(service: ToolService = Depends(get_tool_service)):
    """Delega a busca de estatísticas para o ToolService."""
    return service.get_statistics()


@router.post("/create/from-function", response_model=ToolInfo, status_code=status.HTTP_201_CREATED,
             summary="Cria ferramenta a partir de código Python")
async def create_tool_from_function(
        request: CreateToolFromFunctionRequest,
        service: ToolService = Depends(get_tool_service)
):
    """Delega a criação de uma ferramenta a partir de código para o ToolService."""
    # ToolCreationError é tratado pelo exception handler central -> 400
    new_tool_metadata = service.create_tool_from_function(request.dict())
    return ToolInfo(**new_tool_metadata.dict())

@router.delete("/{tool_name}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove uma ferramenta dinâmica")
async def delete_tool(tool_name: str, service: ToolService = Depends(get_tool_service)):
    """Delega a remoção de uma ferramenta para o ToolService."""
    # ProtectedToolError -> 400 e ToolNotFoundError -> 404 são tratados centralmente
    service.delete_tool(tool_name)

@router.get("/categories/list", summary="Lista todas as categorias de ferramentas")
async def list_categories(service: ToolService = Depends(get_tool_service)):
    return {"categories": service.list_categories()}

@router.get("/permissions/list", summary="Lista todos os níveis de permissão")
async def list_permissions(service: ToolService = Depends(get_tool_service)):
    return {"permission_levels": service.list_permissions()}
