---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/documents.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# documents

## Arquivos-fonte
- `backend/app/api/v1/endpoints/documents.py`

## Rotas
- `DELETE /{doc_id}`
- `GET /list`
- `GET /search`
- `GET /status/{doc_id}`
- `POST /link-url`
- `POST /upload`

## Dependências de código
- Serviços
  - `document_service`

## Símbolos
- function: `get_doc_service(request: Request)` -> `DocumentIngestionService`
- function: `get_knowledge_facade(request: Request)`
- function: `_resolve_upload_user_scope(request: Request | None)` -> `str | None`
- class: `UploadResponse`
- function: `upload_document(file: UploadFile = File(...), request: Request = None, service: DocumentIngestionService = Depends(get_doc_service), auto_consolidate: bool | None = Form(False), conversation_id: str | None = Form(None), knowledge_space_id: str | None = Form(None), source_type: str | None = Form(None), source_id: str | None = Form(None), doc_role: str | None = Form(None), edition_or_version: str | None = Form(None), language: str | None = Form(None), parent_collection_id: str | None = Form(None))`
- class: `DocSearchResponse`
- function: `search_documents(query: str = Query(...), doc_id: str | None = None, knowledge_space_id: str | None = None, limit: int = 5, min_score: float | None = None, request: Request = None, knowledge = Depends(get_knowledge_facade))`
- class: `DocListItem`
- class: `DocListResponse`
- function: `list_documents(conversation_id: str | None = None, knowledge_space_id: str | None = None, request: Request = None, limit: int = 100, knowledge = Depends(get_knowledge_facade))`
- function: `delete_document(doc_id: str, request: Request = None, knowledge = Depends(get_knowledge_facade))`
- function: `_normalize_content_type(raw_content_type: str | None)` -> `str`
- function: `_is_supported_upload(file: UploadFile)` -> `bool`
- function: `_is_allowed_link_url(raw_url: str)` -> `bool`
- function: `_is_allowlisted_host(raw_url: str)` -> `bool`
- function: `_resolve_safe_http_target(raw_url: str)` -> `tuple[str, str, str] | None`
- function: `_is_public_http_url(raw_url: str)` -> `bool`
- class: `LinkUrlResponse`
- function: `link_url(url: str = Form(...), conversation_id: str | None = Form(None), knowledge_space_id: str | None = Form(None), source_type: str | None = Form(None), source_id: str | None = Form(None), doc_role: str | None = Form(None), edition_or_version: str | None = Form(None), language: str | None = Form(None), parent_collection_id: str | None = Form(None), request: Request = None, service: DocumentIngestionService = Depends(get_doc_service))`
- class: `DocStatusResponse`
- function: `_build_doc_samples(points: list[Any])` -> `list[dict[str, Any]]`
- function: `document_status(doc_id: str, request: Request = None, knowledge = Depends(get_knowledge_facade))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
