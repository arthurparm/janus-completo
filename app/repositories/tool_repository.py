import structlog
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool
from fastapi import Depends

from app.core.tools import (
    action_registry,
    ToolCategory,
    PermissionLevel,
    ToolMetadata
)

logger = structlog.get_logger(__name__)

class ToolRepositoryError(Exception):
    """Base exception for tool repository errors."""
    pass

class ToolRepository:
    """
    Camada de Repositório para o registro de ferramentas (`action_registry`).
    Abstrai todas as interações diretas com a infraestrutura de ferramentas.
    """

    def find_all(self, category: Optional[ToolCategory], permission_level: Optional[PermissionLevel],
                 tags: Optional[List[str]]) -> List[ToolMetadata]:
        logger.debug("Buscando ferramentas no repositório", category=category, permission_level=permission_level,
                     tags=tags)
        tools = action_registry.list_tools(category=category, permission_level=permission_level, tags=tags)
        return [action_registry.get_metadata(tool.name) for tool in tools if action_registry.get_metadata(tool.name)]

    def find_by_name(self, tool_name: str) -> Optional[ToolMetadata]:
        logger.debug("Buscando ferramenta por nome no repositório", tool_name=tool_name)
        return action_registry.get_metadata(tool_name)

    def get_all_statistics(self) -> Dict[str, Any]:
        logger.debug("Buscando estatísticas de ferramentas no repositório.")
        return action_registry.get_statistics()

    def save(self, tool: BaseTool, metadata: Dict[str, Any]):
        logger.debug("Salvando ferramenta no repositório", tool_name=tool.name)
        action_registry.register(
            tool,
            category=metadata.get('category', ToolCategory.CUSTOM),
            permission_level=metadata.get('permission_level', PermissionLevel.SAFE),
            rate_limit_per_minute=metadata.get('rate_limit_per_minute'),
            tags=metadata.get('tags', [])
        )

    def delete(self, tool_name: str):
        logger.debug("Removendo ferramenta do repositório", tool_name=tool_name)
        action_registry.unregister(tool_name)

    def get_all_categories(self) -> List[str]:
        return [cat.value for cat in ToolCategory]

    def get_all_permissions(self) -> List[str]:
        return [perm.value for perm in PermissionLevel]


# Padrão de Injeção de Dependência: Getter para o repositório
def get_tool_repository() -> ToolRepository:
    # O action_registry é um singleton global, então o repositório não precisa de estado.
    return ToolRepository()
