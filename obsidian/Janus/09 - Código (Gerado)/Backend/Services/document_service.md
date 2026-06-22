---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/document_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# document_service

## Arquivos-fonte
- `backend/app/services/document_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`
  - `document_manifest_repository`
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/documents.py`
- `backend/app/core/kernel.py`
- `backend/app/planes/knowledge/facade.py`

## Símbolos
- class: `DocumentFileTooLargeError`
- method: `DocumentFileTooLargeError.__init__(self, size_bytes: int, max_bytes: int, doc_id: str)`
- class: `DocumentIngestionService`
- method: `DocumentIngestionService.__init__(self, memory_service: Any | None = None, manifest_repo: DocumentManifestRepository | None = None, outbox_service: OutboxService | None = None)`
- method: `DocumentIngestionService.build_doc_id(self, user_id: str)` -> `str`
- method: `DocumentIngestionService.storage_root(self)` -> `Path`
- method: `DocumentIngestionService.resolve_storage_path(self, *, user_id: str, doc_id: str, filename: str)` -> `Path`
- method: `DocumentIngestionService._chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100)` -> `list[str]`
- method: `DocumentIngestionService.stage_upload(self, *, file: UploadFile, user_id: str, conversation_id: str | None, knowledge_space_id: str | None = None, source_type: str | None = None, source_id: str | None = None, doc_role: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None, auto_consolidate: bool = False)` -> `dict[str, Any]`
- method: `DocumentIngestionService.cleanup_staged_file(self, storage_path: str | Path | None)` -> `None`
- method: `DocumentIngestionService.process_staged_document(self, *, doc_id: str)` -> `dict[str, Any]`
- method: `DocumentIngestionService._recover_indexed_document_without_staged_file(self, *, manifest: dict[str, Any])` -> `dict[str, Any] | None`
- method: `DocumentIngestionService._progress_callback(self, doc_id: str)` -> `Callable[..., Awaitable[None]]`
- method: `DocumentIngestionService.ingest_file(self, filename: str, content_type: str, data: bytes, conversation_id: str | None = None, knowledge_space_id: str | None = None, source_type: str | None = None, source_id: str | None = None, doc_role: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None)` -> `dict[str, Any]`
- method: `DocumentIngestionService._ingest_payload(self, *, doc_id: str, filename: str, content_type: str, data: bytes, conversation_id: str | None = None, knowledge_space_id: str | None = None, source_type: str | None = None, source_id: str | None = None, doc_role: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None, file_size_bytes: int = 0, progress_cb: Callable[..., Awaitable[None]] | None = None)` -> `dict[str, Any]`
- method: `DocumentIngestionService._delete_doc_points(self, *, doc_id: str)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
