---
title: 'Epic 6 Technical Quick-Spec + Cross-Cutting Enablers'
slug: 'epic-6-contract-governance-and-cross-cutting-enablers'
created: '2026-02-12T14:25:05-03:00'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python 3.11 + FastAPI'
  - 'SQLAlchemy repositories'
  - 'RabbitMQ (aio-pika/aiormq)'
  - 'SSE chat stream'
  - 'Angular 20 + TypeScript'
  - 'Vitest + pytest'
  - 'GitHub Actions (novo gate de contrato)'
files_to_modify:
  - 'janus/app/api/v1/router.py'
  - 'janus/app/api/problem_details.py'
  - 'janus/app/api/exception_handlers.py'
  - 'janus/app/api/v1/endpoints/contracts.py (novo)'
  - 'janus/app/api/v1/endpoints/admin_kpis.py (novo)'
  - 'janus/app/api/v1/endpoints/incidents.py (novo)'
  - 'janus/app/api/v1/endpoints/tasks.py'
  - 'janus/app/api/v1/endpoints/autonomy_history.py'
  - 'janus/app/api/v1/endpoints/pending_actions.py'
  - 'janus/app/services/task_service.py'
  - 'janus/app/services/incidents_service.py (novo)'
  - 'janus/app/repositories/task_repository.py'
  - 'janus/app/repositories/incidents_repository.py (novo)'
  - 'janus/app/repositories/observability_repository.py'
  - 'janus/app/repositories/tool_usage_repository.py'
  - 'janus/app/repositories/autonomy_repository.py'
  - 'janus/app/core/infrastructure/message_broker.py'
  - 'janus/app/services/chat_event_publisher.py'
  - 'janus/app/services/chat_service.py'
  - 'janus/app/services/db_migration_service.py'
  - 'janus/app/models/schemas.py'
  - 'janus/app/models/autonomy_models.py'
  - 'front/src/app/features/tools/tools.ts'
  - 'front/src/app/features/tools/tools.html'
  - '.github/workflows/action-locaweb.yml'
  - '.github/workflows/contract-gates.yml (novo)'
  - '.github/branch-protection.md (novo)'
  - 'contracts/openapi/v1/openapi.yaml (novo)'
  - 'contracts/events/v1/*.json (novo)'
  - 'contracts/sse/v1/chat-stream.events.json (novo)'
  - 'contracts/changelog/v1/*.md (novo)'
  - 'contracts/deprecations/v1/*.yaml (novo)'
  - 'janus/tests/contracts/** (novo)'
  - 'janus/tests/integration/**'
  - 'janus/tests/e2e/**'
  - '_bmad-output/planning-artifacts/requirements-inventory.md'
  - '_bmad-output/planning-artifacts/epic-list.md'
  - '_bmad-output/planning-artifacts/backlog-janus-prioridades.md'
  - '_bmad-output/planning-artifacts/backlog-janus-mapeamento-bmad.md'
  - '_bmad-output/planning-artifacts/sprint-status.yaml (novo)'
code_patterns:
  - 'Backend pattern: endpoint -> service -> repository'
  - 'Erro HTTP parcialmente padronizado em problem+json'
  - 'SSE com protocol/token/partial/done/error e version via env'
  - 'Broker com queue policy validation/reconcile e DLX'
  - 'DTOs/Payloads centralizados em app/models/schemas.py'
  - 'Frontend operacional em features/tools consumindo JanusApiService'
  - 'Nao existe janus/app/schemas; padrao atual concentra DTOs em app/models/schemas.py'
  - 'Somente um workflow CI hoje: action-locaweb.yml (deploy front)'
test_patterns:
  - 'pytest integration com TestClient para SSE/API'
  - 'e2e API tests para health/chat'
  - 'ausencia de suite dedicada de contract tests REST/SSE/eventos'
  - 'ausencia de gate CI bloqueante para breaking change de contrato'
---

# Tech-Spec: Epic 6 Technical Quick-Spec + Cross-Cutting Enablers

**Created:** 2026-02-12T14:25:05-03:00

## Overview

### Problem Statement

Falta uma especificacao tecnica unificada para implementar o Epic 6 (FR37-FR40) com governanca de contratos versionados para REST, eventos de dominio (RabbitMQ) e SSE, incluindo deprecacao controlada, auditoria operacional por tenant, incidentes com rastreabilidade e gates de contrato no CI. Alem disso, os enablers transversais JNS-001/002/003/006 ainda nao estao formalizados no backlog tecnico de execucao.

### Solution

Definir um plano tecnico incremental, backend-first, com source of truth de contratos em `contracts/` (OpenAPI + schemas versionados de eventos/SSE), padrao `problem+json`, endpoint dedicado de incidentes (`/api/v1/incidents`), baseline de KPIs administrativos por tenant e formalizacao dos enablers cross-cutting de qualidade documental e cadencia BMAD multi-agente.

### Scope

**In Scope:**
- Epic 6 completo (Stories 6.1, 6.2, 6.3, 6.4).
- Enablers cross-cutting JNS-001, JNS-002, JNS-003, JNS-006.
- Contratos versionados para REST + RabbitMQ + SSE.
- Janela padrao de deprecacao de contrato: 90 dias.
- Story 6.2 em modo MVP backend-first (API + modelo de dados + changelog/deprecacao).
- Story 6.3 com KPIs minimos MVP por tenant:
  - volume de requests
  - taxa de sucesso/erro por capability
  - p95 de latencia por endpoint critico
  - aprovacoes de risco pendentes/concluidas
  - incidentes abertos por severidade
  - consumo de quota
- Story 6.4 com recurso dedicado `/api/v1/incidents` e links para `tasks` e `autonomy_history`.
- Gate de CI bloqueando breaking change REST/SSE e inconsistencias de `problem+json`.

**Out of Scope:**
- UI avancada no MVP (filtros complexos, drill-down pesado, analytics avancado).
- Mudancas de produto fora de Epic 6 + enablers JNS-001/002/003/006.
- Replataformizacao completa de componentes existentes sem necessidade de contrato/governanca.

## Context for Development

### Codebase Patterns

- Backend segue fronteira `endpoint -> service -> repository`.
- Frontend segue `core / features / shared`.
- Contrato de API em `/api/v1`; hoje ha inconsistencia entre handlers (`problem+json` em `problem_details.py` vs `{"detail": ...}` em `exception_handlers.py`).
- Observabilidade com correlacao e trilha auditavel por fluxo critico.
- `tasks` endpoint ja opera com negociacao `application/json` e `application/msgpack`.
- Broker RabbitMQ ja possui primitives para publish/subscribe, DLX e reconciliacao de politicas de fila.
- SSE de chat ja possui metadados de protocolo/versionamento e teste de integracao (`event: protocol`, `event: token`, `event: done`).
- Nao existe pasta `contracts/` no estado atual (gap para source of truth confirmado no escopo).
- Nao existe `janus/app/schemas`; DTOs/request/response estao hoje centralizados em `janus/app/models/schemas.py`.
- CI atual tem apenas workflow de deploy front (`.github/workflows/action-locaweb.yml`), sem lint/test/contract gates.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `_bmad-output/planning-artifacts/prd.md` | FR37-FR40 e NFRs de contrato/compliance/observabilidade |
| `_bmad-output/planning-artifacts/epics/epic-6-contratos-de-produto-e-administrao-operacional.md` | Stories 6.1-6.4 e ACs base |
| `_bmad-output/planning-artifacts/architecture.md` | Decisoes arquiteturais e padroes de contrato/gate CI |
| `_bmad-output/planning-artifacts/backlog-janus-prioridades.md` | Backlog JNS priorizado |
| `_bmad-output/planning-artifacts/backlog-janus-mapeamento-bmad.md` | Mapeamento JNS -> Epics/Stories |
| `janus/app/api/problem_details.py` | Implementacao atual de `application/problem+json` |
| `janus/app/api/exception_handlers.py` | Mapeamento atual de excecoes (formato de erro divergente) |
| `janus/app/api/v1/endpoints/tasks.py` | Vinculo com execucao operacional e RabbitMQ |
| `janus/app/api/v1/endpoints/autonomy_history.py` | Vinculo com historico operacional/autonomia |
| `janus/app/repositories/task_repository.py` | Repositorio de tasks assincronas |
| `janus/app/repositories/autonomy_repository.py` | Persistencia de runs/steps operacionais |
| `janus/app/core/infrastructure/message_broker.py` | Infra de eventos RabbitMQ (publish/subscribe, DLX, policy reconcile) |
| `janus/app/services/chat_event_publisher.py` | Publicacao de eventos em exchange `janus.events` |
| `janus/app/models/schemas.py` | DTOs e enums (TaskMessage, QueueName etc.) |
| `janus/tests/integration/test_chat_sse.py` | Padrao de teste de SSE (`protocol/token/done`) |
| `janus/tests/e2e/test_api_endpoints.py` | Padrao de testes e2e de endpoints API |
| `front/src/app/features/tools/tools.ts` | Tela operacional/admin atual para metricas/eventos/aprovacoes |
| `front/src/app/features/tools/tools.html` | Renderizacao atual de cards e tabela de auditoria |
| `.github/workflows/action-locaweb.yml` | Pipeline CI/CD atual (deploy front, sem gate de contrato) |

### Technical Decisions

- Source of truth de contratos confirmado em `contracts/`:
  - OpenAPI versionado (REST)
  - schemas versionados de eventos (RabbitMQ)
  - schemas versionados de payload/eventos SSE
- Semver obrigatorio para contratos e politica de deprecacao com janela minima de 90 dias.
- Padrao de erro `application/problem+json` com consistencia de campos obrigatorios (`type`, `title`, `status`, `detail`, `instance`, `trace_id`).
- Story 6.2 sera backend-first no MVP (API + dados de changelog/deprecacao), sem tela completa neste ciclo.
- Story 6.3 sera entregue no MVP com KPIs minimos por tenant via API e composicao multi-fonte (observabilidade, quota, aprovacoes e incidentes).
- Story 6.4 cria recurso dedicado `/api/v1/incidents` com referencias cruzadas para tasks e autonomia (`run_id`, `task_id`, `autonomy_step_id`).
- Gate CI bloqueante para breaking change REST/SSE e inconsistencias de `problem+json`, com check obrigatorio para merge.
- Fluxos sensiveis devem cobrir casos negativos: expiracao de aprovacao, concorrencia de aprovacao, idempotencia e rollback explicito.
- Enablers JNS-001/002/003/006 entram no mesmo quick-spec em trilha separada, com entrega incremental e auditavel.

### Architecture Decision Records

- ADR-001 (Accepted): `contracts/` e a fonte canonica de contratos (REST/SSE/eventos). Toda mudanca contratual exige atualizacao de artefatos versionados e validacao no contract gate.
- ADR-002 (Accepted): Toda resposta de erro HTTP deve sair em `application/problem+json` via builder unico compartilhado.
- ADR-003 (Proposed - MVP incremental): Introduzir `tenant_id` nas entidades operacionais criticas com estrategia de compatibilidade durante migracao.
- ADR-004 (Accepted): Recurso de incidentes deve respeitar padrao `endpoint -> service -> repository` com modelo e migracao dedicados.
- ADR-005 (Accepted): KPIs administrativos devem ser compostos por multiplas fontes (observability/tool-usage/autonomy/pending-actions/incidents), nao por um unico repositorio.
- ADR-006 (Accepted): Contract gate deve ser efetivamente bloqueante em PR por status check obrigatorio (alem da existencia do workflow).
- ADR-007 (Accepted): Hardening de fluxos sensiveis (expiracao, concorrencia, idempotencia, compensacao) deve ter tasks explicitas e testes dedicados.

## Implementation Plan

### Tasks

#### Core - Epic 6 (FR37-FR40)

- [ ] Task 1: Criar source of truth versionado para contratos REST/eventos/SSE
  - File: `contracts/openapi/v1/openapi.yaml`
  - Action: Consolidar especificacao OpenAPI v1 dos endpoints criticos (chat, tasks, autonomy_history, incidents).
  - Notes: Incluir metadados de versao e compatibilidade.
- [ ] Task 2: Definir schemas versionados de eventos RabbitMQ e SSE
  - File: `contracts/events/v1/task-events.schema.json`
  - Action: Declarar payloads de eventos de dominio e regras de compatibilidade backward.
  - Notes: Cobrir campos obrigatorios de correlacao (`tenant_id`, `run_id`, `trace_id`).
- [ ] Task 3: Definir contrato SSE de chat/progresso
  - File: `contracts/sse/v1/chat-stream.events.json`
  - Action: Formalizar eventos `protocol`, `token`, `partial`, `done`, `error` com campos e tipos.
  - Notes: Versionar protocolo SSE separado do OpenAPI.
- [ ] Task 4: Expor metadados de versao de contrato nos endpoints/eventos existentes
  - File: `janus/app/services/chat_service.py`
  - Action: Incluir metadados de versao de protocolo nos eventos de stream quando aplicavel.
  - Notes: Nao quebrar clientes atuais; manter backward compatibility.
- [ ] Task 5: Padronizar erro HTTP em `application/problem+json`
  - File: `janus/app/api/exception_handlers.py`
  - Action: Substituir respostas `{"detail": ...}` por builder central de problem details.
  - Notes: Reutilizar utilitario de `janus/app/api/problem_details.py`.
- [ ] Task 6: Reforcar contrato de erros e validacao central
  - File: `janus/app/api/problem_details.py`
  - Action: Garantir campos obrigatorios e factory unica para todos os handlers.
  - Notes: Alinhar status e mensagens para logs/auditoria.
- [ ] Task 7: Implementar portal backend-first de changelog/deprecacao (Story 6.2)
  - File: `janus/app/api/v1/endpoints/contracts.py` (novo)
  - Action: Criar endpoints para listar versoes, changelog, suporte e deprecacao com janela de 90 dias.
  - Notes: Persistencia pode iniciar em arquivo/DB simples com trilha auditavel.
- [ ] Task 8: Registrar endpoint no roteador principal
  - File: `janus/app/api/v1/router.py`
  - Action: Incluir novo router de contratos e deprecacao na API v1.
  - Notes: Garantir consistencia com modo full/minimal API.
- [ ] Task 9: Entregar API de KPIs administrativos por tenant (Story 6.3)
  - File: `janus/app/api/v1/endpoints/admin_kpis.py` (novo)
  - Action: Expor KPIs MVP: requests por tenant, sucesso/erro por capability, p95 latencia endpoint critico, aprovacoes pendentes/concluidas, incidentes por severidade, consumo de quota por tenant.
  - Notes: Filtros por tenant e periodo obrigatorios.
- [ ] Task 10: Implementar composicao de KPIs em camada de repositorios especializados
  - File: `janus/app/repositories/observability_repository.py`
  - Action: Consolidar consultas de latencia/sucesso por endpoint e correlacoes de uso operacional.
  - Notes: Evitar N+1 e garantir particionamento por tenant.
- [ ] Task 11: Integrar quota e uso por tenant no calculo de KPIs
  - File: `janus/app/repositories/tool_usage_repository.py`
  - Action: Expor agregacoes de consumo por tenant para dashboard administrativo.
  - Notes: Padronizar janela temporal com os demais KPIs.
- [ ] Task 12: Criar recurso dedicado de incidentes (Story 6.4)
  - File: `janus/app/api/v1/endpoints/incidents.py` (novo)
  - Action: Implementar CRUD minimo (create/list/get/update status) em `/api/v1/incidents`.
  - Notes: Campos minimos: severidade, capability, impacto, responsavel, status, `run_id`/`task_id`/`autonomy_step_id`.
- [ ] Task 13: Criar camada de servico de incidentes
  - File: `janus/app/services/incidents_service.py` (novo)
  - Action: Centralizar regras de negocio, validacoes de status e correlacao com trilhas operacionais.
  - Notes: Manter endpoint fino, seguindo padrao do projeto.
- [ ] Task 14: Criar camada de repositorio de incidentes
  - File: `janus/app/repositories/incidents_repository.py` (novo)
  - Action: Implementar acesso a dados para incidents com filtros por tenant/status/severidade.
  - Notes: Preparar consultas para timeline de resposta.
- [ ] Task 15: Persistencia e modelo de incidentes
  - File: `janus/app/models/autonomy_models.py`
  - Action: Adicionar modelo SQLAlchemy de incidente e relacionamentos basicos com rastreabilidade operacional.
  - Notes: Indexar por tenant, severidade, status e created_at.
- [ ] Task 16: Evoluir migracao de schema para incidentes e tenant_id incremental
  - File: `janus/app/services/db_migration_service.py`
  - Action: Criar checks e migracao idempotente para tabela/indexes de incidents e colunas de isolamento por tenant quando aplicavel.
  - Notes: Prever estrategia backward-compatible durante transicao.
- [ ] Task 17: Integrar eventos de incidentes no broker
  - File: `janus/app/services/chat_event_publisher.py`
  - Action: Publicar eventos de incidente criado/atualizado com routing key versionada e campos de correlacao.
  - Notes: Garantir fallback preservado e rastreabilidade de erro.
- [ ] Task 18: Ajuste MVP no front operacional para consumo de KPIs/incidentes
  - File: `front/src/app/features/tools/tools.ts`
  - Action: Consumir endpoints backend-first de KPIs/incidentes em modo basico (cards/tabela), sem analytics avancado.
  - Notes: Manter layout atual; sem filtros complexos no MVP.
- [ ] Task 19: Exibir estados explicitos e evidencias no painel de operacao
  - File: `front/src/app/features/tools/tools.html`
  - Action: Exibir status `pending/in_progress/completed/failed`, `run_id`, severidade e proximo passo.
  - Notes: Priorizar clareza de risco e feedback confiavel.
- [ ] Task 20: Criar suite de contract tests REST/SSE/eventos
  - File: `janus/tests/contracts/test_rest_contracts.py` (novo)
  - Action: Validar resposta contra OpenAPI e `problem+json`.
  - Notes: Falha bloqueante para breaking change.
- [ ] Task 21: Criar testes de contrato SSE
  - File: `janus/tests/contracts/test_sse_contracts.py` (novo)
  - Action: Validar eventos e payloads SSE contra schema versionado.
  - Notes: Cobrir ordem minima (`protocol` antes de `token`, `done` terminal).
- [ ] Task 22: Criar testes de contrato de eventos RabbitMQ
  - File: `janus/tests/contracts/test_event_contracts.py` (novo)
  - Action: Validar payloads publicados no broker contra schemas `contracts/events/v1`.
  - Notes: Cobrir headers de correlacao e versionamento.
- [ ] Task 23: Implementar gate CI bloqueante para contrato
  - File: `.github/workflows/contract-gates.yml` (novo)
  - Action: Pipeline de lint/test/contract com bloqueio de merge em breaking REST/SSE ou violacao de `problem+json`.
  - Notes: `action-locaweb.yml` permanece para deploy; novo workflow e obrigatorio para qualidade.
- [ ] Task 24: Tornar contract gate obrigatorio no fluxo de merge
  - File: `.github/branch-protection.md` (novo)
  - Action: Documentar e exigir status check obrigatorio de `contract-gates` para merges em branch principal.
  - Notes: Sem check obrigatorio, o gate nao e efetivamente bloqueante.
- [ ] Task 25: Hardening de aprovacao sensivel expirada e concorrente
  - File: `janus/app/api/v1/endpoints/pending_actions.py`
  - Action: Implementar validacao explicita de expiracao e conflito de aprovacao concorrente para mesma acao.
  - Notes: Respostas com causa + proximo passo em formato previsivel.
- [ ] Task 26: Hardening de idempotencia e compensacao/rollback
  - File: `janus/app/services/task_service.py`
  - Action: Introduzir chave de idempotencia para acoes sensiveis e trilha de compensacao quando houver falha parcial.
  - Notes: Registrar evidencias em trilha auditavel.

#### Cross-Cutting Enablers - JNS-001/002/003/006

- [ ] Task 27: JNS-001 - Sanitizar artefatos de planejamento e shards
  - File: `_bmad-output/planning-artifacts/requirements-inventory.md`
  - Action: Corrigir encoding para UTF-8 canonico e remover duplicacoes estruturais (ex.: heading repetido).
  - Notes: Meta zero ocorrencias de caracteres mojibake nos artefatos canonicos.
- [ ] Task 28: JNS-001 - Limpar template residual de epics
  - File: `_bmad-output/planning-artifacts/epic-list.md`
  - Action: Remover comentarios de template e garantir documento consumivel downstream.
  - Notes: Arquivo deve ficar pronto para parsing automatizado.
- [ ] Task 29: JNS-002 - Mapear rastreabilidade FR/NFR por story
  - File: `_bmad-output/planning-artifacts/backlog-janus-mapeamento-bmad.md`
  - Action: Adicionar matriz `Story -> FR -> NFR` com owner e status de cobertura.
  - Notes: NFRs criticos devem estar explicitamente ancorados em stories.
- [ ] Task 30: JNS-003 - Tornar ACs criticos mensuraveis
  - File: `_bmad-output/planning-artifacts/backlog-janus-prioridades.md`
  - Action: Reescrever ACs vagos (`rapido`, `seguro`, `claro`) para metas operacionais verificaveis.
  - Notes: Cada AC precisa de metrica, limite e evidencia esperada.
- [ ] Task 31: JNS-006 - Formalizar cadencia BMAD multi-agente
  - File: `_bmad-output/planning-artifacts/sprint-status.yaml` (novo)
  - Action: Definir DoR/DoD, handoffs por papel (PM, Architect, Dev, QA, UX, SM) e checkpoints de aprovacao.
  - Notes: Usar formato executavel para status de sprint e auditoria de fluxo.
- [ ] Task 32: JNS-006 - Governar handoffs no fluxo de entrega
  - File: `_bmad-output/planning-artifacts/implementation-readiness-report.md` (novo)
  - Action: Documentar gate de entrada/saida por historia com evidencias obrigatorias e responsavel.
  - Notes: Deve ser atualizado a cada sprint review.

### Acceptance Criteria

#### Core - Epic 6

- [ ] AC 1: Given um contrato REST/SSE/evento novo, when ele e publicado em `contracts/`, then ele possui semver valida e status de suporte registrado.
- [ ] AC 2: Given uma mudanca breaking REST ou SSE sem compatibilidade, when o pipeline de contrato roda no PR, then o merge e bloqueado com motivo explicito.
- [ ] AC 3: Given uma resposta de erro de servico (400/404/408/500), when a API responde, then o `content-type` e `application/problem+json` e os campos obrigatorios estao presentes.
- [ ] AC 4: Given uma versao marcada para deprecacao, when o consumidor consulta o endpoint de changelog, then recebe data de fim de suporte com janela minima de 90 dias.
- [ ] AC 5: Given uma consulta de dashboard admin por tenant e periodo, when a API responde, then retorna os 6 KPIs MVP definidos no escopo com valores numericos.
- [ ] AC 6: Given dados multi-tenant, when um admin consulta KPIs de tenant A, then nenhum dado de tenant B aparece no payload.
- [ ] AC 7: Given criacao de incidente em `/api/v1/incidents`, when o registro e salvo, then inclui severidade, capability, impacto, responsavel e pelo menos um vinculo (`run_id` ou `task_id` ou `autonomy_step_id`).
- [ ] AC 8: Given um incidente aberto, when o status e atualizado, then a timeline registra quem mudou, quando mudou e qual foi a justificativa.
- [ ] AC 9: Given stream SSE de chat, when a sessao inicia, then `event: protocol` e emitido antes de `event: token` e `event: done` encerra a stream sem estado ambiguo.
- [ ] AC 10: Given publicacao de evento RabbitMQ, when o publisher envia payload, then o evento valida contra schema versionado e inclui `trace_id` e identificador de tenant.

#### Hardening de fluxos sensiveis

- [ ] AC 11: Given uma aprovacao sensivel expirada, when o usuario tenta executar a acao, then a execucao e bloqueada com erro explicito e proximo passo claro.
- [ ] AC 12: Given duas aprovacoes concorrentes para a mesma acao, when a segunda chega apos a primeira confirmacao, then o sistema responde conflito e nao duplica execucao.
- [ ] AC 13: Given repeticao de requisicao com a mesma chave de idempotencia, when a segunda chamada chega, then o sistema retorna mesmo resultado logico sem novo efeito externo.
- [ ] AC 14: Given falha parcial apos efeito externo, when o fluxo entra em compensacao, then rollback (ou acao compensatoria) fica registrado na trilha de auditoria.

#### Cross-Cutting Enablers

- [ ] AC 15: Given os artefatos de planejamento atuais, when a sanitizacao e concluida, then nao existe ocorrencia de caracteres mojibake nos arquivos canonicos.
- [ ] AC 16: Given o inventario de requisitos e epics, when a validacao estrutural roda, then nao existem headings duplicados nem comentarios de template residual.
- [ ] AC 17: Given uma story P0/P1, when ela entra no sprint, then ha mapeamento explicito para FR e NFR com owner e status.
- [ ] AC 18: Given stories criticas (riscos medio/alto), when QA revisa os ACs, then todos estao em formato mensuravel com threshold objetivo.
- [ ] AC 19: Given inicio da sprint, when o time atualiza `sprint-status.yaml`, then cada historia possui estado, responsavel, DoR/DoD e evidencia de handoff.
- [ ] AC 20: Given transicao entre agentes BMAD, when ocorre handoff, then o checklist de governanca registra entrada, saida e aprovacao do proximo owner.

## Additional Context

### Dependencies

- FastAPI e estrutura atual de API v1 para novos routers (`contracts`, `admin_kpis`, `incidents`).
- SQLAlchemy models + `db_migration_service.py` para evolucao de schema sem quebrar ambiente existente.
- RabbitMQ (exchange/queue) com `message_broker.py` e publisher atual para eventos de dominio.
- Suite de testes `pytest` com nova pasta `janus/tests/contracts`.
- GitHub Actions com novo workflow bloqueante de contrato (`contract-gates.yml`).
- Artefatos de planejamento BMAD para enablers JNS-001/002/003/006.

### Testing Strategy

- Unit tests:
  - builders/validators de problem+json.
  - serializacao/validacao de contratos REST/SSE/eventos.
  - regras de expiracao, concorrencia e idempotencia.
- Integration tests:
  - endpoints `contracts`, `admin_kpis`, `incidents` com banco real de teste.
  - fluxo de eventos RabbitMQ publicado/consumido com schema check.
  - SSE stream com ordem de eventos e payload versionado.
- Contract tests:
  - OpenAPI diff (baseline vs PR) com bloqueio de breaking.
  - validacao `application/problem+json` em erros mapeados.
  - validacao de schema de eventos e SSE no CI.
- Manual tests:
  - criar incidente, atualizar status e verificar trilha.
  - consultar changelog/deprecacao para versao near-EOL.
  - validar KPI por tenant com dados de tenants distintos.

### Notes

- Risco alto atual: inconsistencia entre handlers de erro e ausencia de gate CI de contrato.
- Risco alto atual: source of truth `contracts/` ainda inexistente; deve ser a primeira entrega tecnica.
- Story 6.2 fica backend-first por decisao explicita; UI completa permanece fora do MVP.
- Nao existe pipeline CI adicional alem de `action-locaweb.yml`; o quick-spec assume criacao obrigatoria de workflow novo para qualidade.
- Este spec incorpora enablers JNS-001/002/003/006 no mesmo plano, mas com trilha separada para evitar acoplamento indevido do core tecnico.


