---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/assistant.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# assistant

## Arquivos-fonte
- `backend/app/api/v1/endpoints/assistant.py`

## Rotas
- `POST /assistant/execute`

## Dependências de código
- Serviços
  - `assistant_service`

## Símbolos
- class: `AssistantExecuteRequest`
- class: `AssistantExecutionResult`
- function: `assistant_execute(body: AssistantExecuteRequest, assistant: AssistantService = Depends(get_assistant_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
