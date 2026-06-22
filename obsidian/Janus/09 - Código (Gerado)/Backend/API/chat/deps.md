---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/deps.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/deps

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/deps.py`

## Símbolos
- function: `actor_user_id(http: Request | None)` -> `str | None`
- function: `actor_project_id(http: Request | None)` -> `str | None`
- function: `anonymous_user_id(http: Request | None)` -> `str | None`
- function: `resolve_user_id(http: Request | None, explicit_user_id: str | None)` -> `str | None`
- function: `_chat_auth_enforced()` -> `bool`
- function: `is_chat_auth_enforced()` -> `bool`
- function: `_chat_transition_warn()` -> `bool`
- function: `_auth_header_present(http: Request | None)` -> `bool`
- function: `_x_user_id_header(http: Request | None)` -> `str | None`
- function: `_chat_http_error(status_code: int, detail: str, code: str)` -> `HTTPException`
- class: `ChatIdentityResolution`
- function: `resolve_authenticated_user_context(http: Request | None, explicit_user_id: str | None, *, allow_anonymous_fallback: bool = False, endpoint_label: str = '/api/v1/chat')` -> `ChatIdentityResolution`
  - Resolve chat identity with support for transition mode and enforcement mode.
- function: `require_actor_user_id(http: Request | None)` -> `str`
  - Strict helper: always require authenticated actor when enforcement is enabled.
- function: `resolve_authenticated_user_id(http: Request | None, explicit_user_id: str | None)` -> `str`
  - Resolve user id for chat endpoints, enforcing auth when configured.
- function: `_channel_limit(channel: SSEChannel)` -> `int`
- function: `acquire_sse_slot(*, channel: SSEChannel, user_id: str)` -> `str`
- function: `release_sse_slot(slot_user: str, *, channel: SSEChannel)` -> `None`
- function: `ensure_origin_allowed(http: Request | None)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
