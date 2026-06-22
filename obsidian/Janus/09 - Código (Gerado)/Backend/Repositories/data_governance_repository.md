---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/data_governance_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_governance_repository

## Arquivos-fonte
- `backend/app/repositories/data_governance_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/repositories/chat_repository_sql.py`
- `backend/app/services/data_governance_service.py`
- `backend/app/services/data_purge_service.py`
- `backend/app/services/document_service.py`
- `backend/app/services/knowledge_space_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/secret_memory_service.py`

## Símbolos
- class: `DataGovernanceRepositoryError`
- class: `DataGovernanceRepository`
- method: `DataGovernanceRepository.__init__(self, session: Session | None = None)`
- method: `DataGovernanceRepository._get_session(self)` -> `Session`
- method: `DataGovernanceRepository.upsert_record(self, *, user_id: int | None, resource_type: str, resource_id: str, classification: str, classification_source: str, retention_policy: str, retention_days: int | None, retention_until: datetime | None, metadata_json: dict[str, Any] | None = None)` -> `int`
- method: `DataGovernanceRepository.list_expired(self, *, now: datetime | None = None, limit: int = 250)` -> `list[DataGovernanceRecord]`
- method: `DataGovernanceRepository.mark_purged(self, *, record_id: int, purge_job_id: str, purged_at: datetime | None = None)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
