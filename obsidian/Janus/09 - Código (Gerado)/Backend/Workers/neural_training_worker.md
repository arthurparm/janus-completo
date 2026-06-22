---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/neural_training_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# neural_training_worker

## Objetivo
Async Neural Training Worker

## Arquivos-fonte
- `backend/app/core/workers/neural_training_worker.py`

## Filas/loops observáveis
- `QueueName.NEURAL_TRAINING`

## Símbolos
- function: `process_neural_training_task(task: TaskMessage)` -> `None`
  - Process a neural training task by invoking the LearningRepository.
- function: `publish_neural_training_task(dataset_version: str | None = None, model_name: str | None = None, training_params: dict[str, Any] | None = None, user_id: str | None = None)` -> `str`
  - Publish a neural training task to the broker.
- function: `start_neural_training_worker()`
  - Start the neural training consumer worker.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
