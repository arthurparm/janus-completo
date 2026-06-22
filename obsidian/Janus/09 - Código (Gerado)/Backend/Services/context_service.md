---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/context_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# context_service

## Arquivos-fonte
- `backend/app/services/context_service.py`

## Dependências de código
- Repositórios
  - `context_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/context.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `ContextServiceError`
  - Base exception for context service errors.
- class: `ContextService`
  - Camada de serviço para operações de contexto ambiental.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `ContextService.__init__(self, repo: ContextRepository)`
- method: `ContextService.get_current_context(self)` -> `ContextInfo`
  - Delega a busca do contexto ambiental atual para o repositório.
- method: `ContextService.perform_web_search(self, query: str, max_results: int, search_depth: str)` -> `WebSearchResult`
  - Delega a busca na web para o repositório.
- method: `ContextService.get_enriched_context(self, query: str | None, include_web_search: bool, max_web_results: int)` -> `dict[str, Any]`
  - Delega a busca por contexto enriquecido para o repositório.
- method: `ContextService.get_formatted_context_for_prompt(self, include_datetime: bool, include_system: bool, web_query: str | None)` -> `str`
  - Orquestra a formatação do contexto para ser usado em um prompt de LLM.
- method: `ContextService.get_web_cache_status(self)` -> `dict[str, Any]`
  - Retorna status atual do cache de busca web.
- method: `ContextService.invalidate_web_cache(self, query: str | None)` -> `dict[str, Any]`
  - Invalida entradas do cache web (por query ou completo).
- function: `get_context_service(request: Request)` -> `ContextService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
