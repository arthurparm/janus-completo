---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/rag_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# rag_service

## Arquivos-fonte
- `backend/app/services/rag_service.py`

## Dependências de código
- Repositórios
  - `chat_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/planes/knowledge/facade.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `RAGServiceError`
  - Base exception for RAG service errors.
- class: `RAGService`
  - Service responsible for Retrieval-Augmented Generation (RAG) operations,
including memory retrieval, indexing, and conversation summarization.
- method: `RAGService.__init__(self, repo: ChatRepository, llm_service: LLMService, memory_service: Optional[MemoryService] = None)`
- method: `RAGService._format_memories(self, memories: list[dict[str, Any]])` -> `Optional[str]`
- method: `RAGService._format_memory_block(self, title: str, items: list[str])` -> `str | None`
- method: `RAGService._format_episodic_context(self, memories: list[dict[str, Any]])` -> `str | None`
- method: `RAGService._merge_memory_sections(self, sections: list[str | None])` -> `str | None`
- method: `RAGService._score_episodic_memory(self, item: dict[str, Any], *, conversation_id: str | None)` -> `float`
- method: `RAGService._retrieve_episodic_context(self, *, message: str, conversation_id: str | None, limit: int)` -> `tuple[list[dict[str, Any]], dict[str, Any]]`
- method: `RAGService._retrieve_semantic_context(self, *, message: str, limit: int)` -> `tuple[list[dict[str, Any]], str | None]`
- method: `RAGService._retrieve_procedural_context(self, *, message: str, conversation_id: str | None, limit: int)` -> `tuple[list[dict[str, Any]], str | None]`
- method: `RAGService._references_uploaded_material(self, message: str)` -> `bool`
- method: `RAGService._conversation_document_context(self, *, conversation_id: str, limit: int = 3)` -> `str | None`
- method: `RAGService._emit_step_telemetry(self, *, endpoint: str, step: str, started_at: float, db: str, confidence: float | None, error_code: str | None = None, extra: dict[str, Any] | None = None)` -> `None`
- method: `RAGService.retrieve_context(self, message: str, limit: int = 5, conversation_id: str | None = None, user_id: str | None = None, caller_endpoint: str = '/chat/rag', transport: str = 'unknown', identity_source: str = 'unknown', route_decision: RouteDecision | None = None)` -> `Optional[str]`
  - Retrieves relevant memories for the current message.
- method: `RAGService._combine_memory_context(self, preference_context: str | None, generic_context: str | None)` -> `str | None`
- method: `RAGService.maybe_index_message(self, text: str, conversation_id: str, role: str, caller_endpoint: str = '/chat/rag', transport: str = 'unknown', identity_source: str = 'unknown')` -> `None`
- method: `RAGService.maybe_summarize(self, conversation_id: str, role: ModelRole, priority: ModelPriority, project_id: Optional[str], threshold_messages: int = 80)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
