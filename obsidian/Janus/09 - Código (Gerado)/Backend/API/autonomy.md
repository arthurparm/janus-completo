---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/autonomy.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy

## Arquivos-fonte
- `backend/app/api/v1/endpoints/autonomy.py`

## Rotas
- `DELETE /goals/{goal_id}`
- `GET /goals`
- `GET /goals/{goal_id}`
- `GET /plan`
- `GET /status`
- `PATCH /goals/{goal_id}/status`
- `POST /goals`
- `POST /start`
- `POST /stop`
- `PUT /plan`
- `PUT /policy`

## Dependências de código
- Serviços
  - `autonomy_admin_service`
  - `autonomy_service`

## Símbolos
- class: `AutonomyStartRequest`
- class: `AutonomyStatusResponse`
- class: `PlanUpdateRequest`
- function: `_validate_plan_steps(plan: list[dict[str, Any]], allowlist: list[str] | None = None, blocklist: list[str] | None = None)` -> `None`
  - Valida cada passo do plano: shape, existência da ferramenta, args_schema e listas de permissão.
- class: `GoalCreateRequest`
- class: `GoalStatusUpdateRequest`
- class: `GoalResponse`
- function: `start_autonomy(request: AutonomyStartRequest, http: Request, service: AutonomyService = Depends(get_autonomy_service))`
- function: `stop_autonomy(service: AutonomyService = Depends(get_autonomy_service))`
- function: `autonomy_status(service: AutonomyService = Depends(get_autonomy_service))`
- function: `update_autonomy_plan(request: PlanUpdateRequest, service: AutonomyService = Depends(get_autonomy_service))`
- class: `PolicyUpdateRequest`
- function: `update_policy(request: PolicyUpdateRequest, service: AutonomyService = Depends(get_autonomy_service))`
- function: `get_autonomy_plan(service: AutonomyService = Depends(get_autonomy_service))`
- function: `create_goal(req: GoalCreateRequest, manager: GoalManager = Depends(get_goal_manager))`
- function: `list_goals(status: str | None = None, manager: GoalManager = Depends(get_goal_manager))`
- function: `get_goal(goal_id: str, manager: GoalManager = Depends(get_goal_manager))`
- function: `update_goal_status(goal_id: str, req: GoalStatusUpdateRequest, request: Request, background_tasks: BackgroundTasks, manager: GoalManager = Depends(get_goal_manager))`
- function: `delete_goal(goal_id: str, manager: GoalManager = Depends(get_goal_manager))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
