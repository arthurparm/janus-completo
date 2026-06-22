---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/autonomy_admin.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_admin

## Arquivos-fonte
- `backend/app/api/v1/endpoints/autonomy_admin.py`

## Rotas
- `GET /board`
- `GET /self-study/neo4j-audit`
- `GET /self-study/runs`
- `GET /self-study/status`
- `POST /backlog/sync`
- `POST /code-qa`
- `POST /self-study/neo4j-repair`
- `POST /self-study/run`
- `POST /self-study/trigger-on-goal-complete`

## Dependências de código
- Serviços
  - `autonomy_admin_service`

## Símbolos
- class: `BacklogSyncResponse`
- class: `SelfStudyRunRequest`
- class: `SelfStudyNeo4jRepairRequest`
- class: `CodeQARequest`
- class: `CodeQAResponse`
- function: `sync_backlog(service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `get_board(status: str | None = Query(default=None), limit: int = Query(default=200, ge=1, le=1000), service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `run_self_study(payload: SelfStudyRunRequest, service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `self_study_status(service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `self_study_runs(limit: int = Query(default=20, ge=1, le=200), service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `self_study_neo4j_audit(orphan_limit: int = Query(default=25, ge=1, le=200), service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `self_study_neo4j_repair(payload: SelfStudyNeo4jRepairRequest, service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `code_qa(payload: CodeQARequest, service: AutonomyAdminService = Depends(get_autonomy_admin_service))`
- function: `admin_manual_goal_completion_trigger(request: Request, background_tasks: BackgroundTasks)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
