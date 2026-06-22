---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/professor_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# professor_agent_worker

## Objetivo
Professor Agent Worker

## Arquivos-fonte
- `backend/app/core/workers/professor_agent_worker.py`

## Filas/loops observáveis
- `JANUS.tasks.agent.professor`
- `QueueName.TASKS_AGENT_PROFESSOR`

## Símbolos
- function: `_build_review_prompt(state: TaskState)` -> `str`
- function: `_parse_review_json(review_text: str)` -> `dict[str, Any]`
  - Parse JSON response from LLM using strict mode + regex fallback.
- function: `process_professor_task(task: TaskMessage)` -> `None`
- function: `start_professor_agent_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
