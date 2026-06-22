---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_command_handler.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_command_handler

## Objetivo
Chat Command Handler Service.
Handles quick commands like /help, /status, /memory, /tools.
Extracted from ChatService to reduce complexity.

## Arquivos-fonte
- `backend/app/services/chat_command_handler.py`

## Fluxos de uso (chamadores)
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `ChatCommandHandler`
  - Processes quick commands (starting with /) for chat service.
- method: `ChatCommandHandler.__init__(self, tool_service: Any | None = None, memory_service: Any | None = None)`
  - Initialize command handler.
- method: `ChatCommandHandler.is_command(self, text: str)` -> `bool`
  - Check if message is a quick command.
- method: `ChatCommandHandler.handle_command(self, text: str, conversation_id: str, user_id: str | None = None)` -> `str | None`
  - Process command and return response.
- method: `ChatCommandHandler._handle_help(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Show available commands.
- method: `ChatCommandHandler._handle_status(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Show system status.
- method: `ChatCommandHandler._handle_memory(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Show memory statistics.
- method: `ChatCommandHandler._handle_tools(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Show available tools.
- method: `ChatCommandHandler._handle_feedback(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Handle user feedback.
- method: `ChatCommandHandler._handle_about(self, args: str, conversation_id: str, user_id: str | None)` -> `str`
  - Show info about Janus.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
