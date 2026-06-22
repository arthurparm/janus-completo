---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat/message_orchestration_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# message_orchestration_service

## Arquivos-fonte
- `backend/app/services/chat/message_orchestration_service.py`

## Dependências de código
- Repositórios
  - `chat_repository`
  - `document_manifest_repository`

## Símbolos
- class: `MessageOrchestrationService`
- method: `MessageOrchestrationService.__init__(self, *, repo: ChatRepository, llm_service: Any, tool_service: Any | None, prompt_service: PromptBuilderService, rag_service: RAGService | None, command_handler: ChatCommandHandler, agent_loop: ChatAgentLoop, conversation_service: ConversationService, outbox_service: OutboxService | None = None, manifest_repo: DocumentManifestRepository | None = None)`
- method: `MessageOrchestrationService._should_use_light_chat(self, *, message: str, role: ModelRole, understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._schedule_rag_index_message(self, *, text: str, conversation_id: str, role: str, project_id: str | None, identity_source: str)` -> `None`
- method: `MessageOrchestrationService.schedule_active_memory_capture(self, *, user_id: str | None, message: str, conversation_id: str)` -> `None`
- method: `MessageOrchestrationService._trim_document_snippet(text: str | None, *, limit: int = 480)` -> `str`
- method: `MessageOrchestrationService._list_document_manifests(self, *, conversation_id: str)` -> `list[dict[str, Any]]`
- method: `MessageOrchestrationService._extract_knowledge_space_ids(manifests: list[dict[str, Any]])` -> `list[str]`
- method: `MessageOrchestrationService._resolve_knowledge_space_id(self, *, manifests: list[dict[str, Any]], requested_knowledge_space_id: str | None)` -> `str | None`
- method: `MessageOrchestrationService._tokenize_source_title(value: str | None)` -> `set[str]`
- method: `MessageOrchestrationService._infer_manifest_source_role(row: dict[str, Any])` -> `str`
- method: `MessageOrchestrationService._manifest_primary_rank(cls, row: dict[str, Any])` -> `tuple[int, int]`
- method: `MessageOrchestrationService._message_explicitly_requests_secondary_sources(cls, *, message: str, manifests: list[dict[str, Any]], understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._message_prefers_primary_only(*, message: str, understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._apply_document_source_policy(cls, *, citations: list[dict[str, Any]], manifests: list[dict[str, Any]], message: str, understanding: dict[str, Any] | None)` -> `list[dict[str, Any]]`
- method: `MessageOrchestrationService._prefer_canonical_answer(message: str, understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._prefer_quick_lookup(message: str, understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._resolve_knowledge_space_mode(self, *, message: str, understanding: dict[str, Any] | None, requested_knowledge_space_id: str | None, source_scope: dict[str, Any] | None)` -> `str`
- method: `MessageOrchestrationService._generate_knowledge_space_reply(self, *, manifests: list[dict[str, Any]], requested_knowledge_space_id: str | None, conversation_id: str, message: str, role: ModelRole, understanding: dict[str, Any] | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService.build_knowledge_space_runtime_notice(self, *, conversation_id: str, message: str, requested_knowledge_space_id: str | None = None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService.resolve_active_knowledge_space_id(self, *, conversation_id: str, requested_knowledge_space_id: str | None = None)` -> `str | None`
- method: `MessageOrchestrationService._should_use_document_grounding(self, *, message: str, understanding: dict[str, Any] | None, manifests: list[dict[str, Any]])` -> `bool`
- method: `MessageOrchestrationService._build_document_processing_result(self, *, message: str, manifests: list[dict[str, Any]], role: ModelRole)` -> `dict[str, Any]`
- method: `MessageOrchestrationService._build_document_grounding_prompt(self, *, message: str, citations: list[dict[str, Any]])` -> `str`
- method: `MessageOrchestrationService.generate_secret_recall_reply(self, *, message: str, role: ModelRole, user_id: str | None, conversation_id: str | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService.apply_response_memory_policies(self, *, assistant_text: str, user_message: str, conversation_id: str)` -> `str`
- method: `MessageOrchestrationService._build_document_grounding_recheck_prompt(self, *, message: str, citations: list[dict[str, Any]])` -> `str`
- method: `MessageOrchestrationService._is_document_operational_task(*, message: str, understanding: dict[str, Any] | None)` -> `bool`
- method: `MessageOrchestrationService._build_document_operational_prompt(self, *, message: str, citations: list[dict[str, Any]])` -> `str`
- method: `MessageOrchestrationService._normalize_document_text(value: str | None)` -> `str`
- method: `MessageOrchestrationService._sanitize_document_grounding_extraction(self, *, extraction: dict[str, Any] | None, citations: list[dict[str, Any]])` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService._sanitize_document_operational_extraction(self, *, extraction: dict[str, Any] | None, citations: list[dict[str, Any]])` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService._recheck_document_grounding(self, *, message: str, citations: list[dict[str, Any]], role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, project_id: str | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService._extract_document_grounding(self, *, message: str, citations: list[dict[str, Any]], role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, project_id: str | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService._extract_document_operational_grounding(self, *, message: str, citations: list[dict[str, Any]], role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, project_id: str | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService._format_document_grounded_response(self, *, extraction: dict[str, Any] | None, citations: list[dict[str, Any]])` -> `str`
- method: `MessageOrchestrationService._format_document_operational_response(self, *, extraction: dict[str, Any] | None, citations: list[dict[str, Any]])` -> `str`
- method: `MessageOrchestrationService.generate_document_grounded_reply(self, *, conversation_id: str, message: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, project_id: str | None, requested_knowledge_space_id: str | None = None, understanding: dict[str, Any] | None)` -> `dict[str, Any] | None`
- method: `MessageOrchestrationService.send_message(self, conversation_id: str, message: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None = None, project_id: str | None = None, knowledge_space_id: str | None = None, identity_source: str = 'unknown')` -> `dict[str, Any]`
- method: `MessageOrchestrationService.trigger_post_response_events(self, conversation_id: str, user_message: str, assistant_text: str, result: dict[str, Any], project_id: str | None)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
