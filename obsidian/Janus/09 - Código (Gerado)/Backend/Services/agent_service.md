---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/agent_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# agent_service

## Arquivos-fonte
- `backend/app/services/agent_service.py`

## Dependências de código
- Repositórios
  - `agent_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/agent.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `AgentServiceError`
  - Base exception for agent service errors.
- class: `AgentTimeoutError`
  - Raised when agent execution exceeds the time limit.
- class: `AgentExecutionError`
  - Raised for general errors during agent execution.
- class: `AgentService`
  - Camada de serviço para orquestrar a execução de agentes.
Recebe sua dependência de repositório via DI.
- method: `AgentService.__init__(self, repo: AgentRepository)`
- method: `AgentService.execute_agent(self, question: str, agent_type: AgentType, http_request: Request)` -> `dict[str, Any]`
  - Orquestra a execução de um agente com um timeout, delegando a chamada
para o repositório.
- function: `get_agent_service(request: Request)` -> `AgentService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
