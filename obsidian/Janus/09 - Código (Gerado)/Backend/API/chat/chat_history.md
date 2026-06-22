---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/chat_history.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/chat_history

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/chat_history.py`

## Rotas
- `GET /conversations`
- `GET /{conversation_id}/history`
- `GET /{conversation_id}/history/paginated`

## Dependências de código
- Serviços
  - `chat_service`

## Símbolos
- function: `chat_history(conversation_id: str, limit: int | None = None, offset: int = 0, before_ts: float | None = None, after_ts: float | None = None, service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `chat_history_paginated(conversation_id: str, limit: int = 50, offset: int = 0, before_ts: float | None = None, after_ts: float | None = None, service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `list_conversations(project_id: str | None = None, limit: int = 50, service: ChatService = Depends(get_chat_service), http: Request = None)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
