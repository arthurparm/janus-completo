---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/learning_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# learning_repository

## Arquivos-fonte
- `backend/app/repositories/learning_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/workers/neural_training_worker.py`
- `backend/app/services/learning_service.py`

## Símbolos
- class: `LearningRepository`
  - Camada de Repositório para dados de aprendizado e treinamento.
Abstrai a lógica de armazenamento e a execução de workers.
- method: `LearningRepository.__init__(self)`
- method: `LearningRepository.get_all_models(self)` -> `list[ModelInfo]`
  - Lista modelos treinados lendo do filesystem (workspace/models).
- method: `LearningRepository.find_model_by_id(self, model_id: str)` -> `ModelInfo | None`
  - Busca modelo pelo id (nome da pasta) lendo do filesystem.
- method: `LearningRepository.save_model(self, model_info: ModelInfo)` -> `ModelInfo`
- method: `LearningRepository.get_active_training_session(self)` -> `TrainingSession | None`
- method: `LearningRepository.get_stats(self)` -> `dict[str, Any]`
- method: `LearningRepository.increment_harvested_count(self, count: int)`
- method: `LearningRepository.run_training_process(self, dataset_version: str | None = None, model_name: str | None = None, training_params: dict[str, Any] | None = None)` -> `dict[str, Any]`
  - Executa o processo de treinamento com NeuralTrainer e tracking de experimento.
- method: `LearningRepository.run_harvesting(self, limit: int, query: str | None = None, min_score: float | None = None, origin: str | None = None)` -> `dict[str, Any]`
  - Abstrai a execução do worker de coleta de dados.
- method: `LearningRepository.is_harvester_healthy(self)` -> `bool`
  - Verifica a saúde do worker de coleta de dados.
- method: `LearningRepository._update_dataset_version(self)` -> `dict[str, Any]`
  - Computa versão do dataset baseada no conteúdo atual do JSONL.
- method: `LearningRepository.get_dataset_version_info(self)` -> `dict[str, Any]`
- method: `LearningRepository._create_experiment(self, dataset_info: dict[str, Any])` -> `str`
- method: `LearningRepository.list_experiments(self)` -> `list[dict[str, Any]]`
- method: `LearningRepository.get_experiment(self, experiment_id: str)` -> `dict[str, Any] | None`
- function: `get_learning_repository()` -> `LearningRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
