---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/collaboration_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# collaboration_repository

## Arquivos-fonte
- `backend/app/repositories/collaboration_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/core/workers/code_agent_worker.py`
- `backend/app/core/workers/codex_worker.py`
- `backend/app/core/workers/debate_critic_worker.py`
- `backend/app/core/workers/debate_proponent_worker.py`
- `backend/app/core/workers/professor_agent_worker.py`
- `backend/app/core/workers/red_team_agent_worker.py`
- `backend/app/core/workers/router_worker.py`
- `backend/app/core/workers/sandbox_agent_worker.py`
- `backend/app/core/workers/thinker_agent_worker.py`
- `backend/app/services/collaboration_service.py`

## Símbolos
- class: `CollaborationRepositoryError`
  - Base exception for collaboration repository errors.
- class: `CollaborationRepository`
  - Camada de Repositório para o Sistema de Colaboração Multi-Agente.
Abstrai todas as interações diretas com a infraestrutura do `MultiAgentSystem`.
- method: `CollaborationRepository._get_system(self)` -> `MultiAgentSystem`
- method: `CollaborationRepository.create_agent(self, role: AgentRole)` -> `SpecializedAgent`
- method: `CollaborationRepository.find_all_agents(self)` -> `list[dict[str, Any]]`
- method: `CollaborationRepository.find_agent_by_id(self, agent_id: str)` -> `SpecializedAgent | None`
- method: `CollaborationRepository.find_tasks_by_agent(self, agent_id: str)` -> `list[Task]`
- method: `CollaborationRepository.save_task(self, task: Task)`
- method: `CollaborationRepository.run_task(self, agent: SpecializedAgent, task: Task)` -> `dict[str, Any]`
- method: `CollaborationRepository.find_all_tasks(self)` -> `list[Task]`
- method: `CollaborationRepository.find_tasks_by_status(self, status: TaskStatus)` -> `list[Task]`
- method: `CollaborationRepository.find_task_by_id(self, task_id: str)` -> `Task | None`
- method: `CollaborationRepository.run_project(self, description: str)` -> `dict[str, Any]`
- method: `CollaborationRepository.run_tasks_parallel(self, task_ids: list[str] | None = None, concurrency: int = 4)` -> `dict[str, Any]`
  - Executa tarefas em paralelo respeitando dependências usando o core system.
- method: `CollaborationRepository.get_workspace_status(self)` -> `dict[str, Any]`
- method: `CollaborationRepository.get_system_health(self)` -> `dict[str, Any]`
- method: `CollaborationRepository.add_artifact(self, key: str, value: Any, author: str)`
- method: `CollaborationRepository.get_artifact(self, key: str)` -> `Any | None`
- method: `CollaborationRepository.send_message(self, from_agent: str, to_agent: str, content: str)` -> `dict[str, Any]`
- method: `CollaborationRepository.get_messages_for(self, agent_id: str)` -> `list[dict[str, Any]]`
- method: `CollaborationRepository.shutdown_all(self)`
- function: `get_collaboration_repository()` -> `CollaborationRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
