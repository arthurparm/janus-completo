---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_service

## Arquivos-fonte
- `backend/app/services/chat_service.py`

## Dependências de código
- Repositórios
  - `chat_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/chat/chat_admin.py`
- `backend/app/api/v1/endpoints/chat/chat_history.py`
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/chat/chat_stream.py`
- `backend/app/api/v1/endpoints/chat/chat_study_jobs.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `ChatService`
  - Stable facade for chat operations.
- method: `ChatService.__init__(self, repo: ChatRepository, llm_service: LLMService, tool_service: ToolService | None = None, memory_service: MemoryService | None = None, prompt_service: PromptBuilderService | None = None, tool_executor_service: ToolExecutorService | None = None, rag_service: RAGService | None = None, event_logger: Any | None = None, outbox_service: OutboxService | None = None)`
- method: `ChatService._estimate_tokens(self, text: str)` -> `int`
- method: `ChatService._split_ui(self, text: str)` -> `tuple[str, dict[str, Any] | None]`
- method: `ChatService._build_understanding_payload(self, message: str)` -> `dict[str, Any] | None`
- method: `ChatService._attach_understanding(self, payload: dict[str, Any], understanding: dict[str, Any] | None)` -> `dict[str, Any]`
- method: `ChatService._is_explicit_tool_creation(self, message: str)` -> `bool`
- method: `ChatService._format_tool_creation_response(self, result: dict[str, Any])` -> `str`
- method: `ChatService._validate_conversation_access(self, conversation_id: str, conv: dict[str, Any], project_id: str | None)` -> `None`
- method: `ChatService._trigger_post_response_events(self, conversation_id: str, user_message: str, assistant_text: str, result: dict[str, Any], project_id: str | None)` -> `None`
- method: `ChatService.start_conversation(self, persona: str | None, project_id: str | None)` -> `str`
- method: `ChatService.start_conversation_async(self, persona: str | None, project_id: str | None)` -> `str`
- method: `ChatService.send_message(self, conversation_id: str, message: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None = None, project_id: str | None = None, knowledge_space_id: str | None = None, identity_source: str = 'unknown')` -> `dict[str, Any]`
- method: `ChatService.resolve_active_knowledge_space_id(self, *, conversation_id: str, requested_knowledge_space_id: str | None = None)` -> `str | None`
- method: `ChatService.get_history(self, conversation_id: str, project_id: str | None = None)` -> `dict[str, Any]`
- method: `ChatService.get_history_paginated(self, conversation_id: str, limit: int = 50, offset: int = 0, before_ts: float | None = None, after_ts: float | None = None, project_id: str | None = None)` -> `dict[str, Any]`
- method: `ChatService.list_conversations(self, project_id: str | None = None, limit: int = 50)` -> `list[dict[str, Any]]`
- method: `ChatService.rename_conversation(self, conversation_id: str, new_title: str, project_id: str | None = None)` -> `None`
- method: `ChatService.delete_conversation(self, conversation_id: str, project_id: str | None = None)` -> `None`
- method: `ChatService.update_message(self, conversation_id: str, message_id: int, new_text: str)` -> `None`
- method: `ChatService.delete_message(self, conversation_id: str, message_id: int)` -> `None`
- method: `ChatService.replace_last_assistant_message(self, conversation_id: str, new_text: str)` -> `None`
- method: `ChatService.get_last_assistant_message(self, conversation_id: str)` -> `dict[str, Any]`
- method: `ChatService.update_message_payload(self, conversation_id: str, message_id: int, patch: dict[str, Any])` -> `dict[str, Any]`
- method: `ChatService.stream_message(self, conversation_id: str, message: str, role: ModelRole | None = None, priority: ModelPriority | None = None, timeout_seconds: int | None = None, project_id: str | None = None, knowledge_space_id: str | None = None, identity_source: str = 'unknown', requested_role: str | None = None, routing_decision: Any | None = None, route_applied: bool | None = None)`
- method: `ChatService.stream_events(self, conversation_id: str)`
- function: `get_chat_service(request: Request)` -> `ChatService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
