---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/collaboration.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# collaboration

## Arquivos-fonte
- `backend/app/api/v1/endpoints/collaboration.py`

## Rotas
- `GET /agents`
- `GET /agents/{agent_id}`
- `GET /health`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /workspace/status`
- `POST /agents/create`
- `POST /projects/execute`
- `POST /tasks/create`
- `POST /tasks/execute`
- `POST /tasks/execute_parallel`

## Dependências de código
- Serviços
  - `collaboration_service`

## Símbolos
- class: `CreateAgentRequest`
- class: `CreateAgentResponse`
- class: `CreateTaskRequest`
- class: `ExecuteTaskRequest`
- class: `ExecuteProjectRequest`
- class: `ExecuteTasksParallelRequest`
- function: `create_agent(request: CreateAgentRequest, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a criação de um novo agente para o CollaborationService.
- function: `list_agents(service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a listagem de agentes para o CollaborationService.
- function: `get_agent_details(agent_id: str, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a busca de detalhes do agente para o CollaborationService.
- function: `create_task(request: CreateTaskRequest, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a criação de uma tarefa para o CollaborationService.
- function: `execute_task(request: ExecuteTaskRequest, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a execução de uma tarefa para o CollaborationService.
- function: `list_tasks(service: CollaborationService = Depends(get_collaboration_service), status: str | None = None)`
  - Delega a listagem de tarefas para o CollaborationService.
- function: `get_task_details(task_id: str, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a busca de detalhes da tarefa para o CollaborationService.
- function: `execute_project(request: ExecuteProjectRequest, service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a execução de um projeto para o CollaborationService.
- function: `get_workspace_status(service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a busca de status do workspace para o CollaborationService.
- function: `execute_tasks_parallel(request: ExecuteTasksParallelRequest, service: CollaborationService = Depends(get_collaboration_service))`
  - Executa tarefas em paralelo, respeitando dependências entre elas.
- function: `health_check(service: CollaborationService = Depends(get_collaboration_service))`
  - Delega a verificação de saúde para o CollaborationService.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
