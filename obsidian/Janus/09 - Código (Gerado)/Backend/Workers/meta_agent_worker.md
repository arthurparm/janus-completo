---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/meta_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# meta_agent_worker

## Objetivo
Meta-Agent Cycle Worker

## Arquivos-fonte
- `backend/app/core/workers/meta_agent_worker.py`

## Filas/loops observáveis
- `QueueName.FAILURE_DETECTED`
- `QueueName.META_AGENT_CYCLE`
- `janus.failure.detected`
- `janus.meta_agent.cycle`

## Símbolos
- function: `_clamp_priority(value: int)` -> `int`
- function: `_compute_trigger_priority(mode: str, payload: dict[str, Any])` -> `int`
- function: `_mode_cooldown_seconds(mode: str)` -> `int`
- function: `_ensure_memory_initialized()` -> `None`
- function: `request_meta_agent_cycle(mode: str = 'single', payload: dict[str, Any] | None = None, priority: int | None = None, force: bool = False)` -> `str | None`
  - Queue a Meta-Agent cycle with debounce/cooldown/priority control.
Returns task_id when queued, or None when dropped.
- function: `process_meta_agent_cycle(task: TaskMessage)` -> `None`
  - Process a single Meta-Agent cycle task.
- function: `publish_meta_agent_cycle(mode: str = 'single', priority: int = 5, payload_extra: dict[str, Any] | None = None)` -> `str`
  - Publish a cycle request to janus.meta_agent.cycle queue.
- function: `start_meta_agent_worker()`
  - Start janus.meta_agent.cycle consumer.
- function: `process_failure_event(task: TaskMessage)` -> `None`
  - Consume janus.failure.detected events and trigger Meta-Agent analysis.
Also stores a compact memory entry for future diagnostics.
- function: `start_failure_event_consumer()`
  - Start janus.failure.detected consumer.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
