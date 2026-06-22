---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/chat_contracts.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_contracts

## Arquivos-fonte
- `backend/app/services/chat/chat_contracts.py`

## Dependências de código
- Repositórios
  - `pending_action_repository`

## Símbolos
- function: `chat_http_error_detail(*, code: str, message: str, category: str, retryable: bool, http_status: int, details: dict[str, Any] | None = None)` -> `dict[str, Any]`
- function: `chat_sse_error_payload(*, code: str, message: str, category: str, retryable: bool, http_status: int | None = None, details: dict[str, Any] | None = None)` -> `dict[str, Any]`
- function: `extract_pending_action_id_from_text(text: str | None)` -> `int | None`
- function: `_normalize_confirmation_reason(reason: Any)` -> `str | None`
- function: `maybe_create_fallback_pending_action(*, message: str, assistant_response: str | None = None, conversation_id: str | None = None, existing_pending_action_id: int | None = None, understanding: dict[str, Any] | None = None)` -> `tuple[int | None, str | None]`
- function: `summarize_risk_from_message_and_confirmation(*, understanding: dict[str, Any] | None, confirmation: dict[str, Any] | None)` -> `dict[str, Any] | None`
- function: `build_confirmation_payload(*, pending_action_id: int | None, reason: str | None)` -> `dict[str, Any] | None`
- function: `normalize_understanding_payload(understanding: dict[str, Any] | None, *, confirmation: dict[str, Any] | None = None)` -> `dict[str, Any] | None`
- function: `build_agent_state(*, stream_phase: str | None = None, understanding: dict[str, Any] | None = None, confirmation: dict[str, Any] | None = None)` -> `dict[str, Any] | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
