---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/context_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# context_repository

## Arquivos-fonte
- `backend/app/repositories/context_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/context_service.py`

## Símbolos
- class: `ContextRepositoryError`
  - Base exception for context repository errors.
- class: `ContextRepository`
  - Camada de Repositório para o Context Manager.
Abstrai todas as interações diretas com a infraestrutura de contexto.
- method: `ContextRepository.get_current_context(self)` -> `ContextInfo`
  - Busca o contexto ambiental atual a partir do manager.
- method: `ContextRepository.search_web(self, query: str, max_results: int, search_depth: str)` -> `WebSearchResult`
  - Realiza uma busca na web através do manager.
- method: `ContextRepository.get_enriched_context(self, query: str | None, include_web_search: bool, max_web_results: int)` -> `dict`
  - Busca o contexto enriquecido através do manager.
- method: `ContextRepository.format_context_for_prompt(self, include_datetime: bool, include_system: bool, web_results: WebSearchResult | None)` -> `str`
  - Formata o contexto para prompt através do manager.
- method: `ContextRepository.get_web_cache_status(self)` -> `dict`
  - Obtém o status atual do cache de busca web.
- method: `ContextRepository.invalidate_web_cache(self, query: str | None)` -> `dict`
  - Invalida entradas do cache web (por query ou completo).
- function: `get_context_repository()` -> `ContextRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
