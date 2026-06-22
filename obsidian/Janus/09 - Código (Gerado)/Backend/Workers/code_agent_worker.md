---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/code_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# code_agent_worker

## Objetivo
Code Agent Worker

## Arquivos-fonte
- `backend/app/core/workers/code_agent_worker.py`

## Filas/loops observáveis
- `JANUS.tasks.agent.coder`
- `QueueName.TASKS_AGENT_CODER`

## Símbolos
- function: `_build_coding_prompt(state: TaskState, compilation_error: str | None = None)` -> `str`
- function: `_estimate_complexity(code: str)` -> `int`
- function: `process_code_task(task: TaskMessage)` -> `None`
- function: `_validate_code_syntax(code: str)` -> `dict[str, Any]`
  - Validate Python code syntax using compile().
- function: `start_code_agent_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
