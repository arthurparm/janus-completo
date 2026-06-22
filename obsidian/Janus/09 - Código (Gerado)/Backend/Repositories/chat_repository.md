---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/chat_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_repository

## Arquivos-fonte
- `backend/app/repositories/chat_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/services/chat/conversation_service.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- class: `ChatRepositoryError`
  - Base exception for Chat repository errors.
- class: `ChatRepository`
  - Repository with durable file persistence for chat conversations and messages.
Structure:
{
    conversation_id: {
        "persona": Optional[str],
        "project_id": Optional[str],
        "title": str,
        "created_at": float,
        "updated_at": float,
        "summary": Optional[str],
        "messages": [
            {"timestamp": float, "role": str, "text": str}
        ]
    }
}
- method: `ChatRepository.__init__(self, store_path: str = 'data/chat_store.json')`
- method: `ChatRepository._ensure_store_dir(self)` -> `None`
- method: `ChatRepository._load(self)` -> `None`
- method: `ChatRepository._save(self)` -> `None`
- method: `ChatRepository._normalize_message(self, msg: dict[str, Any])` -> `dict[str, Any]`
- method: `ChatRepository.start_conversation(self, persona: str | None, project_id: str | None, title: str | None = None)` -> `str`
- method: `ChatRepository.add_message(self, conversation_id: str, role: str, text: str, metadata: dict[str, Any] | None = None)` -> `dict[str, Any]`
- method: `ChatRepository.get_conversation(self, conversation_id: str)` -> `dict[str, Any]`
- method: `ChatRepository.get_history(self, conversation_id: str)` -> `list[dict[str, Any]]`
- method: `ChatRepository.get_recent_messages(self, conversation_id: str, limit: int = 20)` -> `list[dict[str, Any]]`
- method: `ChatRepository.list_conversations(self, project_id: str | None = None, limit: int = 50)` -> `list[dict[str, Any]]`
- method: `ChatRepository.rename_conversation(self, conversation_id: str, new_title: str, project_id: str | None = None)` -> `None`
- method: `ChatRepository.delete_conversation(self, conversation_id: str, project_id: str | None = None)` -> `None`
- method: `ChatRepository.update_summary(self, conversation_id: str, summary: str | None)` -> `None`
- method: `ChatRepository.replace_last_assistant_message(self, conversation_id: str, new_text: str)` -> `None`
- method: `ChatRepository.get_last_assistant_message(self, conversation_id: str)` -> `dict[str, Any]`
- method: `ChatRepository.update_message_payload(self, conversation_id: str, message_id: int, patch: dict[str, Any])` -> `dict[str, Any]`
- method: `ChatRepository.count_conversations(self)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
