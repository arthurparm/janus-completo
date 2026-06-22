---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/orchestrator.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# orchestrator

## Objetivo
Orquestrador de Workers

## Arquivos-fonte
- `backend/app/core/workers/orchestrator.py`

## Símbolos
- function: `get_orchestrator_worker_names()` -> `list[str]`
- class: `DisabledWorkerHandle`
  - Representa um worker intencionalmente desativado por configuração.
- function: `_normalize_node_profile(value: Any)` -> `str | None`
- function: `_get_active_node_profile()` -> `str | None`
- function: `_is_worker_enabled_for_profile(worker_name: str, profile: str | None)` -> `bool`
- function: `start_all_workers()`
  - Inicia todos os workers assíncronos do sistema.
Retorna a lista de tarefas/consumidores iniciados.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
