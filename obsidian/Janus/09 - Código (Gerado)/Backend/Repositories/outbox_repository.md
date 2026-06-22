---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/outbox_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# outbox_repository

## Arquivos-fonte
- `backend/app/repositories/outbox_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/outbox_service.py`

## Símbolos
- class: `OutboxEventRecord`
- class: `OutboxRepositoryError`
- class: `OutboxRepository`
- method: `OutboxRepository.enqueue(self, *, event_type: str, payload_json: dict[str, Any], aggregate_id: str | None = None, dedupe_key: str | None = None)` -> `int`
- method: `OutboxRepository.claim_pending(self, *, limit: int = 50)` -> `list[OutboxEventRecord]`
- method: `OutboxRepository.mark_sent(self, event_id: int)` -> `None`
- method: `OutboxRepository.mark_retry(self, event_id: int, *, error: str, max_attempts: int = 10)` -> `str`
- method: `OutboxRepository.get_stats(self)` -> `dict[str, int]`
- method: `OutboxRepository.requeue_dead(self, *, limit: int = 100)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
