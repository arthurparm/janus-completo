---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/tools.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tools

## Arquivos-fonte
- `backend/app/api/v1/endpoints/tools.py`

## Rotas
- `DELETE /{tool_name}`
- `GET /`
- `GET /categories/list`
- `GET /permissions/list`
- `GET /stats/usage`
- `GET /{tool_name}`
- `POST /create/from-api`
- `POST /create/from-function`

## Dependências de código
- Serviços
  - `tool_service`

## Símbolos
- class: `ToolInfo`
- class: `ToolListResponse`
- class: `ToolStatsResponse`
- class: `CreateToolFromFunctionRequest`
- class: `CreateToolFromApiRequest`
- function: `list_tools(service: ToolService = Depends(get_tool_service), category: str | None = None, permission_level: str | None = None, tags: str | None = None)`
  - Delega a listagem e filtragem de ferramentas para o ToolService.
- function: `get_tool_details(tool_name: str, service: ToolService = Depends(get_tool_service))`
  - Delega a busca de detalhes de uma ferramenta para o ToolService.
- function: `get_tool_statistics(service: ToolService = Depends(get_tool_service))`
  - Delega a busca de estatísticas para o ToolService.
- function: `create_tool_from_function(request: CreateToolFromFunctionRequest, service: ToolService = Depends(get_tool_service))`
  - Delega a criação de uma ferramenta a partir de código para o ToolService.
- function: `create_tool_from_api(request: CreateToolFromApiRequest, service: ToolService = Depends(get_tool_service))`
  - Delega a criação de uma ferramenta que chama um endpoint HTTP para o ToolService.
- function: `delete_tool(tool_name: str, service: ToolService = Depends(get_tool_service))`
  - Delega a remoção de uma ferramenta para o ToolService.
- function: `list_categories(service: ToolService = Depends(get_tool_service))`
- function: `list_permissions(service: ToolService = Depends(get_tool_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
