---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/google_productivity_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# google_productivity_worker

## Arquivos-fonte
- `backend/app/core/workers/google_productivity_worker.py`

## Filas/loops observáveis
- `janus.productivity.google.calendar`
- `janus.productivity.google.mail`

## Símbolos
- function: `publish_google_calendar_add_event(user_id: int, event: dict[str, Any], index: bool)` -> `str`
- function: `publish_google_mail_send(user_id: int, message: dict[str, Any], index: bool)` -> `str`
- function: `start_google_productivity_consumer()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
