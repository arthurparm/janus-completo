---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/ab_experiment_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# ab_experiment_repository

## Arquivos-fonte
- `backend/app/repositories/ab_experiment_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/evaluation.py`
- `backend/app/repositories/llm_repository.py`
- `backend/app/services/ab_testing_service.py`

## Símbolos
- class: `ABExperimentRepository`
- method: `ABExperimentRepository.__init__(self, session: Session | None = None)`
- method: `ABExperimentRepository._get_session(self)` -> `Session`
- method: `ABExperimentRepository.create_experiment(self, name: str, user_id: str | None)` -> `Experiment`
- method: `ABExperimentRepository.add_arm(self, experiment_id: int, name: str, model_spec: str)` -> `ExperimentArm`
- method: `ABExperimentRepository.list_experiments(self, user_id: str | None, limit: int = 50)` -> `list[Experiment]`
- method: `ABExperimentRepository.add_result(self, experiment_id: int, arm_id: int, metric_name: str, metric_value: float)` -> `ExperimentResult`
- method: `ABExperimentRepository.assign_user(self, experiment_id: int, user_id: str)` -> `ExperimentAssignment`
- method: `ABExperimentRepository.get_assignment(self, experiment_id: int, user_id: str)` -> `ExperimentAssignment | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
