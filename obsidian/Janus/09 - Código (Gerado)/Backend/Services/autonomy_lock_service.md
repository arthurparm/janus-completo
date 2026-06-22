---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/autonomy_lock_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_lock_service

## Arquivos-fonte
- `backend/app/services/autonomy_lock_service.py`

## Dependências de código
- Repositórios
  - `autonomy_lock_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/autonomy_service.py`

## Símbolos
- class: `AutonomyLeaseState`
- class: `AutonomyLockService`
- method: `AutonomyLockService.__init__(self, repo: AutonomyLockRepository | None = None)`
- method: `AutonomyLockService.make_owner_id()` -> `str`
- method: `AutonomyLockService.make_scope_key(*, user_id: str | None, project_id: str | None)` -> `str`
- method: `AutonomyLockService.try_acquire(self, *, scope_key: str, owner_id: str, ttl_seconds: int, metadata: dict | None = None)` -> `tuple[bool, AutonomyLeaseState]`
- method: `AutonomyLockService.renew(self, *, scope_key: str, owner_id: str, ttl_seconds: int)` -> `tuple[bool, AutonomyLeaseState]`
- method: `AutonomyLockService.release(self, *, scope_key: str, owner_id: str)` -> `bool`
- method: `AutonomyLockService.get(self, *, scope_key: str)` -> `AutonomyLeaseState`
- method: `AutonomyLockService._to_state(scope_key: str, owner_id: str | None, held: bool, row)` -> `AutonomyLeaseState`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
