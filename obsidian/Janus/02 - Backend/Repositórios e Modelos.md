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

## Mapeamento Detalhado Repository -> Banco

### PostgreSQL (SQLAlchemy)
**Repositórios que dependem de PostgreSQL como fonte de verdade:**

| Repository | Tabelas/Entidades | Impacto Falha | Observações |
|------------|-------------------|---------------|-------------|
| `chat_repository_sql` | `sessions`, `messages` | **CRÍTICO** | Chat transacional principal |
| `user_repository` | `users`, `profiles`, `roles`, `user_roles` | **CRÍTICO** | Identidade e autenticação |
| `consent_repository` | `user_privacy_consents` | **CRÍTICO** | LGPD/consentimentos |
| `prompt_repository` | `prompts` | **CRÍTICO** | Configurações de prompts do sistema |
| `agent_config_repository` | `agent_configurations` | **CRÍTICO** | Configurações de agentes |
| `optimization_repository` | `optimization_history` | **ALTO** | Histórico de otimizações |
| `autonomy_repository` | `autonomy_runs`, `autonomy_steps` | **CRÍTICO** | Execução de autonomia |
| `autonomy_goal_repository` | `autonomy_goals`, `autonomy_goal_transitions` | **CRÍTICO** | Metas e transições |
| `autonomy_admin_repository` | `autonomy_sprints`, `autonomy_task_evidence` | **ALTO** | Administração de autonomia |
| `autonomy_lock_repository` | `autonomy_loop_leases` | **ALTO** | Locks distribuídos |
| `pending_action_repository` | `pending_actions` | **ALTO** | Ações pendentes do sistema |
| `outbox_repository` | `outbox_events` | **ALTO** | Eventos para processamento assíncrono |
| `document_manifest_repository` | `document_manifests` | **ALTO** | Metadados de documentos |
| `knowledge_space_repository` | `knowledge_spaces` | **ALTO** | Espaços de conhecimento |
| `tool_usage_repository` | `tool_daily_usage` | **MÉDIO** | Uso de ferramentas e quotas |
| `ab_experiment_repository` | `ab_experiment_models` | **MÉDIO** | Experimentos A/B |
| `deployment_repository` | Deployment configs | **ALTO** | Deployments e releases |
| `observability_repository` (parte) | `audit_events` | **MÉDIO** | Auditoria e eventos de sistema |

### Neo4j (Grafo)
**Repositórios que dependem de Neo4j para estrutura de conhecimento:**

| Repository | Nós/Relações | Impacto Falha | Observações |
|------------|--------------|---------------|-------------|
| `knowledge_repository` | `Experience`, `Entity`, relações | **ALTO** | Grafo de conhecimento estrutural |
| `observability_repository` (parte) | Métricas de grafo | **MÉDIO** | Observabilidade do conhecimento |

**Serviços que acessam Neo4j diretamente:**
- `KnowledgeGraphService` - Cria nós `Experience` e `Entity`
- `CodeAnalysisService` - Cria `CodeFile`, `CodeFunction`, `CodeClass`
- `AutonomyAdminService` - Gerencia `SelfMemory` nodes

### Qdrant (Vetorial)
**Acesso direto via `vector_store.py` (não via repositórios tradicionais):**

| Coleção | Finalidade | Impacto Falha | Observações |
|-----------|------------|---------------|-------------|
| `janus_episodic_memory` | Memória episódica global | **CRÍTICO** | Fonte para consolidação |
| `user_chat_<user_id>` | Histórico de chat por usuário | **CRÍTICO** | Contexto para RAG |
| `user_docs_<user_id>` | Documentos chunkados por usuário | **ALTO** | Citações e contexto documental |
| `user_memory_<user_id>` | Memórias gerativas por usuário | **ALTO** | Preferências e regras |
| `user_secret_<user_id>` | Segredos cifrados por usuário | **ALTO** | Segurança e privacidade |

**Services que acessam Qdrant:**
- `MemoryCore` - Interface principal para memória vetorial
- `RAGService` - Recuperação de contexto para chat
- `DocumentIngestionService` - Indexação de documentos
- `KnowledgeConsolidator` - Consolidação de conhecimento

### Redis (Cache/Coordenação)
**Repositórios e serviços que usam Redis:**

| Repository | Finalidade | Impacto Falha | Fallback |
|------------|------------|---------------|----------|
| `RateLimitMiddleware` | Rate limiting HTTP | **MÉDIO** | Fail-open, fallback local em endpoints específicos |
| `ConfigService` | Hot-reload de config | **MÉDIO** | Reinício manual necessário |
| `RedisUsageTracker` | Tracking de uso e quotas | **MÉDIO** | Best-effort, PostgreSQL como backup |

### RabbitMQ (Message Broker)
**Repositórios que dependem de RabbitMQ:**

| Repository | Finalidade | Impacto Falha | Observações |
|------------|------------|---------------|-------------|
| `task_repository` | Filas de tarefas assíncronas | **ALTO** | Workers paralisados, sistema síncrono continua |

**Workers afetados:**
- `DocumentIngestionWorker` - Processamento de documentos
- `KnowledgeConsolidatorWorker` - Consolidação de conhecimento
- `CodeAnalysisWorker` - Análise de código em background

### Fallback Local (JSON/File)
**Repositórios que usam fallback local:**

| Repository | Finalidade | Quando Usado | Observações |
|------------|------------|--------------|-------------|
| `chat_repository` | Chat local via JSON | Desenvolvimento/Testing | Não é persistência principal do deploy |
| `learning_repository` | Aprendizado local | Desenvolvimento | Não crítico para produção |
| `agent_repository` | Agentes locais | Desenvolvimento | Não crítico para produção |

## Padrões de Acesso e Transações

### PostgreSQL
- **Transações ACID** via SQLAlchemy
- **Connection pooling** configurado em `postgres_config.py`
- **Health check** via `pg_isready` no docker-compose
- **Fail behavior**: Sem PostgreSQL = sistema não inicializa

### Neo4j  
- **Transações** via driver Neo4j
- **Modo offline** quando indisponível (retorna `[]` para queries)
- **Circuit breaker** implementado em `GraphDatabase.connect()`
- **Fail behavior**: Degradação silenciosa, chat básico continua

### Qdrant
- **REST API** via cliente HTTP
- **Modo offline** quando indisponível
- **Cache local** em `MemoryCore` por tempo limitado
- **Fail behavior**: Perda de RAG e memória, chat continua sem contexto

### Redis
- **Fail-open** por padrão
- **Pub/Sub** para configurações em tempo real
- **Lua scripts** para rate limiting
- **Fail behavior**: Best-effort, sem impacto crítico

### RabbitMQ
- **ACK/NACK** para garantia de processamento
- **Dead letter queues** para mensagens falhadas
- **Fail behavior**: Processamento assíncrono parado

## Repositórios centrais por backend (Original)
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
