## Objetivos

* Persistir conversas, mensagens, usuários e perfis com CRUD por `user_id/session_id`.

* Adotar RBAC básico (roles e permissões) e preparar multi‑tenant para indexação vetorial.

* Integrar com `Qdrant` e manter compatibilidade com a arquitetura e DI existentes.

## Arquitetura

* Banco relacional: `MySQL` via `SQLAlchemy` já configurado em `janus/app/db/mysql_config.py`.

* Vetor: `Qdrant` via `janus/app/db/vector_store.py` com payloads por `user_id/session_id`.

* Grafo: Neo4j permanece para conhecimento consolidado; sem acoplamento direto com conversas no MVP.

* Substituir `ChatRepository` baseado em arquivo por implementação SQL mantendo interface pública usada pelo `ChatService`.

## Modelagem de Dados (SQL)

* `users`: `id`, `external_id` (opcional), `email`, `display_name`, `status`, `created_at`, `updated_at`.

* `profiles`: `id`, `user_id` (FK), `timezone`, `language`, `style_prefs` (JSON), `created_at`, `updated_at`.

* `roles`: `id`, `name` (ex.: `USER`, `ADMIN`), `description`.

* `user_roles`: `user_id` (FK), `role_id` (FK), `created_at`.

* `sessions`: `id`, `user_id` (FK), `persona`, `project_id` (opcional), `title`, `created_at`, `updated_at`, `summary` (TEXT).

* `messages`: `id`, `session_id` (FK), `timestamp`, `role` (`user|assistant|system`), `text` (TEXT), índices por `session_id,timestamp`.

* Índices: por `user_id/session_id`, busca rápida de conversas recentes e filtros por usuário/projeto.

## Repositórios

* `ChatRepositorySQL`: mesma API do atual (`start_conversation`, `add_message`, `get_conversation`, `get_history`, `get_recent_messages`, `list_conversations`, `rename_conversation`, `delete_conversation`, `update_summary`, `count_conversations`), mas operando via `Session` do SQLAlchemy.

* `UserRepository` e `ProfileRepository`: CRUD simples para usuários, perfis e papéis; ver padrão de `PromptRepository` e `AgentConfigRepository`.

* `RBACRepository`: consulta de papéis por usuário (tabela `user_roles`).

## Serviços e DI

* Em `janus/app/main.py:125-128`, trocar a instância do repositório para `ChatRepositorySQL()` preservando `ChatService`.

* Injeção de sessão: reaproveitar `get_mysql_session()` de `janus/app/db/mysql_config.py:86-94` quando usado em endpoints; no repositório, usar `mysql_db.get_session_direct()` como fallback, seguindo o padrão dos repositórios existentes.

* Inicialização: chamar `init_mysql_database()` no startup para garantir criação das novas tabelas.

## Endpoints API

* Chat (`janus/app/api/v1/endpoints/chat.py`): manter os contratos; adicionar parâmetros obrigatórios/validados para `user_id` quando RBAC ativo.

* Usuários/Perfis: novos endpoints `users.py` e `profiles.py` (CRUD básico), alinhados aos DTOs Pydantic usados nos demais endpoints.

* Segurança mínima: cabeçalho `X-User-Id` ou Bearer (stub) mapeado para `user_id` e validação de acesso nos endpoints de conversa.

## Integração Vetorial (Qdrant)

* Coleções por usuário: `user_{user_id}` ou coleção compartilhada com payloads `{"user_id":..., "session_id":..., "type":"chat_msg"}`.

* No `ChatService.send_message`: após armazenar mensagem, opcionalmente indexar embeddings do texto do usuário/assistente via `embedding_manager` e `vector_store` com `get_or_create_collection` (`janus/app/db/vector_store.py:102-137`).

* Chaves de busca: filtro por `user_id` e proximidade de semântica; preparar para RAG pessoal.

## Observabilidade e RBAC

* Propagar `user_id` e `TRACE_ID` via `CorrelationMiddleware` e métricas de chat; já há contadores e latência em `janus/app/services/chat_service.py:207-271`.

* RBAC básico: no repositório `rename/delete/list`, validar `user_id`/`project_id` como hoje, mas consultando roles quando necessário (`ADMIN` pode bypass).

## Migrações/Bootstrap

* Scripts SQL em `janus/sql/init/` para criar tabelas novas (seguindo padrão de `01_create_config_tables.sql`).

* Garantir `sqlalchemy` e `pymysql` no ambiente; já usados pelos módulos.

## Critérios de Aceitação

* CRUD de usuários/perfis funcional e auditável.

* Conversas e mensagens persistidas com filtros por `user_id/session_id`.

* RBAC básico aplicado em list/rename/delete.

* Indexação vetorial por usuário habilitada (coleção criada e payloads corretos).

* `ChatService` e endpoints existentes continuam operando sem quebra.

## Fases de Entrega

1. Esquema e repositórios SQL (users, profiles, sessions, messages, roles).
2. Troca do `ChatRepository` no DI e manutenção de endpoints de chat.
3. Endpoints de usuários/perfis + RBAC básico.
4. Indexação vetorial por usuário/sessão (MVP).
5. Observabilidade (correlação por `user_id`) e testes.

## Notas de Integração

* Referências úteis: `janus/app/main.py:69-76,125-128,176-199`, `janus/app/db/mysql_config.py:34-59,86-94`, `janus/app/repositories/prompt_repository.py:16-27,74-110`, `janus/app/api/v1/endpoints/chat.py:74-104,118-136`.

* Mantém

