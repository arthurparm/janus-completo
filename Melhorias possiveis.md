# 🗺️ Janus Roadmap & Technical Debt (2026)

Este documento centraliza o planejamento estratégico, dívidas técnicas e inovações futuras do Janus.
> *Última atualização: 12/01/2026 (Pós-Auditoria de Infraestrutura)*

## 🚦 Strategic Execution Phases

### Fase 1: Foundation & Security (Imediato / P0)

*Foco: Estabilidade fiduciária, segurança de dados e fundação para escala.*

- [x] **Migração MySQL → PostgreSQL (pgvector)** 🚨
  - *Motivo*: MySQL atual bloqueia analytics de JSON e vector search nativo. Sem JSONB indexável e arrays.
  - *Ação*: Migrar dados, ativar `pgvector` e `pg_trgm`.
- [x] **Redis State Backend (RateLimit & Pricing)** 🚨
  - *Motivo*: Contadores de custo em memória zeram no restart; risco financeiro e de bloqueio de API.
  - *Ação*: Implementar `RedisUsageTracker` para persistência atômica.
- [x] **Configuration Hot-Reload**
  - *Motivo*: Alterar flags/timeouts exige restart (downtime). `AppSettings` é imutável.
  - *Ação*: Implementar `DynamicConfigManager` que observa Redis/File.
- [ ] **Security Headers & Sanitization**
  - *Motivo*: Vulnerabilidades web básicas abertas.
  - *Ação*: Middleware de headers (CSP, HSTS) e sanitização de output consistente.
- [ ] **Prompt Injection Risk**: `PolicyEngine` não sanitiza o *conteúdo* de prompts de planejamento.
- [ ] **Data Retention & Purge Policy**: Não há política automatizada de expiração/anonimização para conversas, logs e metadados antigos (GDPR).
- [ ] **PII em Logs**: Logs podem conter PII. Falta redaction/masking centralizado em middleware.
- [ ] **Audit Log Imutável**: Ações administrativas críticas não são registradas de forma imutável.
- [ ] **Secret Rotation Policy**: Chaves de API e segredos não têm política formal de rotação sem downtime.
- [ ] **Dependency Audit**: Auditoria em `package.json` e `requirements.txt` pendente.

### Fase 2: The "Brain" Upgrade (Curto Prazo / P1)

*Foco: Respalda a inteligência do sistema com memória e busca de nova geração.*

- [x] **Neo4j Vector Index & GraphRAG**
  - *Gaps*: Vector Search ausente, GraphRAG básico, Hybrid Search incompleto.
  - *Ação*: Ativar index vetorial e queries híbridas (Graph + Vector + Text).
- [ ] **LLM Streaming (UX/DX)**
  - *Motivo*: Chat síncrono parece "travado" para o usuário.
  - *Ação*: Endpoint SSE `/chat/stream` com renderização progressiva e `async def astream()`.
- [x] **Qdrant Optimization (Quantization)**
  - *Gaps*: RAM usage alto (float32), HNSW defaults subótimos, Sem caching de embeddings.
  - *Ação*: Ativar Binary Quantization e Scalar Quantization (INT8).
- [x] **DeepSeek Reasoning Integration (R1)**
  - *Motivo*: Custo irrisório para inteligência superior em planejamento.
  - *Ação*: Novo node `ThinkerAgent` antes do `CoderAgent`.

### Fase 3: Scale & Operations (Médio Prazo / P2)

*Foco: Observabilidade, CI/CD e robustez operacional.*

- [ ] **Observabilidade Distribuída (Tracing)**
  - *Ação*: Propagar `trace_id` via RabbitMQ headers (API → Worker).
- [ ] **Automated A/B Testing**
  - *Ação*: Framework para comparar performance de modelos em prod.
- [ ] **Cost Anomaly Detection**
  - *Ação*: `CostSentinel` para detectar loops de gastos infinitos (> 5σ spikes).
- [ ] **RabbitMQ Resilience**
  - *Ação*: DLX não configurado por padrão, Backpressure ausente, Poison Pill sem alerta.
- [ ] **Distributed Rate Limiting**: Migrar de memória local para Redis.
- [ ] **Detecção de Drift entre Ambientes**: Detectar divergências de config entre dev/stage/prod.
- [ ] **Migration System**: Migrar de `db_migration_service.py` para **Alembic**.

### Fase 4: Innovation & Vision (Longo Prazo / P3)

*Foco: SOTA (State of the Art) e diferenciais competitivos.*

- [ ] **Self-Hosted Imitation Learning**: Treinar modelo "Janus-7B-LoRA" com base em logs de melhores planos.
- [ ] **Multi-Modal Memory**: Grafo e Vetores armazenando embeddings de imagens e voz.
- [ ] **Multi-Modal LLM Support**: Suporte a modelos de visão/áudio no router.
- [ ] **Autonomous TDD Agent**: Agente que escreve testes *antes* do código.
- [ ] **Speculative Decoding**: Usar Qwen local para rascunhar e V3 para verificar.

---

## 🏗️ Detailed Backlog by Domain

### 🧠 Autonomia & LLM Orchestration

- [ ] **Agent "Hardcoded Minds"**: Extrair prompts hardcoded para templates/DB.
- [ ] **Policy-Aware Planning**: Planner deve consultar `PolicyEngine` (budget/segurança) antes de gerar planos.
- [ ] **Batch Processing Support**: Usar OpenAI Batch API para tarefas offline (-50% custo).
- [ ] **Forecasting de Tokens**: Melhorar EMA para separar Input/Output tokens (precisão de custo).
- [ ] **Fallback Chain Configurável**: Definir cadeia de failover (ex: GPT-4 -> Claude -> Local) via config.
- [ ] **Métricas de Sucesso por Objetivo**: Atribuir métricas de sucesso/fracasso por tipo de goal.
- [ ] **Exploration Bias**: Implementar decay dinâmico em `LLM_EXPLORATION_PERCENT`.
- [ ] **Multi-Armed Bandit**: Implementar UCB1/Thompson Sampling para seleção de modelos.
- [ ] **Model Quality Metrics**: Score de seleção considerando qualidade (retry rate, feedback).
- [ ] **Cache Warming**: Pré-carregar cache com queries frequentes pós-restart.
- [ ] **Quota Consumption Visibility**: Endpoint para ver consumo de quotas em tempo real.
- [ ] **Quota Alerts**: Alertas quando budget mensal atinge thresholds (50%, 80%).

### 🎨 Frontend & UX (Angular)

- [x] **State Management Moderno**: Migrar `janus-api.service.ts` para **Angular Signals**.
- [x] **Components Refactor**: Quebrar God Components (`conversations.ts` +800 lines).
- [x] **Graph Visualization**: Adicionar Cytoscape.js para visualizar o "cérebro" (Neo4j) na UI.
- [x] **Budget UI**: Painel para usuário ver consumo de quota/custo em tempo real.
- [x] **Accessibility (A11y)**: Landmarks ARIA, keyboard navigation, empty states, adicionar `<main>`.
- [x] **RxJS Anti-patterns**: Eliminar "subscribe inside subscribe".
- [ ] **Feedback de Erros Invisível**: Adicionar `<app-notification-banner>`.
- [ ] **Feedback de Carregamento**: Padronizar Skeleton Loaders.
- [ ] **Internacionalização**: Implementar `@ngx-translate`.
- [ ] **Atalhos de Teclado**: UI power-user flows.
- [ ] **Sem UI para Parlamento**: Visualização de `TaskState` e agentes ativos.
- [ ] **Sem UI para Poison Pills**: Visualização de mensagens mortas/erros.
- [ ] **Modo Read-Only Operacional**: UI para janelas de manutenção.
- [ ] **Fallback de Auto-Analysis**: Evitar "Happy Path" falso vindo de mocks.

### 🛡️ Backend & Infraestrutura

- [ ] **ChatService Refactor**: Quebrar monolito (+1600 linhas).
- [ ] **Loose Typing**: Migrar `Dict[str, Any]` para Pydantic Models.
- [ ] **Weak Testing Patterns**: Substituir repositórios reais por Mocks em unit tests.
- [ ] **Cross-Cutting Concerns**: Centralizar logging, tracing, metrics.
- [ ] **Config Sprawl**: Centralizar configs espalhadas e limpar feature flags.
- [ ] **Feature Flags Ausentes**: Toggles seguros por ambiente.
- [ ] **Auto-Analysis Real**: Conectar a métricas reais de gatilho (ObservabilityService).
- [ ] **Persistência de Métricas UX**: Armazenar `UxMetricItem` em banco.
- [ ] **Tooling Modernization**: Migrar `poetry` para `uv`.
- [ ] **Orquestração WebRTC**: Sinalização backend para pareamento.
- [ ] **Model Context Protocol (MCP)**: Pesquisar adoção para tools externas.

### 🔄 Parlamento (Multi-Agent System)

- [ ] **Planner Hardcoded no Router**: `_infer_first_agent` ignora plano gerado.
- [ ] **Circuit Breakers**: Impedir loops infinitos entre agentes (Coder <-> Professor).
- [ ] **Task State Validation**: Usar Enums rigorosos para transições de estado.
- [ ] **Parlamento sem timeout global**: Tarefas presas indefinidamente.
- [ ] **History bloat no TaskState**: Limitar crescimento do histórico.
- [ ] **Meta-Agent integration**: Meta-agent cego para métricas do Parlamento.
- [ ] **Hardcoded Logic no Coder**: Heurística de complexidade fixa.
- [ ] **Idempotência**: Garantir que workers possam reprocessar mensagens.
- [ ] **Replay & Re-run**: Mecanismo para reprocessar `TaskState` de checkpoint.
- [ ] **Human-in-the-Loop**: Configurar aprovação manual para ações críticas.

### 📦 Knowledge, Data & Messaging

- [ ] **RabbitMQ Gaps**:
  - Distributed Tracing incompleto.
  - Queue Metrics limitados.
  - Sem Backup/Restore de mensagens.
  - Sem Stream Processing.
  - Prefetch fixo hardcoded.
  - Msgpack não otimizado (sem compressão).
- [ ] **Neo4j Gaps**:
  - Temporal Queries ausentes.
  - Graph Analytics limitada.
  - Anomaly Detection inexistente.
  - Schema implícito (sem Pydantic pre-validation).
  - GraphQL integration faltando.
  - Real-time updates (CDC) faltantes.
  - GNN embeddings faltantes.
  - Graph Compression ausente.
- [ ] **Qdrant Gaps**:
  - Hybrid Search inexistente.
  - Reranking ausente.
  - Sparse Vectors não usados.
  - Sem Data Lifecycle/Archiving.
  - Deduplicação incompleta (automática).
  - Snapshots & Backup ausente.
  - Multi-tenancy (payload filtering) pendente.
  - Semantic Caching por similaridade pendente.
- [ ] **Memory Core**:
  - PII Redaction incompleto (Regex vs NER).
  - Memory Compaction ausente.
  - Memory Export/Import ausente.
- [ ] **Consolidator**:
  - Conflitos de consolidação (Locking).
  - Métricas de consolidação.
  - Cross-Modal consolidation.

### 🧪 Testing & Quality Assurance

- [ ] **Cobertura Fragmentada**: Muitos módulos críticos sem testes unitários.
- [ ] **Testes Dependentes de Infra**: Falta de mocks/fixtures isolados.
- [ ] **Chaos Testing Incompleto**: Integrar `chaos_harness.py` ao CI.
- [ ] **Test Coverage Reporting**: Faltam métricas de cobertura (pytest-cov).
- [ ] **Contract Testing**: Falta OpenAPI/Pact entre Front e Back.
- [ ] **Property-Based Testing**: Considerar `hypothesis`.
- [ ] **Test Data Management**: Factories/Builders unificados.
- [ ] **Flaky Tests**: Quarentena e retry automático.
- [ ] **Security Regression**: Suite de testes de segurança recorrente.
- [ ] **Smoke Tests Observabilidade**: Melhorar validação real.
- [ ] **Verify Scripts Manuais**: Integrar ao CI.
- [ ] **Linting Hooks**: Pre-commit hooks para ruff/mypy.
- [ ] **Type Checking CI**: Ativar mypy no pipeline.

### 🌙 Evolution & Dream Mode

- [ ] **Lab Cleanup Incompleto**: Garantir limpeza de containers de teste.
- [ ] **Evolution Persistence**: UI e API para histórico de evoluções.
- [ ] **Dry Run Realista**: Estimativa de custo/tempo.
- [ ] **Evolution Rollback**: Snapshot e restore automático em falha.
- [ ] **Guardrails de Segurança**: Bloquear alterações sensíveis.
- [ ] **Dataset Sintético**: Gerar dados de teste anonimizados.
- [ ] **LogAwareReflector**: Parsear stack traces multi-linha.
- [ ] **Reflection Triggers**: Reativo a taxa de erros.
- [ ] **Self-Study Scope**: Suportar TS, YAML, MD.
- [ ] **Study Results Persistence**: Salvar aprendizados no Neo4j.

### Ω Outros (Docs, Analytics, Multi-Modal)

- [ ] **Analytics**: User Behavior, Cost Attribution, Performance Insights.
- [ ] **Multi-Modal**: Wake Word, Voice Circuit Breaker, Real-Time Transcription, Voice Response, Vision Pipeline, Screenshot Analysis, OCR.
- [ ] **Docs**: Inconsistência de versões, Docs duplicadas, SEO, runbook de Troubleshooting, ADRs ausentes.
- [ ] **CI/CD**: Pipeline Github Actions, Blue-Green Deployment, Container Health Checks.

---

## ✅ Histórico de Conclusões (Arquivado)

### Jan/2026 - Auditoria & Autonomia

- [x] **Robustness Layers**: State Checkpointing, Reflexion Loops e Pydantic Validation.
- [x] **Meta-Agent Architecture**: Refatoração para Grafos de Estado (StateGraph).
- [x] **Runtime Self-Correction**: Loop OODA no AutonomyService.
- [x] **Volatile Memory**: SQLite WAL local-first com self-healing.
- [x] **Ghost Data Fix**: Correção de integridade referencial distribuída.
- [x] **Event Loop Blocking Fix**: Remoção de chamadas síncronas no fluxo async.
- [x] **Docker Limits**: Resource limits configurados.
- [x] **Design System**: Criação de `_design-system.scss` e tokens unificados.
- [x] **Local LLM Setup**: Configuração de Qwen 2.5 e DeepSeek Distill locais (16GB VRAM).
- [x] **Agent Events Dashboard**: UI em tempo real para visualizar raciocínio.
- [x] **Config Secrets**: Pydantic SecretStr para evitar vazamento de chaves.
- [x] **SOTA Planning (Reflexion)**: Planner pipeline (Draft -> Critique -> Refine).
- [x] **Dual-PaaS Conflict**: Firebase definido como SSOT.

---
*Documento vivo. Verificar Board do Jira/Github Projects para status diário.*
