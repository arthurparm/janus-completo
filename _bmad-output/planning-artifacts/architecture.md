---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
  - '_bmad-output/project-context.md'
  - 'docs/api-contracts-front.md'
  - 'docs/api-contracts-janus.md'
  - 'docs/architecture-front.md'
  - 'docs/architecture-janus.md'
  - 'docs/component-inventory-front.md'
  - 'docs/component-inventory-janus.md'
  - 'docs/contribution-guide.md'
  - 'docs/data-models-front.md'
  - 'docs/data-models-janus.md'
  - 'docs/deployment-guide.md'
  - 'docs/development-guide-front.md'
  - 'docs/development-guide-janus.md'
  - 'docs/index.md'
  - 'docs/integration-architecture.md'
  - 'docs/project-overview.md'
  - 'docs/source-tree-analysis.md'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-02-11T22:52:25-03:00'
project_name: 'janus-completo'
user_name: 'Arthur'
date: '2026-02-11T21:49:25-03:00'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
O PRD define 40 FRs em 7 categorias: gestao de tenant/identidade, governanca de acoes/aprovacao, conversa proativa, execucao assistida, integracoes/conectividade, auditoria/compliance/direitos de dados e contratos/administracao operacional. Arquiteturalmente, isso exige fronteiras claras entre contexto de conversa, motor de execucao assistida, politicas de aprovacao e trilha de auditoria por tenant.

**Non-Functional Requirements:**
Ha 23 NFRs mensuraveis com impacto arquitetural direto: seguranca (TLS 1.2+, AES-256, rotacao de segredos), compliance (DSAR com SLA, LGPD/GDPR-ready, SOC2-ready), confiabilidade (SLO/error budget, RTO/RPO, runbooks), estabilidade de integracao (versionamento semantico REST/SSE + contract tests com gate de CI), escalabilidade (3x carga por tenant), observabilidade correlacionavel (tenant/usuario/acao/fluxo) e acessibilidade (WCAG 2.1 AA).

**Scale & Complexity:**
Projeto de alta complexidade com runtime agentico, integracoes externas e requisitos regulatorios/operacionais fortes.

- Primary domain: full-stack SaaS B2B (web + API + workers assincronos)
- Complexity level: enterprise
- Estimated architectural components: ~15 componentes macro (UI, API, stream/chat, politicas/approvals, auditoria, integracoes, workers, observabilidade, dados relacionais e nao relacionais)

### Technical Constraints & Dependencies

Monorepo com frontend Angular 20 e backend FastAPI (Python 3.11), integracao REST/SSE e infraestrutura distribuida (Postgres, Redis, RabbitMQ, Neo4j, Qdrant, observabilidade Prometheus/Grafana/OTEL). Ha dependencia explicita de contratos estaveis para SSE/REST e governanca de mudancas no CI.
Restricoes relevantes ja identificadas na documentacao:
- Isolamento logico obrigatorio por tenant em dados, quotas, auditoria e telemetria.
- Gate de contrato para endpoints criticos REST/SSE.
- Dependencia de SSE com necessidade de reconexao/backoff e monitoramento de saude.
- Risco de drift de schema (SQL legado com sintaxe MySQL vs runtime principal Postgres/SQLAlchemy).
- Necessidade de hardening de configuracao/segredos em ambientes.

### Cross-Cutting Concerns Identified

- Multi-tenancy e segregacao de dados ponta a ponta
- RBAC + politicas de risco + human-in-the-loop para acoes sensiveis
- Auditoria com integridade verificavel e retencao por tier
- Observabilidade operacional com correlacao por tenant/usuario/acao/fluxo
- Governanca de contratos de API/SSE (versionamento, depreciacao, CI gates)
- Resiliencia de integracoes OAuth/quotas e recuperacao guiada
- Acessibilidade e UX operacional em fluxos criticos (WCAG 2.1 AA)

## Starter Template Evaluation

### Primary Technology Domain

Full-stack web monorepo (Angular SPA + FastAPI backend + workers/event-driven infra), baseado na analise de requisitos e no contexto tecnico existente.

### Starter Options Considered

1. Angular CLI starter (oficial) para frontend greenfield
- Pros: padrao oficial, flags atuais e setup previsivel.
- Cons: nao resolve orquestracao de monorepo full-stack por si so.

2. Nx workspace/init (oficial) para monorepo
- Pros: adocao incremental em repositorio existente, task graph, caching, comandos "affected", melhor governanca de build/test em escala.
- Cons: adiciona camada de tooling e convencoes Nx.

3. FastAPI full-stack template (oficial do ecossistema FastAPI)
- Pros: template produtivo bem mantido para full-stack.
- Cons: orientado a stack frontend diferente da atual (nao Angular), gerando desalinhamento com a base ja estabelecida.

### Selected Starter: Nx Incremental Monorepo Init (sobre stack atual)

**Rationale for Selection:**
A melhor decisao arquitetural de "starter" para este projeto ja existente e adotar uma base incremental de orquestracao monorepo sem rebootstrap de frontend/backend. Nx init preserva Angular/FastAPI atuais e melhora governanca de escala (build/test/ci por impacto).

**Initialization Command:**

```bash
npx nx@latest init
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Preserva os runtimes atuais (TypeScript/Angular e Python/FastAPI), sem migracao de linguagem.

**Styling Solution:**
Sem alteracao da stack visual atual (Tailwind + Angular Material).

**Build Tooling:**
Introduz task graph/orquestracao e caching para comandos de build/test/lint com foco em execucao por impacto.

**Testing Framework:**
Mantem Vitest e pytest; a decisao passa a ser orquestrar execucao por targets/projetos afetados.

**Code Organization:**
Mantem a estrutura existente e adiciona governanca de workspace/projeto para evolucao de monorepo.

**Development Experience:**
Melhora feedback em CI/local (affected tasks, padronizacao de comandos, opcao de cache remoto).

**Note:** A inicializacao/adocao Nx deve ser tratada como primeira story de implementacao arquitetural (com rollout incremental e validacao de pipeline).

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Padronizar estrategia de migracao de schema: Alembic como fonte unica de verdade para mudancas estruturais (eliminando drift de SQL manual incompativel).
- Fechar modelo de autenticacao/autorizacao para MVP: tokens padronizados + enforcement tenant-aware + RBAC.
- Padronizar contrato de erro e versao de API/SSE para gates de contrato em CI.
- Definir pipeline CI/CD obrigatorio para front e back com qualidade minima bloqueante.

**Important Decisions (Shape Architecture):**
- Definir ownership de dados entre Postgres/Redis/Neo4j/Qdrant.
- Definir modularizacao de cliente API no frontend para reduzir acoplamento.
- Definir estrategia de observabilidade por fluxo critico (chat stream, produtividade, auditoria).

**Deferred Decisions (Post-MVP):**
- Multi-regiao ativa/ativa.
- Estrategia offline-first completa no frontend.
- Camada API alternativa (ex.: GraphQL) alem de REST/SSE.

### Data Architecture

- **System of record transacional:** PostgreSQL (baseline para novos ambientes: serie 18; minimo suportado em transicao: 16+).
- **Cache e rate limit:** Redis (serie 8.4 estavel recomendada).
- **Broker de tarefas/eventos:** RabbitMQ (serie 4.2 recomendada).
- **Conhecimento relacional/semantico:** Neo4j (linha 5.x).
- **Busca vetorial/memoria:** Qdrant (linha 1.16.x).
- **Modelagem e acesso:** SQLAlchemy 2.x com repositories por dominio.
- **Migracoes:** Alembic-first; `db_migration_service` apenas como compatibilidade temporaria e com plano de descontinuidade.
- **Validacao de dados:** Pydantic no boundary de API + validacoes de dominio na service layer.
- **Caching strategy:** cache read-through para consultas quentes e TTL explicito por dominio.

### Authentication & Security

- **Autenticacao:** token padronizado em formato JWT assinado (fase de transicao com compatibilidade para token legado).
- **Autorizacao:** RBAC alinhado ao PRD (Owner/Admin/Operator/Auditor/Integration Service) com scoping obrigatorio por `tenant_id`.
- **Seguranca de transporte e dados:** TLS 1.2+ em transito, criptografia em repouso, rotacao de segredos/chaves.
- **API security:** middlewares de auth, correlation-id, auditoria obrigatoria em acoes sensiveis.
- **Rate limiting:** token bucket em Redis por IP e por chave.

### API & Communication Patterns

- **Padrao de API:** REST + SSE como contrato canonico.
- **Versionamento:** `/api/v1` com deprecacao controlada e changelog obrigatorio.
- **Contrato de erro:** `application/problem+json` como padrao.
- **Documentacao de API:** OpenAPI como contrato de referencia e base para contract tests.
- **Comunicacao async interna:** RabbitMQ para workloads longos e orquestracao de workers.

### Frontend Architecture

- **State management:** Angular Signals para estado global + RxJS para fluxos assincronos e SSE.
- **Arquitetura de componentes:** manter `core / features / shared` e componentes enxutos.
- **Cliente de API:** quebrar `JanusApiService` por bounded contexts (chat, autonomia, observabilidade, docs, tools).
- **Routing:** rotas lazy-loaded por feature.
- **Performance:** code splitting por dominio e controle de bundle em CI.

### Infrastructure & Deployment

- **Ambientes:** dev com Docker Compose; producao com artefatos containerizados e segregacao de configuracao por ambiente.
- **CI/CD minimo obrigatorio:**
- Front: lint + test + build.
- Back: ruff/black/mypy + pytest + contract tests.
- **Observabilidade:** dashboards por fluxo critico, alertas por SLO/error budget e rastreabilidade por tenant/usuario/acao.
- **Escalabilidade:** API e workers horizontalmente escalaveis; SSE com estrategia de resiliencia e fallback.

### Decision Impact Analysis

**Implementation Sequence:**
1. Autenticacao/autorizacao tenant-aware + auditoria.
2. Normalizacao de migracoes e ownership de dados.
3. Contratos de API/SSE + erro padrao + gates de CI.
4. Refatoracao de cliente API frontend por dominios.
5. Fortalecimento de pipeline CI/CD e observabilidade por SLO.

**Cross-Component Dependencies:**
- RBAC e tenant scoping impactam API, services, repositories e frontend permissions.
- Padrao de erro impacta backend handlers e UX de mensagens no frontend.
- Contract tests impactam governanca de mudanca de endpoints e releases.
- Migracao Alembic impacta deploy, rollback e confiabilidade de schema entre ambientes.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
15 areas where AI agents could make different choices and break compatibility.

### Naming Patterns

**Database Naming Conventions:**
- Tabelas: `snake_case` no plural (`users`, `audit_events`, `tool_daily_usage`).
- Colunas: `snake_case` (`user_id`, `created_at`, `password_hash`).
- Chaves estrangeiras: `<entity>_id` (`user_id`, `session_id`).
- Indices: `idx_<table>_<cols>` (ex.: `idx_users_email`).
- Constraints unicas: `uq_<table>_<cols>` (ex.: `uq_users_email`).

**API Naming Conventions:**
- Prefixo fixo: `/api/v1`.
- Recursos REST: plural e lowercase (`/users`, `/documents`, `/goals`).
- Acoes explicitas: kebab-case (`/start-all`, `/stop-all`) quando nao for CRUD puro.
- Path params: `snake_case` (`{user_id}`, `{conversation_id}`).
- Query/body fields no backend: `snake_case`.
- Headers de correlacao obrigatorios: `X-Request-ID`, `X-User-Id`, `X-Session-Id`, `X-Project-Id`.

**Code Naming Conventions:**
- Python: modulos/funcoes/variaveis em `snake_case`; classes em `PascalCase`.
- Angular:
- services `*.service.ts`
- stores `*.store.ts`
- shared components `*.component.ts`
- features por pasta com trio `feature.ts/html/scss`.
- Evitar criar segundo padrao para o mesmo tipo de artefato.

### Structure Patterns

**Project Organization:**
- Backend: manter fluxo `endpoint -> service -> repository`.
- Frontend: manter fronteiras `core / features / shared / services`.
- Utilitarios compartilhados:
- front: `shared/` ou `core/` conforme escopo
- back: `core/` (infra) ou `services/` (dominio), nunca em endpoint.
- Tarefas longas: sempre via worker/broker, nunca bloqueando request HTTP.

**File Structure Patterns:**
- Testes front co-localizados (`*.spec.ts`).
- Testes backend em `janus/tests/{unit,integration,e2e,smoke,manual}`.
- Docs tecnicas em `docs/`.
- Config de observabilidade/deploy centralizada em `janus/{observability,prometheus,grafana}` e raiz (`docker-compose.yml`).

### Format Patterns

**API Response Formats:**
- Sucesso HTTP: payload tipado direto (Pydantic response model), sem wrappers ad-hoc.
- Erro HTTP padrao alvo: `application/problem+json` com:
- `type`, `title`, `status`, `detail`, `instance`, `code`, `request_id`.
- SSE erro padrao: `{"error":"...","code":"..."}`.

**Data Exchange Formats:**
- JSON backend/API: `snake_case`.
- Datas/horarios: ISO-8601 com timezone.
- Boolean: `true/false`.
- `null` explicito quando campo opcional sem valor.
- Frontend pode mapear para camelCase apenas internamente (na borda do adapter), sem alterar contrato externo.

### Communication Patterns

**Event System Patterns (SSE):**
- Eventos canonicos: `start`, `protocol`, `ack`, `token`, `partial` (compat), `heartbeat`, `done`, `error`.
- Nome de evento: lowercase.
- `protocol` deve anunciar capacidade/versao (ex.: deprecacao de `partial`).
- `done` encerra stream; `error` sempre inclui `code`.

**State Management Patterns:**
- Estado de stream canonico no front: `idle | connecting | open | streaming | retrying | closed | error`.
- Atualizacao de estado: imutavel e previsivel.
- Retry com backoff exponencial + jitter.
- Side-effects de stream encapsulados em service dedicado (`ChatStreamService`).

### Process Patterns

**Error Handling Patterns:**
- Endpoint nao propaga excecao crua: converte para erro de contrato.
- Separar log tecnico de mensagem ao usuario.
- Logs estruturados com correlacao (`request_id`, `user_id`, `session_id`, `project_id`).
- Erros de autorizacao/politica sempre auditados.

**Loading State Patterns:**
- Toda acao assincrona exposta na UI deve ter estado de carregamento explicito.
- Distincao obrigatoria entre `loading inicial` e `retry em andamento`.
- Encerramento de loading sempre em `done` ou `error` (sem estados zumbis).

### Enforcement Guidelines

**All AI Agents MUST:**
- Seguir naming conventions de banco/API/codigo sem excecao local.
- Preservar contratos de headers de correlacao e formato de erro.
- Respeitar fronteiras arquiteturais (`endpoint -> service -> repository`, `core/features/shared`).

**Pattern Enforcement:**
- CI gate obrigatorio: lint + types + tests + contract tests.
- Violacoes de padrao documentadas no PR com plano de ajuste.
- Mudanca de padrao so via atualizacao deste documento + aprovacao tecnica.

### Pattern Examples

**Good Examples:**
- `GET /api/v1/users/{user_id}`
- `{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"...","instance":"/api/v1/...","code":"RateLimitExceeded","request_id":"..."}`
- `event: done` com payload final e fechamento de stream
- `janus/app/services/user_service.py` (regra de negocio fora do endpoint)

**Anti-Patterns:**
- Misturar `userId` e `user_id` no mesmo contrato de API
- Endpoint acessando DB e broker diretamente sem service
- Criar novo formato de erro por endpoint
- Criar stream SSE sem `heartbeat`/`done`/`error`
- Duplicar utilitario em `features/*` quando ja existe em `shared/*`

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
janus-completo/
├── .github/
│   └── workflows/
│       └── action-locaweb.yml
├── _bmad/
├── _bmad-output/
│   ├── planning-artifacts/
│   │   ├── architecture.md
│   │   ├── prd.md
│   │   └── prd-validation-report.md
│   └── project-context.md
├── docs/
│   ├── index.md
│   ├── project-overview.md
│   ├── source-tree-analysis.md
│   ├── integration-architecture.md
│   ├── architecture-front.md
│   ├── architecture-janus.md
│   ├── api-contracts-front.md
│   ├── api-contracts-janus.md
│   ├── data-models-front.md
│   ├── data-models-janus.md
│   ├── component-inventory-front.md
│   ├── component-inventory-janus.md
│   ├── development-guide-front.md
│   ├── development-guide-janus.md
│   ├── deployment-guide.md
│   └── contribution-guide.md
├── front/
│   ├── package.json
│   ├── angular.json
│   ├── tailwind.config.js
│   ├── vitest.config.ts
│   ├── proxy.conf.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── index.html
│   │   ├── environments/
│   │   │   ├── environment.ts
│   │   │   └── environment.prod.ts
│   │   ├── app/
│   │   │   ├── app.routes.ts
│   │   │   ├── app.config.ts
│   │   │   ├── app.ts
│   │   │   ├── core/
│   │   │   │   ├── auth/
│   │   │   │   ├── guards/
│   │   │   │   ├── interceptors/
│   │   │   │   ├── layout/
│   │   │   │   │   ├── header/
│   │   │   │   │   └── sidebar/
│   │   │   │   ├── services/
│   │   │   │   ├── state/
│   │   │   │   └── types/
│   │   │   ├── features/
│   │   │   │   ├── auth/
│   │   │   │   │   ├── login/
│   │   │   │   │   └── register/
│   │   │   │   ├── conversations/
│   │   │   │   ├── home/
│   │   │   │   └── tools/
│   │   │   ├── services/
│   │   │   │   ├── janus-api.service.ts
│   │   │   │   ├── chat-stream.service.ts
│   │   │   │   ├── graph-api.service.ts
│   │   │   │   ├── auto-analysis.service.ts
│   │   │   │   └── ux-metrics.service.ts
│   │   │   └── shared/
│   │   │       ├── components/
│   │   │       ├── pipes/
│   │   │       ├── directives/
│   │   │       └── services/
│   │   └── assets/
│   │       └── i18n/
│   ├── docker/
│   │   └── Dockerfile
│   └── public/
├── janus/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── poetry.lock
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── ollama.Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── exception_handlers.py
│   │   │   ├── problem_details.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── db/
│   │   └── core/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── e2e/
│   │   ├── smoke/
│   │   └── manual/
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── observability/
│   │   └── otel-collector.yaml
│   ├── otel/
│   │   └── otel-collector-config.yaml
│   └── sql/
│       └── init/
│           └── 01_create_config_tables.sql
├── scripts/
├── tests/
│   ├── core/
│   ├── load/
│   └── execution_logs/
├── docker-compose.yml
├── .pre-commit-config.yaml
└── .editorconfig
```

### Architectural Boundaries

**API Boundaries:**
- Entrada externa unica via frontend -> `/api/v1/*` no backend.
- Borda HTTP em `janus/app/api/v1/endpoints/*`.
- Boundary de autenticacao/autorizacao em `core/infrastructure/auth.py` + middlewares + endpoints de auth/users/consents.
- Boundary de erro padrao em `janus/app/api/problem_details.py` e handlers de excecao.

**Component Boundaries:**
- Frontend roteia por feature (`auth`, `conversations`, `tools`, `home`).
- Componentes compartilhados exclusivamente em `front/src/app/shared/components`.
- Estado global transversal em `front/src/app/core/state/global-state.store.ts`.
- Streaming encapsulado em `front/src/app/services/chat-stream.service.ts`.

**Service Boundaries:**
- Contrato obrigatorio: `endpoint -> service -> repository`.
- Processos longos/assincronos somente via `core/workers/*` + broker.
- Orquestracao de agentes isolada em `core/agents/*`.
- Integracoes externas concentradas em services/workers especificos (ex.: produtividade/OAuth).

**Data Boundaries:**
- Postgres (SoR transacional): `models/*` + `repositories/*`.
- Redis: cache/rate-limit/estado efemero.
- RabbitMQ: fila e eventos assincronos.
- Neo4j: relacoes/knowledge graph.
- Qdrant: memoria vetorial/RAG.
- Filesystem/workspace: artefatos de colaboracao e documentos.

### Requirements to Structure Mapping

**Feature/FR Mapping:**
- `Gestao de Tenant e Identidade` -> `front/features/auth/*`, `janus/api/v1/endpoints/{auth,users,profiles}.py`, `janus/services/system_user_service.py`, `janus/models/user_models.py`.
- `Governanca de Acoes e Aprovacao` -> `janus/api/v1/endpoints/{pending_actions,autonomy,productivity}.py`, `janus/core/autonomy/policy_engine.py`, `janus/services/autonomy_service.py`.
- `Conversa Proativa e Assistencia Contextual` -> `front/features/conversations/*`, `front/services/{janus-api,chat-stream}.service.ts`, `janus/api/v1/endpoints/{chat,context,rag,knowledge}.py`, `janus/services/{chat_service,rag_service,memory_service}.py`.
- `Execucao Assistida de Tarefas` -> `front/features/tools/*`, `janus/api/v1/endpoints/{tools,tasks,collaboration,sandbox}.py`, `janus/services/{tool_service,task_service,collaboration_service}.py`, `janus/core/workers/*`.
- `Integracoes e Conectividade` -> `janus/api/v1/endpoints/{productivity,documents,deployment}.py`, `janus/core/workers/google_productivity_worker.py`, `janus/services/document_service.py`.
- `Auditoria, Compliance e Direitos de Dados` -> `janus/api/v1/endpoints/{observability,consents,users}.py`, `janus/services/{observability_service,data_retention_service}.py`, `janus/models/{user_models,consent_models}.py`.
- `Contratos de Produto e Administracao Operacional` -> `janus/api/v1/endpoints/{system_status,system_overview,optimization,evaluation,workspace}.py`, `janus/services/{system_status_service,optimization_service}.py`.

**Cross-Cutting Concerns:**
- Correlacao e tracing -> `core/infrastructure/correlation_middleware.py`.
- Rate limiting -> `core/infrastructure/rate_limit_middleware.py`.
- Contratos de API/erro -> `api/problem_details.py`, `api/exception_handlers.py`.
- Observabilidade -> `janus/prometheus`, `janus/grafana`, `janus/observability`, `janus/otel`.

### Integration Points

**Internal Communication:**
- Front -> backend via `HttpClient` em `janus-api.service.ts`.
- Front streaming -> backend SSE (`/api/v1/chat/stream/{conversation_id}`).
- Backend sync path: endpoint -> service -> repository.
- Backend async path: endpoint/service -> broker -> worker -> persistencia/eventos.

**External Integrations:**
- OAuth Google e produtividade em `productivity` endpoints + worker dedicado.
- LLM providers via `core/llm/*`.
- Infra externa via Redis/RabbitMQ/Postgres/Neo4j/Qdrant.

**Data Flow:**
- Usuario interage na UI -> chamada REST/SSE.
- Backend valida auth/tenant/policies -> executa service/repository ou worker.
- Eventos/metricas/auditoria persistem e retroalimentam observabilidade/UX.

### File Organization Patterns

**Configuration Files:**
- Root: orquestracao geral (`docker-compose.yml`, hooks, CI).
- Front: build/dev/lint/test configs no proprio pacote.
- Janus: runtime/config/deps em `pyproject.toml`, `app/config.py`, configs de observabilidade em pastas dedicadas.

**Source Organization:**
- Front: `core` (infra), `features` (jornadas), `shared` (reuso), `services` (borda API).
- Back: `api` (borda), `services` (dominio), `repositories` (dados), `core` (runtime/plataforma), `models` (contratos e persistencia).

**Test Organization:**
- Front: specs co-localizadas nos componentes/services.
- Back: testes segmentados por nivel em `janus/tests/{unit,integration,e2e,smoke,manual}`.
- Repositorio raiz: testes adicionais de contrato/cenarios transversais.

**Asset Organization:**
- Front: `src/assets` e `public`.
- Back: dashboards/configs em `janus/grafana`, `janus/prometheus`, `janus/observability`, `janus/otel`.

### Development Workflow Integration

**Development Server Structure:**
- Front em `front` com proxy para API.
- Back em `janus` local ou stack docker.

**Build Process Structure:**
- Front build Angular.
- Back packaging Python + compose para infraestrutura.

**Deployment Structure:**
- Workflow atual com deploy de frontend por FTP.
- Estrutura de backend preparada para deploy containerizado e observabilidade integrada.

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
As decisoes sao compativeis entre si: stack Angular + FastAPI + workers + Redis/RabbitMQ + Neo4j/Qdrant + Postgres esta alinhada com o dominio SaaS B2B multi-tenant e com os requisitos de SSE, auditoria e governanca.

**Pattern Consistency:**
Os padroes de naming, estrutura, comunicacao e processos suportam as decisoes arquiteturais e reduzem conflitos entre agentes (endpoint->service->repository, core/features/shared, convencoes de headers e SSE).

**Structure Alignment:**
A estrutura fisica do repositorio suporta os limites arquiteturais definidos, com fronteiras claras entre UI, API, runtime core, dados e observabilidade.

### Requirements Coverage Validation

**Epic/Feature Coverage:**
Sem epicos formais, a cobertura foi feita por categorias de FR com mapeamento explicito para `front` e `janus`.

**Functional Requirements Coverage:**
Cobertura completa das 7 categorias de FR:
- Gestao de Tenant e Identidade
- Governanca de Acoes e Aprovacao
- Conversa Proativa e Assistencia Contextual
- Execucao Assistida de Tarefas
- Integracoes e Conectividade
- Auditoria, Compliance e Direitos de Dados
- Contratos de Produto e Administracao Operacional

**Non-Functional Requirements Coverage:**
Cobertos arquiteturalmente:
- Seguranca (TLS, criptografia, authN/authZ, rate-limit)
- Confiabilidade (SLO/error budget, retries, workers)
- Escalabilidade (separacao sync/async, componentes escalaveis)
- Compliance (auditoria, DSAR, segregacao por tenant)
- Qualidade de contrato (versionamento e testes de contrato)

### Implementation Readiness Validation

**Decision Completeness:**
Decisoes criticas estao documentadas com racional e impacto. Ha transicao planejada para pontos que ainda nao estao plenamente uniformes no codigo atual.

**Structure Completeness:**
Estrutura de projeto suficiente para implementacao orientada por agentes, com limites de integracao e ownership claros.

**Pattern Completeness:**
Padroes cobrem os principais pontos de conflito entre agentes: naming, erro, SSE, estado, localizacao de codigo e fronteiras de camada.

### Gap Analysis Results

**Critical Gaps:**
- Nenhum gap critico bloqueante identificado.

**Important Gaps:**
1. Estrategia de migracao: decisao "Alembic-first" ainda precisa ser materializada no repositorio.
2. Contrato de erro: coexistem formatos diferentes; falta convergencia total para `problem+json`.
3. CI/CD: workflow atual esta centrado em deploy de frontend; faltam gates completos front+back+contract tests.

**Nice-to-Have Gaps:**
- Guia operacional de rollback por dominio.
- Matriz de ownership por diretorio/componente para times/agentes.
- Catalogo de exemplos de payload por endpoint critico.

### Validation Issues Addressed

- Gaps importantes foram convertidos em prioridades explicitas de implementacao inicial.
- Nao ha impedimento arquitetural para avancar; ha necessidades de hardening na fase de execucao.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Contexto de projeto analisado
- [x] Escala e complexidade avaliada
- [x] Restricoes tecnicas identificadas
- [x] Cross-cutting concerns mapeados

**Architectural Decisions**
- [x] Decisoes criticas documentadas
- [x] Stack tecnologica especificada
- [x] Padroes de integracao definidos
- [x] Consideracoes de desempenho enderecadas

**Implementation Patterns**
- [x] Convencoes de nomenclatura definidas
- [x] Padroes de estrutura definidos
- [x] Padroes de comunicacao definidos
- [x] Padroes de processo definidos

**Project Structure**
- [x] Estrutura de diretorios definida
- [x] Boundaries de componentes estabelecidos
- [x] Pontos de integracao mapeados
- [x] Mapeamento requisito->estrutura completo

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** high

**Key Strengths:**
- Alinhamento entre requisitos, decisoes, padroes e estrutura.
- Forte foco em consistencia entre agentes.
- Base robusta para implementacao incremental com governanca.

**Areas for Future Enhancement:**
- Formalizar Alembic e politica de migracao.
- Fechar padronizacao final de erro HTTP.
- Expandir gates de CI/CD para cobertura fim-a-fim.

### Implementation Handoff

**AI Agent Guidelines:**
- Seguir decisoes e padroes deste documento como fonte primaria.
- Respeitar boundaries e convencoes sem excecoes locais.
- Tratar mudancas arquiteturais como alteracao explicita deste artefato.

**First Implementation Priority:**
- Inicializar foundation de monorepo (`npx nx@latest init`) e, em seguida, executar hardening de migracao/erro/CI como trilha inicial.
