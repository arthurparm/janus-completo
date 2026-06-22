---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/collaboration_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# collaboration_service

## Arquivos-fonte
- `backend/app/services/collaboration_service.py`

## Dependências de código
- Repositórios
  - `autonomy_goal_repository`
  - `collaboration_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/collaboration.py`
- `backend/app/api/v1/endpoints/workspace.py`
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
- `backend/app/services/autonomy_service.py`

## Símbolos
- class: `CollaborationServiceError`
  - Base exception for collaboration service errors.
- class: `AgentNotFoundError`
  - Raised when an agent is not found.
- class: `TaskNotFoundError`
  - Raised when a task is not found.
- class: `CollaborationService`
  - Camada de serviço para o sistema de colaboração multi-agente.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `CollaborationService.__init__(self, repo: CollaborationRepository)`
- method: `CollaborationService.create_agent(self, role: AgentRole)` -> `dict[str, Any]`
- method: `CollaborationService.list_agents(self)` -> `list[dict[str, Any]]`
- method: `CollaborationService.get_agent_details(self, agent_id: str)` -> `dict[str, Any]`
- method: `CollaborationService.create_task(self, description: str, priority: TaskPriority, assigned_to: str | None, dependencies: list[str])` -> `Task`
- method: `CollaborationService.execute_task(self, task_id: str, agent_id: str)` -> `dict[str, Any]`
- method: `CollaborationService.list_tasks(self, status: TaskStatus | None = None)` -> `list[Task]`
- method: `CollaborationService.get_task_details(self, task_id: str)` -> `Task`
- method: `CollaborationService.execute_project(self, description: str)` -> `dict[str, Any]`
- method: `CollaborationService.get_workspace_status(self)` -> `dict[str, Any]`
- method: `CollaborationService.get_health_status(self)` -> `dict[str, Any]`
- method: `CollaborationService.add_artifact(self, key: str, value: Any, author: str)` -> `dict[str, Any]`
- method: `CollaborationService.get_artifact(self, key: str)` -> `Any | None`
- method: `CollaborationService.send_message(self, from_agent: str, to_agent: str, content: str)` -> `dict[str, Any]`
- method: `CollaborationService.get_messages_for(self, agent_id: str)` -> `list[dict[str, Any]]`
- method: `CollaborationService.shutdown_system(self)` -> `None`
- method: `CollaborationService.execute_tasks_parallel(self, task_ids: list[str] | None = None, concurrency: int = 4)` -> `dict[str, Any]`
  - Exposição de execução paralela com dependências via serviço.
- method: `CollaborationService.pass_task(self, task_state: TaskState)` -> `str`
  - Publica o TaskState na fila adequada com base em `next_agent_role`.
Fallback: roteia para `JANUS.tasks.router` quando indefinido.
- method: `CollaborationService.maybe_finalize_autonomy_goal(self, task_state: TaskState)` -> `None`
- method: `CollaborationService._try_finalize_autonomy_goal_from_taskstate(self, task_state: TaskState)` -> `None`
- function: `get_collaboration_service(request: Request)` -> `CollaborationService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
