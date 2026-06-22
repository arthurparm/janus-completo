---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/agent_tasks_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# agent_tasks_worker

## Objetivo
Async Agent Tasks Worker

## Arquivos-fonte
- `backend/app/core/workers/agent_tasks_worker.py`

## Filas/loops observáveis
- `QueueName.AGENT_TASKS`

## Símbolos
- function: `_get_bulkhead(agent_type: AgentType)` -> `asyncio.Semaphore`
- function: `_get_circuit(agent_type: AgentType)` -> `CircuitBreaker`
- function: `_parse_agent_type(value: Any)` -> `AgentType`
- function: `process_agent_task(task: TaskMessage)` -> `None`
  - Process an agent task message and run the agent.
- function: `publish_agent_task(question: str, agent_type: AgentType | str)` -> `str`
  - Publish an agent task message to the broker.
- function: `start_agent_tasks_worker()`
  - Start the agent tasks consumer worker.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
