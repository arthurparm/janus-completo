---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/tool_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tool_repository

## Arquivos-fonte
- `backend/app/repositories/tool_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/evolution/safe_evolution_manager.py`
- `backend/app/core/kernel.py`
- `backend/app/core/tools/agent_tools.py`
- `backend/app/services/tool_service.py`

## Símbolos
- class: `ToolRepositoryError`
  - Base exception for tool repository errors.
- class: `ToolRepository`
  - Camada de Repositório para o registro de ferramentas (`action_registry`).
Abstrai todas as interações diretas com a infraestrutura de ferramentas.
- method: `ToolRepository.find_all(self, category: ToolCategory | None, permission_level: PermissionLevel | None, tags: list[str] | None)` -> `list[ToolMetadata]`
- method: `ToolRepository.find_by_name(self, tool_name: str)` -> `ToolMetadata | None`
- method: `ToolRepository.get_all_statistics(self)` -> `dict[str, Any]`
- method: `ToolRepository.save(self, tool: BaseTool, metadata: dict[str, Any])`
- method: `ToolRepository.delete(self, tool_name: str)`
- method: `ToolRepository.get_all_categories(self)` -> `list[str]`
- method: `ToolRepository.get_all_permissions(self)` -> `list[str]`
- function: `get_tool_repository()` -> `ToolRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
