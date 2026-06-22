---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/streaming_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# streaming_service

## Arquivos-fonte
- `backend/app/services/chat/streaming_service.py`

## Dependências de código
- Repositórios
  - `chat_repository`

## Símbolos
- class: `StreamingService`
- method: `StreamingService.__init__(self, *, repo: ChatRepository, llm_service: Any, tool_service: Any | None, prompt_service: PromptBuilderService, rag_service: RAGService | None, conversation_service: ConversationService, message_orchestration_service: MessageOrchestrationService)`
- method: `StreamingService.stream_message(self, conversation_id: str, message: str, role: ModelRole | None = None, priority: ModelPriority | None = None, timeout_seconds: int | None = None, user_id: str | None = None, project_id: str | None = None, knowledge_space_id: str | None = None, identity_source: str = 'unknown', requested_role: str | None = None, routing_decision: Any | None = None, route_applied: bool | None = None)`
- method: `StreamingService.stream_events(self, conversation_id: str, user_id: str | None = None)`
- method: `StreamingService._cb_should_block(self, provider: str | None)` -> `bool`
- method: `StreamingService._cb_on_error(self, provider: str | None)` -> `None`
- method: `StreamingService._cb_on_success(self, provider: str | None)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
