---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/message_helpers.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# message_helpers

## Arquivos-fonte
- `backend/app/services/chat/message_helpers.py`

## Símbolos
- function: `estimate_tokens(prompt_service: Any, text: str)` -> `int`
- function: `split_ui(text: str)` -> `tuple[str, dict[str, Any] | None]`
- function: `_build_question_summary(normalized: str)` -> `str`
- function: `build_understanding_payload(message: str)` -> `dict[str, Any] | None`
- function: `attach_understanding(payload: dict[str, Any], understanding: dict[str, Any] | None)` -> `dict[str, Any]`
- function: `is_explicit_tool_creation(message: str)` -> `bool`
- function: `format_tool_creation_response(result: dict[str, Any])` -> `str`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
