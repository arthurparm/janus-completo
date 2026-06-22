---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/agent_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# agent_repository

## Arquivos-fonte
- `backend/app/repositories/agent_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/agent_service.py`

## Símbolos
- class: `AgentRepositoryError`
  - Base exception for agent repository errors.
- class: `AgentRepository`
  - Camada de Repositório para o Agent Manager.
Recebe sua dependência de infraestrutura via DI.
- method: `AgentRepository.__init__(self, manager: AgentManager)`
- method: `AgentRepository.run_agent(self, question: str, agent_type: AgentType, http_request: Request)` -> `dict[str, Any]`
  - Executa um agente através do agent_manager.
- function: `get_agent_repository(manager: AgentManager = Depends(get_agent_manager))` -> `AgentRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
