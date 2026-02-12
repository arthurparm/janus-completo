# Data Models - Backend (`janus`)

## Visao Geral

O backend usa modelos SQLAlchemy para persistencia relacional e modelos Pydantic para contratos de API e mensagens internas.

## Modelos Relacionais (SQLAlchemy)

### Configuracao e Otimizacao

- `prompts`
- `agent_configurations`
- `optimization_history`

### Usuarios e Sessao

- `users`, `profiles`, `roles`, `user_roles`
- `sessions`, `messages`
- `user_privacy_consents`, `oauth_tokens`, `audit_events`

### Autonomia e Workflow

- `autonomy_runs`, `autonomy_steps`
- `pending_actions`

### Experimentacao e Uso

- `experiments`, `experiment_arms`, `experiment_results`, `experiment_feedback`
- `experiment_assignments`
- `tool_daily_usage`

### Governanca/Qualidade

- `quarantine_items`
- `user_consents` (modelo adicional de consentimento)

## Modelos Pydantic (Contratos)

Em `app/models/schemas.py`:

- `Experience`, `ScoredExperience`, `TaskState`, `TaskMessage`
- enums de grafo e fila (`GraphLabel`, `GraphRelationship`, `QueueName`)
- contratos de status e overview do sistema

## Arquitetura de Dados Complementar

- **Neo4j:** conhecimento relacional/semantico
- **Qdrant:** memoria vetorial
- **Redis:** cache/rate-limit e suporte operacional
- **RabbitMQ:** fila de eventos/tarefas

## Riscos de Schema

`janus/sql/init/01_create_config_tables.sql` contem sintaxe `AUTO_INCREMENT` e trechos em estilo MySQL, divergindo do runtime primario (Postgres + SQLAlchemy). Deve ser revisado para evitar migrações inconsistentes.

---

_Gerado pelo workflow BMAD `document-project`_
