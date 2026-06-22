---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/rag.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# rag

## Arquivos-fonte
- `backend/app/api/v1/endpoints/rag.py`

## Rotas
- `GET /hybrid_search`
- `GET /productivity`
- `GET /search`
- `GET /user-chat`
- `GET /user_chat`

## Dependências de código
- Serviços
  - `code_hybrid_search_service`
  - `memory_service`

## Símbolos
- function: `get_knowledge_facade(request: Request)`
- function: `_emit_rag_step(*, endpoint: str, step: str, source: str, db: str, started_at: float, scores: list[Any] | None = None, confidence: float | None = None, error_code: str | None = None, extra: dict[str, Any] | None = None)` -> `None`
- class: `RAGSearchResponse`
- function: `rag_search(query: str = Query(..., description='Pergunta ou texto de busca'), type: str | None = Query(None, description='Filtrar por tipo da experiência'), origin: str | None = Query(None, description='Filtrar por metadata.origin'), doc_id: str | None = Query(None, description='Filtrar por metadata.doc_id'), file_path: str | None = Query(None, description='Filtrar por metadata.file_path'), limit: int | None = Query(5, ge=1, le=10), min_score: float | None = Query(None, ge=0.0, le=1.0), service: MemoryService = Depends(get_memory_service))`
- class: `RAGUserChatResponse`
- function: `rag_user_chat_search(request: Request, query: str = Query(..., description='Pergunta ou texto de busca'), session_id: str | None = Query(None, description='ID da conversa para filtrar'), role: str | None = Query(None, description='Filtrar por role (user|assistant)'), limit: int | None = Query(5, ge=1, le=10), min_score: float | None = Query(None, ge=0.0, le=1.0), knowledge = Depends(get_knowledge_facade))`
- class: `RAGProductivityResponse`
- function: `rag_productivity_search(request: Request, query: str = Query(..., description='Consulta'), type: str | None = Query(None, description='calendar_event|email_message|note_item'), limit: int | None = Query(5, ge=1, le=10), min_score: float | None = Query(None, ge=0.0, le=1.0), knowledge = Depends(get_knowledge_facade))`
- class: `RAGUserChatResponseV2`
- function: `rag_user_chat_search_v2(query: str, session_id: str | None = None, start_ts_ms: int | None = None, end_ts_ms: int | None = None, limit: int = 5, min_score: float | None = None, http: Request = None, knowledge = Depends(get_knowledge_facade))`
- class: `RAGHybridResponse`
- function: `rag_hybrid_search(query: str, limit: int = 5, min_score: float | None = None, http: Request = None)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
