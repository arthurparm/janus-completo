---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/chat_citation_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_citation_service

## Arquivos-fonte
- `backend/app/services/chat/chat_citation_service.py`

## Símbolos
- function: `requires_mandatory_citations(message: str)` -> `bool`
- function: `references_uploaded_material(message: str)` -> `bool`
- function: `map_citation_hits(items: list[dict[str, Any]])` -> `list[dict[str, Any]]`
- function: `build_citation_status(*, message: str, citations: list[dict[str, Any]], retrieval_failed: bool = False)` -> `dict[str, Any]`
- function: `_dedupe_citations(citations: list[dict[str, Any]], limit: int)` -> `list[dict[str, Any]]`
- function: `_map_document_hits(points: list[Any])` -> `list[dict[str, Any]]`
- function: `_query_document_citations(*, message: str, conversation_id: str | None, limit: int)` -> `list[dict[str, Any]]`
- function: `_recent_document_citations(*, conversation_id: str | None, limit: int)` -> `list[dict[str, Any]]`
- function: `collect_document_citations(*, message: str, conversation_id: str | None, limit: int = 5)` -> `list[dict[str, Any]]`
- function: `collect_chat_citations(*, message: str, conversation_id: str | None, memory_service: Any | None = None, limit: int = 5)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
