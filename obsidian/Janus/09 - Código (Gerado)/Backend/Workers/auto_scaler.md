---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/auto_scaler.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# auto_scaler

## Objetivo
Queue Auto-Scaler

## Arquivos-fonte
- `backend/app/core/workers/auto_scaler.py`

## Filas/loops observáveis
- `QueueName.AGENT_TASKS`
- `QueueName.KNOWLEDGE_CONSOLIDATION`
- `QueueName.META_AGENT_CYCLE`
- `QueueName.NEURAL_TRAINING`

## Símbolos
- class: `_QueueRule`
- method: `_QueueRule.__init__(self, queue_name: str, callback: Callable[[Any], Awaitable[Any]], min_consumers: int = 1, max_consumers: int = 4, prefetch_per_consumer: int = 5, scale_up_backlog: int = 25, scale_down_backlog: int = 5, enabled: bool = True)` -> `None`
- function: `_apply_settings_overrides()` -> `None`
- function: `_ensure_consumers(queue_name: str, target_ours: int, rule: _QueueRule)` -> `None`
- function: `_scale_once()` -> `None`
- function: `start_auto_scaler(poll_interval_seconds: int | None = None)` -> `asyncio.Task`
  - Inicia o auto-escalador em background.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
