---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/chat_repository_sql.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_repository_sql

## Arquivos-fonte
- `backend/app/repositories/chat_repository_sql.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`
  - `user_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/pending_actions.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `ChatRepositoryError`
- class: `ChatRepositorySQL`
- method: `ChatRepositorySQL.__init__(self, session: Session | None = None)`
- method: `ChatRepositorySQL._fallback_ts(self, dt: datetime)` -> `float`
- method: `ChatRepositorySQL._message_to_dict(self, message: Message | dict[str, Any])` -> `dict[str, Any]`
- method: `ChatRepositorySQL._get_session(self)` -> `Session`
- method: `ChatRepositorySQL._resolve_user_id(self, user_id: str)` -> `int | None`
  - Resolve different user ID formats to database user ID.
Supports:
- Numeric strings: "123" -> 123
- Current user placeholder: "current-user" -> None (for now)
- User email or external ID: maps to internal user ID
- method: `ChatRepositorySQL.start_conversation(self, persona: str | None, user_id: str | None, project_id: str | None, title: str | None = None)` -> `str`
- method: `ChatRepositorySQL.add_message(self, conversation_id: str, role: str, text: str, metadata: dict[str, Any] | None = None)` -> `dict[str, Any]`
- method: `ChatRepositorySQL.get_conversation(self, conversation_id: str)` -> `dict[str, Any]`
- method: `ChatRepositorySQL.get_history(self, conversation_id: str)` -> `list[dict[str, Any]]`
- method: `ChatRepositorySQL.get_history_paginated(self, conversation_id: str, limit: int = 50, offset: int = 0, before_ts: float | None = None, after_ts: float | None = None)` -> `dict[str, Any]`
  - Retorna histórico paginado de mensagens com metadados.
- method: `ChatRepositorySQL.get_recent_messages(self, conversation_id: str, limit: int = 20)` -> `list[dict[str, Any]]`
- method: `ChatRepositorySQL.list_conversations(self, user_id: str | None = None, project_id: str | None = None, limit: int = 50)` -> `list[dict[str, Any]]`
- method: `ChatRepositorySQL.rename_conversation(self, conversation_id: str, new_title: str, user_id: str | None = None, project_id: str | None = None)` -> `None`
- method: `ChatRepositorySQL.delete_conversation(self, conversation_id: str, user_id: str | None = None, project_id: str | None = None)` -> `None`
- method: `ChatRepositorySQL.update_message_text(self, conversation_id: str, message_id: int, new_text: str, user_id: str | None = None)` -> `None`
- method: `ChatRepositorySQL.replace_last_assistant_message(self, conversation_id: str, new_text: str, user_id: str | None = None)` -> `None`
- method: `ChatRepositorySQL.get_last_assistant_message(self, conversation_id: str, user_id: str | None = None)` -> `dict[str, Any]`
- method: `ChatRepositorySQL.update_message_payload(self, conversation_id: str, message_id: int, patch: dict[str, Any], user_id: str | None = None)` -> `dict[str, Any]`
- method: `ChatRepositorySQL.delete_message(self, conversation_id: str, message_id: int, user_id: str | None = None)` -> `None`
- method: `ChatRepositorySQL.update_summary(self, conversation_id: str, summary: str | None)` -> `None`
- method: `ChatRepositorySQL.count_messages(self, conversation_id: str)` -> `int`
  - Conta o número total de mensagens em uma conversa.
- method: `ChatRepositorySQL.count_conversations(self)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
