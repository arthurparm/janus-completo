---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/workers.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# workers

## Arquivos-fonte
- `backend/app/api/v1/endpoints/workers.py`

## Rotas
- `GET /status`
- `POST /start-all`
- `POST /stop-all`

## Símbolos
- function: `_task_status(task: Any)` -> `dict[str, Any]`
- function: `_is_worker_active(task: Any)` -> `bool`
- function: `_cancel_worker_task(task: Any)` -> `int`
- function: `start_workers(request: Request)`
- function: `stop_workers(request: Request)`
- function: `workers_status(request: Request)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
