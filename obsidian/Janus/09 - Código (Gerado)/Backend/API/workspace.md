---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/workspace.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# workspace

## Arquivos-fonte
- `backend/app/api/v1/endpoints/workspace.py`

## Rotas
- `GET /workspace/artifacts/{key}`
- `GET /workspace/messages/{agent_id}`
- `POST /system/shutdown`
- `POST /workspace/artifacts/add`
- `POST /workspace/messages/send`

## Dependências de código
- Serviços
  - `collaboration_service`

## Símbolos
- class: `AddArtifactRequest`
- function: `add_artifact(payload: AddArtifactRequest, service: CollaborationService = Depends(get_collaboration_service))`
- function: `get_artifact(key: str, service: CollaborationService = Depends(get_collaboration_service))`
- class: `SendMessageRequest`
- function: `send_message(payload: SendMessageRequest, service: CollaborationService = Depends(get_collaboration_service))`
- function: `get_messages_for(agent_id: str, service: CollaborationService = Depends(get_collaboration_service))`
- function: `shutdown_system(service: CollaborationService = Depends(get_collaboration_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
