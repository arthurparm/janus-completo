---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/conversation_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# conversation_service

## Arquivos-fonte
- `backend/app/services/chat/conversation_service.py`

## Dependências de código
- Repositórios
  - `chat_repository`
  - `pending_action_repository`

## Símbolos
- class: `ConversationService`
- method: `ConversationService.__init__(self, repo: ChatRepository)`
- method: `ConversationService._get_resolved_pending_statuses(self, messages: list[dict[str, Any]])` -> `dict[int, str]`
- method: `ConversationService._reconcile_pending_confirmation_message(self, message: dict[str, Any], *, status_by_action_id: dict[int, str])` -> `dict[str, Any]`
- method: `ConversationService._reconcile_pending_confirmation_messages(self, messages: list[dict[str, Any]])` -> `list[dict[str, Any]]`
- method: `ConversationService.validate_conversation_access(self, conversation_id: str, conv: dict[str, Any], project_id: str | None)` -> `None`
- method: `ConversationService.start_conversation(self, persona: str | None, project_id: str | None)` -> `str`
- method: `ConversationService.start_conversation_async(self, persona: str | None, project_id: str | None)` -> `str`
- method: `ConversationService.get_history(self, conversation_id: str, project_id: str | None = None)` -> `dict[str, Any]`
- method: `ConversationService.get_history_paginated(self, conversation_id: str, limit: int = 50, offset: int = 0, before_ts: float | None = None, after_ts: float | None = None, project_id: str | None = None)` -> `dict[str, Any]`
- method: `ConversationService.list_conversations(self, project_id: str | None = None, limit: int = 50)` -> `list[dict[str, Any]]`
- method: `ConversationService.rename_conversation(self, conversation_id: str, new_title: str, project_id: str | None = None)` -> `None`
- method: `ConversationService.delete_conversation(self, conversation_id: str, project_id: str | None = None)` -> `None`
- method: `ConversationService.update_message(self, conversation_id: str, message_id: int, new_text: str)` -> `None`
- method: `ConversationService.delete_message(self, conversation_id: str, message_id: int)` -> `None`
- method: `ConversationService.replace_last_assistant_message(self, conversation_id: str, new_text: str)` -> `None`
- method: `ConversationService.get_last_assistant_message(self, conversation_id: str)` -> `dict[str, Any]`
- method: `ConversationService.update_message_payload(self, conversation_id: str, message_id: int, patch: dict[str, Any])` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
