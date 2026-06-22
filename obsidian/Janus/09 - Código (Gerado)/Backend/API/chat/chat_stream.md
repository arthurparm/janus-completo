---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/chat_stream.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/chat_stream

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/chat_stream.py`

## Rotas
- `GET /stream/{conversation_id}`
- `GET /{conversation_id}/events`
- `GET /{conversation_id}/trace`

## Dependências de código
- Serviços
  - `chat_service`
  - `intent_routing_service`
  - `trace_service`

## Símbolos
- function: `stream_message(conversation_id: str, message: str, role: str = 'auto', priority: str = 'fast_and_cheap', timeout_seconds: int | None = None, user_id: str | None = None, project_id: str | None = None, knowledge_space_id: str | None = None, service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `get_conversation_trace(conversation_id: str, service: TraceService = Depends(get_trace_service), chat_service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `stream_agent_events(conversation_id: str, user_id: str | None = None, service: ChatService = Depends(get_chat_service), http: Request = None)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
