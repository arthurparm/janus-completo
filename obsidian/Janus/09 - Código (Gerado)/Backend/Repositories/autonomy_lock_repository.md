---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/autonomy_lock_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_lock_repository

## Arquivos-fonte
- `backend/app/repositories/autonomy_lock_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/services/autonomy_lock_service.py`

## Símbolos
- class: `AutonomyLockRepository`
- method: `AutonomyLockRepository.__init__(self, session: Session | None = None)`
- method: `AutonomyLockRepository._get_session(self)` -> `Session`
- method: `AutonomyLockRepository.try_acquire(self, *, scope_key: str, owner_id: str, ttl_seconds: int, metadata_json: str | None = None)` -> `tuple[bool, AutonomyLoopLease | None]`
- method: `AutonomyLockRepository.renew(self, *, scope_key: str, owner_id: str, ttl_seconds: int)` -> `tuple[bool, AutonomyLoopLease | None]`
- method: `AutonomyLockRepository.release(self, *, scope_key: str, owner_id: str)` -> `bool`
- method: `AutonomyLockRepository.get(self, scope_key: str)` -> `AutonomyLoopLease | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
