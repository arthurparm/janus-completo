"""
Sprint 6: Endpoint de Gerenciamento de Ferramentas

API REST para gerenciar, listar e criar ferramentas dinamicamente.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.problem_details import ProblemDetails
from app.core.tools import (
    action_registry,
    DynamicToolGenerator,
    ToolCategory,
    PermissionLevel
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


# ==================== SCHEMAS ====================

class ToolInfo(BaseModel):
    """Informações sobre uma ferramenta."""
    name: str
    description: str
    category: str
    permission_level: str
    rate_limit_per_minute: Optional[int]
    requires_confirmation: bool
    tags: List[str]


class ToolListResponse(BaseModel):
    """Resposta da listagem de ferramentas."""
    total: int
    tools: List[ToolInfo]


class ToolStatsResponse(BaseModel):
    """Estatísticas de uso de ferramentas."""
    total_tools_registered: int
    total_calls: int
    successful_calls: int
    success_rate: float
    tool_usage: Dict[str, Dict[str, Any]]


class CreateToolFromFunctionRequest(BaseModel):
    """Request para criar ferramenta a partir de função."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=10, max_length=500)
    code: str = Field(..., description="Código Python da função", min_length=1)
    function_name: str = Field(default="execute", description="Nome da função a ser chamada")
    category: str = Field(default="custom")
    permission_level: str = Field(default="safe")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    tags: List[str] = Field(default_factory=list)


class CreateToolFromAPIRequest(BaseModel):
    """Request para criar ferramenta que chama API."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=10, max_length=500)
    endpoint_url: str = Field(..., description="URL do endpoint HTTP")
    method: str = Field(default="GET", description="Método HTTP (GET, POST)")
    headers: Optional[Dict[str, str]] = None
    category: str = Field(default="api")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=100)


# ==================== ENDPOINTS ====================

@router.get(
    "/",
    response_model=ToolListResponse,
    summary="Lista todas as ferramentas",
    description="Retorna lista completa de ferramentas disponíveis com metadados"
)
async def list_tools(
        category: Optional[str] = None,
        permission_level: Optional[str] = None,
        tags: Optional[str] = None
):
    """
    Lista ferramentas com filtros opcionais.

    Query params:
    - category: Filtrar por categoria (filesystem, api, database, etc)
    - permission_level: Filtrar por nível de permissão (read_only, safe, write, dangerous)
    - tags: Filtrar por tags (separadas por vírgula)
    """
    try:
        # Parse filtros
        cat_filter = None
        if category:
            try:
                cat_filter = ToolCategory(category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Categoria inválida: {category}"
                )

        perm_filter = None
        if permission_level:
            try:
                perm_filter = PermissionLevel(permission_level)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nível de permissão inválido: {permission_level}"
                )

        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]

        # Lista ferramentas
        tools = action_registry.list_tools(
            category=cat_filter,
            permission_level=perm_filter,
            tags=tag_list
        )

        # Converte para resposta
        tool_infos = []
        for tool in tools:
            metadata = action_registry.get_metadata(tool.name)
            if metadata:
                tool_infos.append(ToolInfo(
                    name=metadata.name,
                    description=metadata.description,
                    category=metadata.category.value,
                    permission_level=metadata.permission_level.value,
                    rate_limit_per_minute=metadata.rate_limit_per_minute,
                    requires_confirmation=metadata.requires_confirmation,
                    tags=metadata.tags
                ))

        return ToolListResponse(
            total=len(tool_infos),
            tools=tool_infos
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Tools API] Erro ao listar ferramentas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{tool_name}",
    response_model=ToolInfo,
    summary="Obtém detalhes de uma ferramenta",
    description="Retorna informações detalhadas sobre uma ferramenta específica"
)
async def get_tool_details(tool_name: str):
    """Obtém metadados de uma ferramenta específica."""
    metadata = action_registry.get_metadata(tool_name)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ferramenta '{tool_name}' não encontrada"
        )

    return ToolInfo(
        name=metadata.name,
        description=metadata.description,
        category=metadata.category.value,
        permission_level=metadata.permission_level.value,
        rate_limit_per_minute=metadata.rate_limit_per_minute,
        requires_confirmation=metadata.requires_confirmation,
        tags=metadata.tags
    )


@router.get(
    "/stats/usage",
    response_model=ToolStatsResponse,
    summary="Estatísticas de uso de ferramentas",
    description="Retorna métricas agregadas sobre uso e performance das ferramentas"
)
async def get_tool_statistics():
    """Retorna estatísticas de uso das ferramentas."""
    try:
        stats = action_registry.get_statistics()
        return ToolStatsResponse(**stats)

    except Exception as e:
        logger.error(f"[Tools API] Erro ao obter estatísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/create/from-function",
    response_model=ToolInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Cria ferramenta a partir de código Python",
    description=(
            "Cria dinamicamente uma ferramenta a partir de código Python fornecido. "
            "⚠️ Use com cuidado! Apenas em ambientes confiáveis."
    )
)
async def create_tool_from_function(request: CreateToolFromFunctionRequest):
    """
    Cria ferramenta dinamicamente a partir de código Python.

    ATENÇÃO: Esta funcionalidade permite execução de código arbitrário.
    Use apenas em ambientes controlados e confiáveis.

    Exemplo:
    ```json
    {
        "name": "greet_user",
        "description": "Cumprimenta um usuário pelo nome",
        "code": "def execute(name: str) -> str:\\n    return f'Olá, {name}!'",
        "function_name": "execute",
        "category": "custom"
    }
    ```
    """
    try:
        # Parse categoria e permissão
        try:
            category = ToolCategory(request.category)
        except ValueError:
            category = ToolCategory.CUSTOM

        try:
            perm_level = PermissionLevel(request.permission_level)
        except ValueError:
            perm_level = PermissionLevel.SAFE

        # Cria ferramenta
        tool = DynamicToolGenerator.from_python_code(
            name=request.name,
            description=request.description,
            code=request.code,
            function_name=request.function_name
        )

        # Registra
        action_registry.register(
            tool,
            category=category,
            permission_level=perm_level,
            rate_limit_per_minute=request.rate_limit_per_minute,
            tags=request.tags
        )

        metadata = action_registry.get_metadata(request.name)

        logger.info(f"[Tools API] Ferramenta '{request.name}' criada com sucesso")

        return ToolInfo(
            name=metadata.name,
            description=metadata.description,
            category=metadata.category.value,
            permission_level=metadata.permission_level.value,
            rate_limit_per_minute=metadata.rate_limit_per_minute,
            requires_confirmation=metadata.requires_confirmation,
            tags=metadata.tags
        )

    except Exception as e:
        logger.error(f"[Tools API] Erro ao criar ferramenta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ProblemDetails(
                type="tool_creation_error",
                title="Erro ao Criar Ferramenta",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
                instance="/api/v1/tools/create/from-function"
            ).model_dump()
        )


@router.post(
    "/create/from-api",
    response_model=ToolInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Cria ferramenta que chama API HTTP",
    description="Cria dinamicamente uma ferramenta que faz chamadas HTTP a um endpoint"
)
async def create_tool_from_api(request: CreateToolFromAPIRequest):
    """
    Cria ferramenta que chama um endpoint HTTP.

    Exemplo:
    ```json
    {
        "name": "get_weather",
        "description": "Obtém clima de uma cidade",
        "endpoint_url": "https://api.weather.com/v1/current",
        "method": "GET",
        "category": "api",
        "rate_limit_per_minute": 20
    }
    ```
    """
    try:
        # Cria ferramenta
        tool = DynamicToolGenerator.from_api_endpoint(
            name=request.name,
            description=request.description,
            endpoint_url=request.endpoint_url,
            method=request.method,
            headers=request.headers
        )

        # Registra
        action_registry.register(
            tool,
            category=ToolCategory.API,
            permission_level=PermissionLevel.SAFE,
            rate_limit_per_minute=request.rate_limit_per_minute
        )

        metadata = action_registry.get_metadata(request.name)

        logger.info(f"[Tools API] Ferramenta de API '{request.name}' criada: {request.endpoint_url}")

        return ToolInfo(
            name=metadata.name,
            description=metadata.description,
            category=metadata.category.value,
            permission_level=metadata.permission_level.value,
            rate_limit_per_minute=metadata.rate_limit_per_minute,
            requires_confirmation=metadata.requires_confirmation,
            tags=metadata.tags
        )

    except Exception as e:
        logger.error(f"[Tools API] Erro ao criar ferramenta de API: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{tool_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma ferramenta",
    description="Remove uma ferramenta do registro. Ferramentas built-in não podem ser removidas."
)
async def delete_tool(tool_name: str):
    """Remove uma ferramenta dinamicamente criada."""
    # Lista de ferramentas built-in que não podem ser removidas
    PROTECTED_TOOLS = {
        "write_file", "read_file", "list_directory",
        "recall_experiences", "analyze_memory_for_failures",
        "get_current_datetime", "get_system_info",
        "search_web", "get_enriched_context",
        "execute_python_code", "execute_python_expression"
    }

    if tool_name in PROTECTED_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ferramenta '{tool_name}' é built-in e não pode ser removida"
        )

    metadata = action_registry.get_metadata(tool_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ferramenta '{tool_name}' não encontrada"
        )

    action_registry.unregister(tool_name)
    logger.info(f"[Tools API] Ferramenta '{tool_name}' removida")


@router.get(
    "/categories/list",
    summary="Lista categorias disponíveis",
    description="Retorna todas as categorias de ferramentas"
)
async def list_categories():
    """Lista todas as categorias de ferramentas."""
    return {
        "categories": [cat.value for cat in ToolCategory]
    }


@router.get(
    "/permissions/list",
    summary="Lista níveis de permissão",
    description="Retorna todos os níveis de permissão disponíveis"
)
async def list_permissions():
    """Lista todos os níveis de permissão."""
    return {
        "permission_levels": [perm.value for perm in PermissionLevel]
    }
