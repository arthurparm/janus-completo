---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/evaluation.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# evaluation

## Arquivos-fonte
- `backend/app/api/v1/endpoints/evaluation.py`

## Rotas
- `GET /experiments`
- `GET /experiments/{experiment_id}/winner`
- `POST /experiments`
- `POST /experiments/{experiment_id}/arms`
- `POST /experiments/{experiment_id}/results`

## Dependências de código
- Serviços
  - `ab_testing_service`
- Repositórios
  - `ab_experiment_repository`

## Símbolos
- function: `get_repo()` -> `ABExperimentRepository`
- class: `ExperimentCreateRequest`
- class: `ExperimentResponse`
- class: `ArmCreateRequest`
- class: `ArmResponse`
- class: `ResultCreateRequest`
- function: `create_experiment(req: ExperimentCreateRequest, repo: ABExperimentRepository = Depends(get_repo))`
- function: `add_arm(experiment_id: int, req: ArmCreateRequest, repo: ABExperimentRepository = Depends(get_repo))`
- function: `list_experiments(repo: ABExperimentRepository = Depends(get_repo))`
- function: `add_result(experiment_id: int, req: ResultCreateRequest, repo: ABExperimentRepository = Depends(get_repo))`
- function: `experiment_winner(experiment_id: int, metric_name: str = 'accuracy')`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
