---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/config_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# config_service

## Arquivos-fonte
- `backend/app/services/config_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/admin_config.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `ConfigService`
  - Service for managing configuration hot-reloads via Redis Pub/Sub.
Allows dynamic updates to AppSettings across all running instances.
- method: `ConfigService.__init__(self)`
- method: `ConfigService.start(self)`
  - Starts the background listener task.
- method: `ConfigService.stop(self)`
  - Stops the background listener task.
- method: `ConfigService._listen_loop(self)`
  - Main loop for listening to Redis Pub/Sub messages.
- method: `ConfigService._handle_update(self, data: bytes | str)`
  - Parses update message and applies changes to settings.
- method: `ConfigService.update_config(self, updates: dict[str, Any])`
  - Updates configuration locally and publishes event to other instances.
- function: `get_config_service()` -> `ConfigService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
