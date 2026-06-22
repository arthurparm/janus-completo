---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/router_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# router_worker

## Objetivo
Router Worker (Rececionista)

## Arquivos-fonte
- `backend/app/core/workers/router_worker.py`

## Filas/loops observáveis
- `JANUS.tasks.router`
- `QueueName.KNOWLEDGE_CONSOLIDATION`
- `QueueName.TASKS_KNOWLEDGE_DISTILLATION`
- `QueueName.TASKS_ROUTER`

## Símbolos
- function: `_decompose_complex_task(goal: str)` -> `str`
  - Usa o prompt task_decomposition para analisar requisições complexas.
- function: `_infer_first_agent(original_goal: str)` -> `str`
  - Fallback heurístico para o primeiro agente; prefere 'thinker'.
- function: `_contains_knowledge_payload(state: TaskState)` -> `bool`
  - Heurística: decide se o TaskState contém conhecimento a ser consolidado.
- function: `_extract_routed_role(notes: str | None)` -> `str | None`
- function: `_is_repeated_route_loop(state: TaskState, next_role: str)` -> `bool`
- function: `_choose_loop_escape_role(next_role: str)` -> `str`
- function: `process_router_task(task: TaskMessage)` -> `None`
  - Processa mensagens de roteamento e encaminha para o próximo agente.
- function: `start_router_worker()`
  - Inicia o consumidor da fila central do Router.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
