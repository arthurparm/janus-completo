---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/tool_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tool_service

## Arquivos-fonte
- `backend/app/services/tool_service.py`

## Dependências de código
- Repositórios
  - `tool_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/tools.py`
- `backend/app/core/evolution/evolution_manager.py`
- `backend/app/core/evolution/safe_evolution_manager.py`
- `backend/app/core/kernel.py`
- `backend/app/core/tools/agent_tools.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `ToolServiceError`
  - Base exception for tool service errors.
- class: `ToolNotFoundError`
  - Raised when a tool is not found.
- class: `ToolCreationError`
  - Raised on failure to create a dynamic tool.
- class: `ProtectedToolError`
  - Raised when attempting to modify a protected built-in tool.
- class: `ToolService`
  - Service layer for managing tools.
Orchestrate business logic, receiving its dependencies via DI.
- method: `ToolService.__init__(self, repo: ToolRepository)`
- method: `ToolService.list_tools(self, category: ToolCategory | None, permission_level: PermissionLevel | None, tags: list[str] | None)` -> `list[ToolMetadata]`
- method: `ToolService.get_tool_details(self, tool_name: str)` -> `ToolMetadata`
- method: `ToolService.get_statistics(self)` -> `dict[str, Any]`
- method: `ToolService.generate_documentation(self, include_stats: bool = True, format: str = 'markdown')` -> `str`
  - Generates descriptive documentation of the registered local tools.
- method: `ToolService.create_tool_from_function(self, request_data: dict[str, Any])` -> `ToolMetadata`
- method: `ToolService.create_tool_from_api(self, request_data: dict[str, Any])` -> `ToolMetadata`
- method: `ToolService.delete_tool(self, tool_name: str)`
- method: `ToolService.list_categories(self)` -> `list[str]`
- method: `ToolService.list_permissions(self)` -> `list[str]`
- function: `get_tool_service(request: Request)` -> `ToolService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
