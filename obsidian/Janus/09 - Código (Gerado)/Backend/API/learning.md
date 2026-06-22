---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/learning.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# learning

## Arquivos-fonte
- `backend/app/api/v1/endpoints/learning.py`

## Rotas
- `GET /dataset/preview`
- `GET /dataset/version`
- `GET /experiments`
- `GET /experiments/{experiment_id}`
- `GET /health`
- `GET /models`
- `GET /models/{model_id}`
- `GET /stats`
- `GET /training/status`
- `POST /evaluate`
- `POST /harvest`
- `POST /train`

## Dependências de código
- Serviços
  - `learning_service`

## Símbolos
- class: `HarvestRequest`
- class: `TrainingConfig`
- class: `TrainRequest`
- class: `LearningResponse`
- class: `TrainingAckResponse`
- class: `TrainingStatusResponse`
- class: `ModelInfo`
- class: `ModelListResponse`
- class: `EvaluateRequest`
- class: `EvaluationResponse`
- class: `DatasetVersionResponse`
- class: `ExperimentInfo`
- class: `ExperimentListResponse`
- function: `trigger_harvesting(request: HarvestRequest, learning_service: LearningService = Depends(get_learning_service))`
  - Delega a coleta de dados de experiência para o LearningService.
- function: `trigger_training(request: TrainRequest, learning_service: LearningService = Depends(get_learning_service))`
  - Agenda o processo de treinamento de modelo via fila e retorna ack com task_id.
- function: `get_training_status(learning_service: LearningService = Depends(get_learning_service))`
  - Busca o status de qualquer sessão de treinamento ativa via LearningService.
- function: `list_models(learning_service: LearningService = Depends(get_learning_service))`
  - Delega a listagem de modelos para o LearningService.
- function: `get_model_details(model_id: str, learning_service: LearningService = Depends(get_learning_service))`
  - Delega a busca de detalhes de um modelo para o LearningService.
- function: `get_learning_stats(learning_service: LearningService = Depends(get_learning_service))`
  - Delega a busca de estatísticas para o LearningService.
- function: `preview_dataset(limit: int = 20, learning_service: LearningService = Depends(get_learning_service))`
  - Retorna os primeiros N exemplos do dataset de treino (JSONL).
- function: `evaluate_model(request: EvaluateRequest, learning_service: LearningService = Depends(get_learning_service))`
  - Delega a avaliação de um modelo para o LearningService.
- function: `get_dataset_version(learning_service: LearningService = Depends(get_learning_service))`
  - Retorna metadados de versão do dataset de treino.
- function: `list_experiments(learning_service: LearningService = Depends(get_learning_service))`
  - Lista os experimentos rastreados pelo repositório de aprendizado.
- function: `get_experiment_details(experiment_id: str, learning_service: LearningService = Depends(get_learning_service))`
  - Detalhes de um experimento específico.
- function: `learning_health(learning_service: LearningService = Depends(get_learning_service))`
  - Verifica a saúde do sistema de treinamento.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
