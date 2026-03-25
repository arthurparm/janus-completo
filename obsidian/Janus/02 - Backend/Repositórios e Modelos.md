---
tipo: dominio
dominio: backend
camada: persistencia
fonte-de-verdade: codigo
status: ativo
---

# Repositórios e Modelos

## Objetivo
Registrar a base de persistência e os tipos de dados explícitos do backend.

## Responsabilidades
- Mapear repositórios por domínio.
- Mapear modelos nomeados usados como contratos internos.

## Entradas
- `backend/app/repositories`
- `backend/app/models`

## Saídas
- Inventário de persistência útil para troubleshooting e extensão.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[07 - Glossário e Inventários/Inventário de Entidades]]

## Repositórios centrais por backend
### Postgres
- Chat e identidade:
  - `chat_repository_sql`
  - `user_repository`
  - `consent_repository`
- Configuração e otimização:
  - `prompt_repository`
  - `agent_config_repository`
  - `optimization_repository`
- Autonomia e execução:
  - `autonomy_repository`
  - `autonomy_goal_repository`
  - `autonomy_admin_repository`
  - `autonomy_lock_repository`
  - `pending_action_repository`
  - `outbox_repository`
- Documentos e spaces:
  - `document_manifest_repository`
  - `knowledge_space_repository`
- Governança e métricas:
  - `tool_usage_repository`
  - `ab_experiment_repository`
  - `deployment_repository`
  - parte de `observability_repository`

### Neo4j
- `knowledge_repository`
- parte de `observability_repository`

### Qdrant
- `memory_repository` como porta lógica sobre `MemoryCore`
- serviços de memória/documento usam `db/vector_store.py` diretamente mais do que repositórios dedicados

### RabbitMQ / broker
- `task_repository`

### Processo / fallback local
- `chat_repository` usa arquivo JSON e atua como alternativa local/fallback, não como persistência principal do deploy
- `learning_repository`, `agent_repository`, `tool_repository`, `context_repository`, `sandbox_repository`, `collaboration_repository` e parte de `llm_repository`/`reflexion_repository` não são bancos transacionais centrais do runtime

## Modelos SQL que formam a fonte de verdade transacional
- Identidade e chat:
  - `user_models`
  - tabelas: `users`, `profiles`, `roles`, `user_roles`, `sessions`, `messages`, `user_privacy_consents`, `audit_events`, `oauth_tokens`
- Configuração:
  - `config_models`
  - tabelas: `prompts`, `agent_configurations`, `optimization_history`
- Autonomia:
  - `autonomy_models`
  - tabelas: `autonomy_runs`, `autonomy_steps`, `autonomy_goals`, `autonomy_goal_transitions`, `autonomy_sprints`, `autonomy_sprint_types`, `autonomy_task_evidence`, `autonomy_self_study_runs`, `autonomy_self_study_files`, `autonomy_self_study_state`, `autonomy_enqueue_ledger`, `autonomy_loop_leases`
- Execução e integração:
  - `pending_action_models`
  - `outbox_models`
  - `tool_usage_models`
  - `document_models`
  - `knowledge_space_models`
  - `quarantine_models`
  - `ab_experiment_models`
  - `ab_assignment_models`

## Arquivos-fonte
- `backend/app/repositories/*.py`
- `backend/app/models/*.py`
- `backend/app/db/postgres_config.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Riscos/Lacunas
- Há persistência híbrida entre SQL, grafo, vetorial e fila.
- O significado de algumas entidades depende mais do serviço que do modelo isolado.
- `KnowledgeSpace` e ingestão documental são domínios compostos: o repositório SQL sozinho não descreve o comportamento real sem considerar Qdrant e Neo4j.
