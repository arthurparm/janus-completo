---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/reflexion_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# reflexion_worker

## Objetivo
Reflexion Worker - Consome tarefas de reflexão e publica sinais de falha.

## Arquivos-fonte
- `backend/app/core/workers/reflexion_worker.py`

## Filas/loops observáveis
- `QueueName.FAILURE_DETECTED`
- `QueueName.REFLEXION_TASKS`
- `janus.failure.detected`
- `janus.tasks.reflexion`

## Símbolos
- function: `_ensure_services_initialized()` -> `None`
- function: `publish_reflexion_task(payload: dict[str, Any], correlation_id: str | None = None)` -> `dict[str, Any]`
  - Publica uma tarefa de Reflexion na fila interna.
- function: `_publish_failure_signal(reason: str, score: float, context: dict[str, Any])` -> `None`
- function: `process_reflexion_task(task: TaskMessage)` -> `None`
  - Processa uma tarefa de Reflexion recebida da fila.
- function: `start_reflexion_worker()`
  - Inicia o consumidor da fila de Reflexion.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
