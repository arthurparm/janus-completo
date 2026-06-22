---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/context.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# context

## Arquivos-fonte
- `backend/app/api/v1/endpoints/context.py`

## Rotas
- `GET /current`
- `GET /format-prompt`
- `GET /web-cache/status`
- `GET /web-search`
- `POST /enriched`
- `POST /web-cache/invalidate`

## Dependências de código
- Serviços
  - `context_service`

## Símbolos
- class: `EnrichedContextRequest`
- class: `InvalidateCacheRequest`
- function: `get_current_context(service: ContextService = Depends(get_context_service))`
  - Delega a busca do contexto ambiental atual para o ContextService.
- function: `search_web(query: str = Query(..., description='Query de busca'), max_results: int = Query(5, ge=1, le=10, description='Número máximo de resultados'), search_depth: str = Query('basic', pattern='^(basic|advanced)$', description='Profundidade da busca'), service: ContextService = Depends(get_context_service))`
  - Delega a busca na web para o ContextService.
- function: `get_enriched_context(request: EnrichedContextRequest, service: ContextService = Depends(get_context_service))`
  - Delega a busca por contexto enriquecido para o ContextService.
- function: `format_context_for_prompt(include_datetime: bool = Query(True, description='Incluir data/hora'), include_system: bool = Query(False, description='Incluir informações do sistema'), web_query: str | None = Query(None, description='Query opcional para busca web'), service: ContextService = Depends(get_context_service))`
  - Delega a formatação de contexto para o ContextService.
- function: `get_web_cache_status(service: ContextService = Depends(get_context_service))`
  - Retorna informações sobre o cache da busca web (Tavily).
- function: `invalidate_web_cache(request: InvalidateCacheRequest, service: ContextService = Depends(get_context_service))`
  - Invalida o cache de busca web por query (prefixo) ou completamente se não informado.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
