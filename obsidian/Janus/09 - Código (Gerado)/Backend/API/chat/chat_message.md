---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/chat_message.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/chat_message

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/chat_message.py`

## Rotas
- `POST /message`
- `POST /start`

## Dependências de código
- Serviços
  - `chat_service`
  - `chat_study_service`
  - `intent_routing_service`
  - `memory_service`

## Símbolos
- function: `_get_chat_study_job_service(http: Request, service: ChatService)` -> `ChatStudyJobService`
- function: `start_chat(request: ChatStartRequest, service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `send_message(payload: ChatMessageRequest, service: ChatService = Depends(get_chat_service), http: Request = None, memory: MemoryService = Depends(get_memory_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
