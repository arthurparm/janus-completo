import structlog
from typing import List, Dict, Any, Optional
from fastapi import Depends

from app.repositories.tool_repository import ToolRepository, get_tool_repository
from app.core.tools import (
    DynamicToolGenerator,
    ToolCategory,
    PermissionLevel,
    ToolMetadata
)

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---

class ToolServiceError(Exception):
    """Base exception for tool service errors."""
    pass

class ToolNotFoundError(ToolServiceError):
    """Raised when a tool is not found."""
    pass

class ToolCreationError(ToolServiceError):
    """Raised on failure to create a dynamic tool."""
    pass

class ProtectedToolError(ToolServiceError):
    """Raised when attempting to modify a protected built-in tool."""
    pass

# --- Tool Service ---

class ToolService:
    """
    Camada de serviço para gerenciamento de ferramentas.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    PROTECTED_TOOLS = {
        "write_file", "read_file", "list_directory",
        "recall_experiences", "analyze_memory_for_failures",
        "get_current_datetime", "get_system_info",
        "search_web", "get_enriched_context",
        "execute_python_code", "execute_python_expression"
    }

    def __init__(self, repo: ToolRepository):
        self._repo = repo

    def list_tools(self, category: Optional[ToolCategory], permission_level: Optional[PermissionLevel],
                   tags: Optional[List[str]]) -> List[ToolMetadata]:
        logger.info("Listando ferramentas via serviço.")
        return self._repo.find_all(category, permission_level, tags)

    def get_tool_details(self, tool_name: str) -> ToolMetadata:
        logger.info("Buscando detalhes da ferramenta via serviço", tool_name=tool_name)
        metadata = self._repo.find_by_name(tool_name)
        if not metadata:
            raise ToolNotFoundError(f"Ferramenta '{tool_name}' não encontrada.")
        return metadata

    def get_statistics(self) -> Dict[str, Any]:
        logger.info("Buscando estatísticas de ferramentas via serviço.")
        return self._repo.get_all_statistics()

    def create_tool_from_function(self, request_data: Dict[str, Any]) -> ToolMetadata:
        logger.info("Orquestrando criação de ferramenta a partir de código Python", tool_name=request_data['name'])
        try:
            tool = DynamicToolGenerator.from_python_code(
                name=request_data['name'],
                description=request_data['description'],
                code=request_data['code'],
                function_name=request_data['function_name']
            )
            metadata_to_save = {
                "category": ToolCategory(request_data.get('category', 'custom')),
                "permission_level": PermissionLevel(request_data.get('permission_level', 'safe')),
                "rate_limit_per_minute": request_data.get('rate_limit_per_minute'),
                "tags": request_data.get('tags', [])
            }
            self._repo.save(tool, metadata_to_save)
            return self.get_tool_details(request_data['name'])
        except Exception as e:
            logger.error("Erro no serviço ao criar ferramenta a partir de função", exc_info=e)
            raise ToolCreationError(f"Falha ao criar ferramenta: {e}") from e

    def delete_tool(self, tool_name: str):
        logger.info("Orquestrando remoção de ferramenta", tool_name=tool_name)
        if tool_name in self.PROTECTED_TOOLS:
            raise ProtectedToolError(f"A ferramenta '{tool_name}' é protegida e não pode ser removida.")
        self.get_tool_details(tool_name)  # Verifica se a ferramenta existe
        self._repo.delete(tool_name)
        logger.info("Ferramenta removida com sucesso via serviço", tool_name=tool_name)

    def list_categories(self) -> List[str]:
        return self._repo.get_all_categories()

    def list_permissions(self) -> List[str]:
        return self._repo.get_all_permissions()


# Padrão de Injeção de Dependência: Getter para o serviço
def get_tool_service(repo: ToolRepository = Depends(get_tool_repository)) -> ToolService:
    return ToolService(repo)
