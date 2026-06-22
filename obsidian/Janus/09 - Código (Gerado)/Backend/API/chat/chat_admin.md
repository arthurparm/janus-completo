---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/chat_admin.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/chat_admin

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/chat_admin.py`

## Rotas
- `DELETE /{conversation_id}`
- `GET /health`
- `PUT /{conversation_id}/rename`

## Dependências de código
- Serviços
  - `chat_service`

## Símbolos
- function: `rename_conversation(conversation_id: str, payload: ChatRenameRequest, service: ChatService = Depends(get_chat_service), http: Request = None)`
- function: `chat_health(service: ChatService = Depends(get_chat_service))`
- function: `delete_conversation(conversation_id: str, project_id: str | None = None, service: ChatService = Depends(get_chat_service), http: Request = None)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
