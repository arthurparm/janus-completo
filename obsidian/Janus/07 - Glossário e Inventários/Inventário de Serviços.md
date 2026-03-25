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
- `agent_service`
- `assistant_service`
- `autonomy_admin_service`
- `autonomy_service`
- `chat_service`
- `chat_agent_loop`
- `chat_command_handler`
- `chat_study_service`
- `code_analysis_service`
- `collaboration_service`
- `config_service`
- `context_service`
- `db_migration_service`
- `document_service`
- `feedback_service`
- `intent_routing_service`
- `knowledge_service`
- `knowledge_space_service`
- `learning_service`
- `llm_service`
- `memory_service`
- `meta_agent_service`
- `observability_service`
- `optimization_service`
- `outbox_service`
- `prompt_builder_service`
- `prompt_service`
- `rag_service`
- `reflexion_service`
- `sandbox_service`
- `scheduler_service`
- `system_status_service`
- `task_service`
- `tool_executor_service`
- `tool_service`
- `trace_service`

## Arquivos-fonte
- `backend/app/services/*.py`

## Fluxos relacionados
- [[07 - Glossário e Inventários/Inventário de Endpoints]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Riscos/Lacunas
- O inventário comprime serviços auxiliares menos centrais para manter legibilidade.
