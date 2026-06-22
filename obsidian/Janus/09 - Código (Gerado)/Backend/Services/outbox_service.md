---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/outbox_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# outbox_service

## Arquivos-fonte
- `backend/app/services/outbox_service.py`

## Dependências de código
- Repositórios
  - `outbox_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/document_service.py`

## Símbolos
- class: `OutboxService`
- method: `OutboxService.__init__(self, repo: OutboxRepository)`
- method: `OutboxService.enqueue_consolidation(self, *, payload: dict[str, Any], aggregate_id: str | None, dedupe_key: str | None)` -> `int`
- method: `OutboxService.enqueue_document_ingestion(self, *, payload: dict[str, Any], aggregate_id: str | None, dedupe_key: str | None)` -> `int`
- method: `OutboxService.dispatch_pending(self, *, limit: int = 50)` -> `dict[str, int]`
- method: `OutboxService._dispatch_item(self, item: OutboxEventRecord)` -> `tuple[bool, str]`
- method: `OutboxService.start(self, *, interval_seconds: int = 5)` -> `None`
- method: `OutboxService.stop(self)` -> `None`
- method: `OutboxService.reconcile(self, *, limit: int = 100, requeue_dead: bool = True)` -> `dict[str, Any]`
- method: `OutboxService.get_stats(self)` -> `dict[str, int]`
- method: `OutboxService._run_loop(self)` -> `None`
- method: `OutboxService._resolve_queue(self, event_type: str)` -> `str`
- method: `OutboxService._update_gauges(self, *, stats: dict[str, int] | None = None)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
