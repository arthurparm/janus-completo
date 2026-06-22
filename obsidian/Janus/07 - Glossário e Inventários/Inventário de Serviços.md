---
tipo: inventario
dominio: backend
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Serviços

## Objetivo
Listar os serviços nomeados do backend.

## Responsabilidades
- Facilitar navegação por capacidade.

## Entradas
- `backend/app/services/*.py`

## Saídas
- Índice de serviços.

## Dependências
- [[02 - Backend/Como o Backend Pensa]]
- [[02 - Backend/Repositórios e Modelos]]

## Serviços
- `ab_testing_service`
- `active_memory_service`
- `agent_service`
- `assistant_service`
- `autonomy_admin_service`
- `autonomy_lock_service`
- `autonomy_service`
- `bias_check_service`
- `chat_agent_loop`
- `chat_citation_service`
- `chat_command_handler`
- `chat_contracts`
- `chat_event_logger`
- `chat_event_publisher`
- `chat_service`
- `chat_study_service`
- `code_analysis_service`
- `code_hybrid_search_service`
- `collaboration_service`
- `config_service`
- `context_service`
- `conversation_service`
- `data_governance_service`
- `data_purge_service`
- `data_retention_service`
- `db_migration_service`
- `dedupe_service`
- `document_parser_service`
- `document_semantic_enrichment_service`
- `document_service`
- `feedback_service`
- `intent_routing_service`
- `knowledge_extraction_service`
- `knowledge_graph_service`
- `knowledge_service`
- `knowledge_space_service`
- `learning_service`
- `llm_service`
- `memory_service`
- `message_helpers`
- `message_orchestration_service`
- `meta_agent_service`
- `observability_service`
- `optimization_service`
- `outbox_service`
- `predictive_anomaly_detection_service`
- `procedural_memory_service`
- `prompt_builder_service`
- `prompt_composer_service`
- `prompt_service`
- `rag_service`
- `reasoning_rag_service`
- `reflexion_service`
- `resource_manager`
- `sandbox_service`
- `scheduler_service`
- `secret_key_rotation_service`
- `secret_memory_service`
- `secret_retention_service`
- `semantic_commit_service`
- `semantic_reranker_service`
- `streaming_service`
- `system_status_service`
- `system_user_service`
- `task_service`
- `technical_qa_eval_service`
- `tool_executor_service`
- `tool_service`
- `trace_service`
- `user_preference_memory_service`
- `vault_transit_rotation_service`
## Recorte tools e sandbox
- `tool_service`: camada de catálogo sobre `ToolRepository`; lista, detalha, cria e remove tools no `action_registry`.
- `tool_executor_service`: parser e executor real de `tool_call_envelope`; valida schema, política, quotas, simulação, timeout e auditoria.
- `sandbox_service`: fachada HTTP para `python_sandbox`; executa código/expressão e descreve capacidades do sandbox.

## Arquivos-fonte
- `backend/app/services/*.py`

## Fluxos relacionados
- [[07 - Glossário e Inventários/Inventário de Endpoints]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Riscos/Lacunas
- O inventário comprime serviços auxiliares menos centrais para manter legibilidade.
