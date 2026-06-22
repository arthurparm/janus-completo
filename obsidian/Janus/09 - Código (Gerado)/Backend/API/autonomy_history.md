---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/autonomy_history.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_history

## Arquivos-fonte
- `backend/app/api/v1/endpoints/autonomy_history.py`

## Rotas
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/enqueues`
- `GET /runs/{run_id}/steps`

## Dependências de código
- Repositórios
  - `autonomy_repository`

## Símbolos
- function: `get_autonomy_repo(request: Request)` -> `AutonomyRepository`
- class: `RunSummary`
- class: `StepItem`
- class: `EnqueueLedgerItem`
- function: `list_runs(project_id: str | None = None, limit: int = 50, repo: AutonomyRepository = Depends(get_autonomy_repo))`
- function: `get_run(run_id: int, repo: AutonomyRepository = Depends(get_autonomy_repo))`
- function: `list_steps(run_id: int, cycle: int | None = None, limit: int = 100, repo: AutonomyRepository = Depends(get_autonomy_repo))`
- function: `list_enqueues(run_id: int, limit: int = 100, repo: AutonomyRepository = Depends(get_autonomy_repo))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
