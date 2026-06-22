---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/data_purge_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_purge_service

## Arquivos-fonte
- `backend/app/services/data_purge_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`
  - `document_manifest_repository`
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/governance.py`
- `backend/app/services/scheduler_service.py`

## Símbolos
- class: `DataPurgeServiceError`
- class: `DataPurgeService`
- method: `DataPurgeService.__init__(self, *, gov_repo: DataGovernanceRepository | None = None, manifest_repo: DocumentManifestRepository | None = None)`
- method: `DataPurgeService._job_id()` -> `str`
- method: `DataPurgeService._cleanup_storage_path(storage_path: str | None)` -> `bool`
- method: `DataPurgeService.run_expired_purge(self, *, limit: int = 250)` -> `dict[str, Any]`
- method: `DataPurgeService._purge_one(self, *, item: Any, job_id: str, counters: dict[str, int])` -> `None`
- method: `DataPurgeService._delete_chat_session(self, *, session_id: str)` -> `bool`
- method: `DataPurgeService._delete_chat_message(self, *, message_id: str)` -> `bool`
- method: `DataPurgeService._delete_chat_points(self, *, session_id: str)` -> `None`
- method: `DataPurgeService._delete_memory_point(self, *, point_id: str)` -> `None`
- method: `DataPurgeService._purge_document(self, *, doc_id: str, user_id: int | None)` -> `bool`
- method: `DataPurgeService._purge_knowledge_space(self, *, knowledge_space_id: str, user_id: int | None)` -> `bool`
- method: `DataPurgeService._deactivate_secret(self, *, item: Any)` -> `bool`
- method: `DataPurgeService._purge_expired_neo4j(self, *, job_id: str)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
