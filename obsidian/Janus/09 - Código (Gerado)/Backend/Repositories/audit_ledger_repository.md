---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/audit_ledger_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# audit_ledger_repository

## Arquivos-fonte
- `backend/app/repositories/audit_ledger_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/repositories/observability_repository.py`
- `backend/app/services/scheduler_service.py`

## Símbolos
- function: `_canonical_json(payload: Any)` -> `str`
- function: `_sha256_hex(value: str)` -> `str`
- function: `_get_hmac_key()` -> `bytes`
- class: `AuditLedgerRepository`
  - Ledger append-only com hash-chain e assinatura HMAC.
- method: `AuditLedgerRepository._get_session(self)` -> `Session`
- method: `AuditLedgerRepository.append(self, *, actor_user_id: int | None, endpoint: str, action: str, tool: str | None, status: str, trace_id: str | None, payload_json: dict[str, Any] | None)` -> `int | None`
- method: `AuditLedgerRepository.list_events(self, *, user_id: int | None, tool: str | None, status: str | None, endpoint: str | None, start_ts: float | None, end_ts: float | None, limit: int, offset: int)` -> `list[AuditLedgerEvent]`
- method: `AuditLedgerRepository.count_events(self, *, user_id: int | None, tool: str | None, status: str | None, endpoint: str | None, start_ts: float | None, end_ts: float | None)` -> `int`
- method: `AuditLedgerRepository.list_events_by_trace_id(self, *, trace_id: str, limit: int, offset: int)` -> `list[AuditLedgerEvent]`
- method: `AuditLedgerRepository.verify_integrity(self, *, max_errors: int = 25)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
