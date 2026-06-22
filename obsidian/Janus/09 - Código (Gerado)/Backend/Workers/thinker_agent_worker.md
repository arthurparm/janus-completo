---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/thinker_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# thinker_agent_worker

## Objetivo
Thinker Agent Worker (Reasoning Node)

## Arquivos-fonte
- `backend/app/core/workers/thinker_agent_worker.py`

## Filas/loops observáveis
- `JANUS.tasks.agent.thinker.`
- `QueueName.TASKS_AGENT_THINKER`

## Símbolos
- function: `_build_thinking_prompt(state: TaskState)` -> `str`
- function: `process_thinker_task(task: TaskMessage)` -> `None`
- function: `start_thinker_agent_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
