---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/neural_training_system.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# neural_training_system

## Objetivo
Sprint 9: Gênese Neural - Sistema de Treinamento Autônomo

## Arquivos-fonte
- `backend/app/core/workers/neural_training_system.py`

## Símbolos
- function: `_experience_to_dict(exp: Any)` -> `dict[str, Any]`
  - Normaliza experiências para dicts (dict / Pydantic model / objeto leve).
- function: `_load_prompt_template(prompt_name: str)` -> `str`
- class: `ModelType`
  - Tipos de modelos que podem ser treinados.
- class: `TrainingStatus`
  - Status de um job de treinamento.
- class: `TrainingConfig`
  - Configuração para treinamento de modelo.
- class: `TrainingResult`
  - Resultado de um job de treinamento.
- class: `DatasetPreparator`
  - Prepara datasets de treino a partir de experiências coletadas.
- method: `DatasetPreparator.prepare_for_llm_finetuning(self, experiences: list[dict[str, Any] | Experience])` -> `list[dict[str, str]]`
  - Prepara dataset para fine-tuning de LLM (formato chat/completion).
- method: `DatasetPreparator.prepare_for_classification(self, experiences: list[dict[str, Any] | Experience])` -> `tuple[list[str], list[str]]`
  - Prepara dataset para treinamento de classificador.
- method: `DatasetPreparator.prepare_for_prediction(self, experiences: list[dict[str, Any] | Experience])` -> `list[dict[str, Any]]`
  - Prepara dataset para predição de próximas ações.
- class: `NeuralTrainer`
  - Sistema de treinamento autônomo de modelos.
- method: `NeuralTrainer.__init__(self)`
- method: `NeuralTrainer.train_model(self, config: TrainingConfig)` -> `TrainingResult`
  - Treina um modelo com a configuração especificada.
- method: `NeuralTrainer._load_training_data(self, config: TrainingConfig)` -> `list[dict[str, Any]]`
  - Carrega dados de treino da memória episódica ou arquivo.
- method: `NeuralTrainer._prepare_dataset(self, model_type: ModelType, experiences: list[dict[str, Any]])` -> `Any`
  - Prepara dataset baseado no tipo de modelo.
- method: `NeuralTrainer._train(self, config: TrainingConfig, dataset: Any)` -> `TrainingResult`
  - Executa treinamento do modelo.
- method: `NeuralTrainer._validate(self, config: TrainingConfig, result: TrainingResult)` -> `TrainingResult`
  - Valida performance do modelo em dataset de validação.
- method: `NeuralTrainer._save_model(self, config: TrainingConfig, result: TrainingResult)` -> `TrainingResult`
  - Salva modelo treinado em disco.
- method: `NeuralTrainer._memorize_training(self, config: TrainingConfig, result: TrainingResult)`
  - Memoriza resultado do treinamento.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
