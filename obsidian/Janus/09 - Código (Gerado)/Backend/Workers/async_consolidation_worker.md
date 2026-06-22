---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/async_consolidation_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# async_consolidation_worker

## Objetivo
Async Knowledge Consolidation Worker - Sprint 1 + Sprint 8

## Arquivos-fonte
- `backend/app/core/workers/async_consolidation_worker.py`

## Filas/loops observáveis
- `QueueName.KNOWLEDGE_CONSOLIDATION`
- `janus.event.conversation.`
- `janus.events`

## Símbolos
- function: `process_consolidation_task(task: TaskMessage)` -> `None`
  - Processa uma tarefa de consolidação de conhecimento recebida do RabbitMQ.
- function: `publish_consolidation_task(payload: dict[str, Any], correlation_id: str | None = None)` -> `dict[str, Any]`
  - Publica uma tarefa de consolidação na fila apropriada.
- function: `start_consolidation_worker()`
  - Inicia o worker de consolidação de conhecimento.
Consome mensagens da fila de consolidação e processa em background.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
