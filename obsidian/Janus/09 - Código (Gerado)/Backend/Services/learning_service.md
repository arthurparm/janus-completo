---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/learning_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# learning_service

## Arquivos-fonte
- `backend/app/services/learning_service.py`

## Dependências de código
- Repositórios
  - `learning_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/learning.py`

## Símbolos
- class: `LearningServiceError`
  - Base exception for learning service errors.
- class: `ModelNotFoundError`
  - Raised when a model is not found.
- class: `TrainingFailedError`
  - Raised when the training process fails.
- class: `ExperimentNotFoundError`
  - Raised when an experiment is not found.
- class: `LearningService`
  - Camada de serviço para orquestrar a coleta de dados e o treinamento de modelos.
- method: `LearningService.__init__(self, repo: LearningRepository)`
- method: `LearningService.trigger_harvesting(self, limit: int, query: str | None = None, min_score: float | None = None, origin: str | None = None)` -> `dict[str, Any]`
- method: `LearningService.trigger_training(self, model_type: str, training_config: dict[str, Any], model_name: str | None = None, user_id: str | None = None)` -> `dict[str, Any]`
  - Publica uma tarefa de treinamento na fila e retorna o ack com task_id.
- method: `LearningService.get_training_status(self)` -> `dict[str, Any] | None`
- method: `LearningService.list_all_models(self)` -> `list[ModelInfo]`
- method: `LearningService.get_model_details(self, model_id: str)` -> `ModelInfo`
- method: `LearningService.get_learning_statistics(self)` -> `dict[str, Any]`
- method: `LearningService.get_health_status(self)` -> `dict[str, Any]`
- method: `LearningService.preview_dataset(self, limit: int = 20)` -> `dict[str, Any]`
  - Retorna os primeiros N exemplos do dataset de treino para inspeção rápida.
- method: `LearningService.evaluate_model(self, model_id: str, test_data_limit: int = 50)` -> `dict[str, Any]`
  - Avalia um modelo treinado usando dados disponíveis no workspace.
- method: `LearningService.get_dataset_version_info(self)` -> `dict[str, Any]`
- method: `LearningService.list_experiments(self)` -> `list[dict[str, Any]]`
- method: `LearningService.get_experiment_details(self, experiment_id: str)` -> `dict[str, Any]`
- function: `get_learning_service(repo: LearningRepository = Depends(get_learning_repository))` -> `LearningService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
