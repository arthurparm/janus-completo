---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/document_manifest_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# document_manifest_repository

## Arquivos-fonte
- `backend/app/repositories/document_manifest_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/data_purge_service.py`
- `backend/app/services/document_service.py`
- `backend/app/services/knowledge_space_service.py`

## Símbolos
- class: `DocumentManifestRepositoryError`
- class: `DocumentManifestRepository`
- method: `DocumentManifestRepository.create_manifest(self, *, doc_id: str, user_id: str, conversation_id: str | None, knowledge_space_id: str | None = None, source_type: str | None = None, source_id: str | None = None, doc_role: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None, file_name: str, content_type: str | None, file_size_bytes: int = 0, status: str = 'queued', storage_path: str | None = None)` -> `dict[str, Any]`
- method: `DocumentManifestRepository.get_manifest(self, doc_id: str, user_id: str | None = None)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository.list_manifests(self, *, user_id: str | None = None, conversation_id: str | None = None, knowledge_space_id: str | None = None, limit: int = 100, statuses: Iterable[str] | None = None)` -> `list[dict[str, Any]]`
- method: `DocumentManifestRepository.update_manifest(self, doc_id: str, *, user_id: str | None = None, **fields: Any)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository.delete_manifest(self, doc_id: str)` -> `bool`
- method: `DocumentManifestRepository.mark_processing(self, doc_id: str)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository.mark_completed(self, doc_id: str, *, chunks_total: int, chunks_indexed: int, semantic_doc_type: str | None, semantic_summary: str | None, semantic_confidence: float | None)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository.mark_failed(self, doc_id: str, *, status: str, error_code: str | None = None, error_message: str | None = None, chunks_total: int | None = None, chunks_indexed: int | None = None, file_size_bytes: int | None = None)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository.update_progress(self, doc_id: str, *, chunks_total: int, chunks_indexed: int, file_size_bytes: int | None = None, semantic_doc_type: str | None = None, semantic_summary: str | None = None, semantic_confidence: float | None = None)` -> `dict[str, Any] | None`
- method: `DocumentManifestRepository._serialize(self, row: DocumentManifest)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
