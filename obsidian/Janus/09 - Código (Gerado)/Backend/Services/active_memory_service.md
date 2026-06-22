---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/active_memory_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# active_memory_service

## Arquivos-fonte
- `backend/app/services/active_memory_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/chat/message_orchestration_service.py`

## Símbolos
- class: `ActiveMemoryService`
  - Separates memory capture from memory recall and promotes only durable signals.
- method: `ActiveMemoryService.maybe_capture_from_message(self, *, user_id: str | None, message: str, conversation_id: str | None, identity_source: str = 'unknown', target_entity: str | None = None)` -> `dict[str, Any] | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
