---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/codex_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# codex_worker

## Objetivo
Codex Worker

## Arquivos-fonte
- `backend/app/core/workers/codex_worker.py`

## Filas/loops observáveis
- `QueueName.TASKS_CODEX_WORKER`

## Símbolos
- function: `_build_codex_policy(approved: bool)` -> `PolicyEngine`
- function: `process_codex_task(task: TaskMessage)` -> `None`
- function: `start_codex_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
