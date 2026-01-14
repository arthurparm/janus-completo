# 🗺️ Janus Roadmap & Technical Debt (2026)

Este documento centraliza o planejamento estratégico, dívidas técnicas e inovações futuras do Janus.
> *Última atualização: 12/01/2026 (Pós-Auditoria de Infraestrutura)*

## 🚦 Strategic Execution Phases

### 🧭 Strategic Pivots (2026 Roadmap Review)
>
> *Mandated by 2026 Architecture Review. These override conflicting backlog items.*

- [ ] **Generative UI Standardization (A2UI)** ⚠️
  - *Pivot*: Abandon custom JSON-UI parsers.
  - *Action*: Adopt Vercel AI SDK / A2UI standards for React component streaming.
- [ ] **Hybrid Agent Architecture** 🏗️
  - *Pivot*: Modularize agent runtimes.
  - *Action*: Use **LangGraph** for orchestration (State/Router) and **PydanticAI** for leaf workers (Type-safe tools).
- [ ] **Native GraphRAG Pipelines** 🔧
  - *Pivot*: Stop custom graph builders.
  - *Action*: Integrate `neo4j_graphrag` package for automated hybrid retrieval & entity extraction.
- [ ] **Centralized HITL (Human-in-the-Loop)** 🛡️
  - *Pivot*: Remove decentralised approval logic.
  - *Action*: Move all human approval interruptions to LangGraph Checkpointers (Postgres).
- [ ] **Native Security Middleware** 🔒
  - *Pivot*: Replace regex filters.
  - *Action*: Deploy LangChain v1.0+ PII Redaction & Moderation middlewares.

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

#### 🎯 Frontend Sprint Roadmap (2026 Q1)

> **Status**: PLANNED | **Objetivo**: Polir frontend para cobertura completa do backend  
> **Gap Atual**: 18% (7/38 endpoints com UI) | **Meta**: 90%+ cobertura  
> **Design**: Abandono do Magicpunk → Clean Professional (GitHub-style dark)

**Estrutura**: 3 páginas/sprint | 2 devs paralelos | ~4 semanas

---

##### Sprint 0: Foundation (1 semana) 🏗️

**Objetivo**: Remover Magicpunk, criar design system limpo

- [x] **Design System Clean**
  - *Ação*: Deletar `styles.scss` (364 linhas Magicpunk: orbs, scanlines, glows)
  - *Criar*: `_tokens.scss` (cores profissionais), `_components.scss` (botões/cards limpos)
  - *Resultado*: Base visual GitHub-style (dark mode, subtle accents)

- [x] Shared Components Library
  - [x] Planejamento e Design de API
  - [x] Implementar `UiCardComponent`
  - [x] Implementar `UiButtonDirective` (mais leve que componente)
  - [x] Implementar `UiBadgeComponent`
  - [x] Implementar `UiTableComponent` (container styles)
  - [x] Refatorar `HudPanelComponent` para usar novos componentes

- [x] **Markdown Service**
  - *Dependências*: `marked`, `highlight.js`, `dompurify`
  - *Função*: Renderizar respostas LLM com syntax highlighting

---

##### Sprint 1: Core Pages (1 semana) 🚀

**Página 1: Chat Redesign** ✨

- *Backend*: `chat.py` (23KB)
- *Expectativa*:
  - Mensagens renderizadas em **Markdown** (headers, listas, code blocks)
  - **Citations expandíveis** em cards (file path, score, snippet)
  - Streaming visual (typing indicator, progress bar)
  - Layout limpo: sidebar + main (GitHub style)
- *Features*:
  - ✅ SSE streaming mantido
  - ✅ Paginação histórico
  - ✅ Busca conversas
  - ✅ Syntax highlighting em código
  - ✅ Citation cards interativos

**Página 2: Observability Dashboard** 📊

- *Backend*: `observability.py` (8.6KB)
- *Expectativa*:
  - **Tab 1 - Poison Pills**: Tabela com filtro por queue, botão cleanup
  - **Tab 2 - Graph Quarantine**: Lista de entidades quarentenadas (promote/reject actions)
  - **Tab 3 - Audit Log**: Eventos de auditoria (filtros: tool, status, date range)
- *Features*:
  - ✅ Quarantine table com ações inline
  - ✅ Stats cards (total quarantined, by queue)
  - ✅ Audit events timeline

**Página 3: LLM Management** 🤖

- *Backend*: `llm.py` (8.7KB)
- *Expectativa*:
  - **Provider Cards**: OpenAI ✅, Anthropic ✅, DeepSeek ⚠️ (c/ status health)
  - **Cache Stats**: Hit rate graph, total entries
  - **Circuit Breakers**: Visual de estado (open/closed), botão reset
  - **Budget Summary**: Gráfico spend vs. limit
- *Features*:
  - ✅ Real-time provider health
  - ✅ Toggle enable/disable providers
  - ✅ Cache performance metrics
  - ✅ Cost tracking visual

---

##### Sprint 2: Advanced Pages (1 semana) 🔧

**Página 4: RAG/Knowledge** 🧠

- *Backend*: `rag.py` (20KB!)
- *Expectativa*:
  - **Tab 1 - Vector Search**: Input query → results table (score, snippet, metadata)
  - **Tab 2 - Stats**: Total vectors, query latency avg, cache hits
  - **Tab 3 - Consolidation**: Trigger manual job, view queue status
- *Features*:
  - ✅ Search UI com filters (min score, limit)
  - ✅ Results highlighting
  - ✅ Consolidation job monitor

**Página 5: Autonomy Dashboard** 🤖

- *Backend*: `autonomy.py` (10.8KB)
- *Expectativa*:
  - **Control Panel**: Big toggle Start/Stop, status badge (active/idle)
  - **Live Plan**: JSON editor visualizando plano atual
  - **Policy Editor**: Form (risk profile dropdown, allowlist chips, budget slider)
  - **Execution Timeline**: Histórico de ações executadas
- *Features*:
  - ✅ Start/stop controls
  - ✅ Real-time status
  - ✅ Plan preview editable
  - ✅ Policy configuration UI

**Página 6: Meta-Agent Monitor** 🧬

- *Backend*: `meta_agent.py`
- *Expectativa*:
  - **OODA Loop Visualization**: 4 stages (Observe → Orient → Decide → Act)
  - **Current Cycle**: Card showing active stage + reasoning
  - **History Table**: Past cycles (date, outcome, decisions made)
- *Features*:
  - ✅ Real-time cycle updates
  - ✅ OODA stage progression
  - ✅ Decision rationale display

---

##### Sprint 3: Nice-to-Have (1 semana) 🎁

**Página 7: Tools Management** 🔧

- *Backend*: `tools.py` (7KB)
- *Expectativa*:
  - **Tools Grid**: Cards (name, description, category, permission level)
  - **Filters**: Por category/permission
  - **Executor Modal**: Form dinâmico baseado em schema da tool
- *Features*:
  - ✅ Tool catalog visual
  - ✅ Dynamic form generation
  - ✅ Execute tool com args

**Página 8: Workers Status** ⚙️

- *Backend*: `workers.py`
- *Expectativa*:
  - **Worker Cards**: Status (running/stopped), last heartbeat, tasks processed
  - **Controls**: Start All / Stop All buttons
  - **Auto-refresh**: Polling 5s
- *Features*:
  - ✅ Worker health monitoring
  - ✅ Mass control actions

**Página 9: System Dashboard** 🏠

- *Backend*: `system_overview.py`
- *Expectativa*:
  - **Metrics Cards**: CPU, RAM, uptime, tokens/min (big numbers)
  - **Service Health**: Grid de indicators (green/yellow/red)
  - **Quick Links**: Botões para Chat, Autonomy, Observability
- *Features*:
  - ✅ At-a-glance system health
  - ✅ Navigation hub
  - ✅ Real-time metrics

---

**Progresso**: 0/9 páginas | **Próximo**: Sprint 0 (Design System)

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

## 💬 Prompt System (Modular Architecture)

### Melhorias Identificadas (Jan/2026)

- [ ] **LLM-based Context Compression** 🔥
  - *Arquivo*: `app/core/prompts/modules/context_compression.py:78`
  - *Gap*: Usa compressão extrativa simples (caracteres / 4)
  - *Ação*: Integrar LLM (DeepSeek-Distill) para compressão semântica inteligente
  - *Impacto*: Melhor preservação de contexto em conversas longas

- [ ] **ML-based Intent Classification** 💡
  - *Arquivo*: `app/core/prompts/intent_classifier.py`
  - *Gap*: Classificação baseada em keywords (pode errar em casos ambíguos)
  - *Ação*: Treinar modelo ML simples (SVM/BERT lightweight) com logs históricos
  - *Impacto*: 95%+ accuracy vs ~80% atual

- [ ] **Proper Tokenizer Integration** 🔧
  - *Arquivo*: `app/core/prompts/base.py:73`
  - *Gap*: Estimativa de tokens usa heurística (`len(text) // 4`)
  - *Ação*: Integrar `tiktoken` para contagem precisa
  - *Impacto*: Precisão de métricas e budgets

- [ ] **Prompt Caching (LRU)** ⚡
  - *Arquivo*: `app/services/prompt_composer_service.py`
  - *Gap*: Cache desabilitado (skeleton implementado)
  - *Ação*: Ativar `@lru_cache` com TTL de 5 minutos
  - *Impacto*: Reduzir latência em 30-40% para mensagens similares

- [ ] **Sophisticated Fallback Hierarchy** 🔥🔥🔥
  - *Gap*: **474+ ocorrências** de `except Exception:` com fallbacks silenciosos ou simplificados em todo o codebase
  - *Arquivos críticos identificados*:
    - `reasoning_protocol.py:53-56` - Fallback simples quando protocolo não encontrado
    - `document_service.py` - **28 fallbacks genéricos** (!!)
    - `chat_service.py` - **50+ fallbacks sem logging adequado**
    - `knowledge_consolidator_worker.py` - Fallback síncrono sem estratégia
    - `autonomy_service.py:474-493` - Fallback de tool único (poderia ter chain)
    - `tool_executor_service.py:38` - Parsing com fallback "frouxo" sem validação
    - `semantic_commit_service.py:136` - Fallback naïve (primeira linha não-vazia)
    - `vision/screen_capture.py:99` - Fallback fullscreen sem aviso
    - `router_worker.py:45` - Heurística hardcoded como fallback
  - *Problemas*:
    1. **Silent Failures**: 90% dos `except Exception:` não logam contexto suficiente
    2. **No Retry Strategy**: Apenas captura e ignora, sem tentativas graduais
    3. **No Circuit Breaking**: Falhas repetidas não abrem circuit breaker
    4. **No Monitoring**: Métricas de fallback rate ausentes
    5. **Single-Level**: Maioria tem apenas 1 fallback, deveria ter hierarchy
    6. **No Degradation Strategy**: Tudo-ou-nada vs graceful degradation
  - *Ação*:
    1. **Criar `FallbackChain` pattern**:

       ```python
       class FallbackChain:
           def __init__(self, strategies: list[Callable]):
               self.strategies = strategies
           
           async def execute(self, *args, **kwargs):
               for i, strategy in enumerate(self.strategies):
                   try:
                       result = await strategy(*args, **kwargs)
                       if i > 0:  # Fallback usado
                           FALLBACK_COUNTER.labels(level=i).inc()
                       return result
                   except Exception as e:
                       logger.warning(f"Strategy {i} failed: {e}")
                       if i == len(self.strategies) - 1:
                           raise  # Último fallback falhou
               ```

    2. **Implementar hierarchical fallbacks**:
       - Primary → Secondary → Tertiary → Minimal → Error
       - Reasoning: Full Protocol → Generic → Minimal → Error
       - Tools: Preferred → Alternative → Built-in → Manual
       - Parsing: Strict → Lenient → Regex → Raw
    3. **Adicionar logging estruturado**:

       ```python
       except Exception as e:
           logger.warning(
               "fallback_triggered",
               primary_failed=str(e),
               fallback_level=level,
               context={...}
           )
       ```

    4. **Métricas de saúde**:
       - `fallback_rate_total` (by component)
       - `fallback_success_rate` (quantos fallbacks funcionaram)
       - `fallback_depth_avg` (qual nível foi usado em média)
    5. **Circuit Breaker Integration**:
       - Se primary falha >5x em 60s → abrir circuit e usar fallback direto
       - Auto-recovery após timeout
  - *Impacto*:
    - **Robustez**: Sistema degrada graciosamente vs crash hard
    - **Observabilidade**: Saber onde fallbacks são usados frequentemente
    - **Confiabilidade**: 99.9% uptime com degradação inteligente
    - **Performance**: Evitar tentar primary quando sabidamente falho
  - *Prioridade*: **P0** - Afeta estabilidade de produção
  - *Estimativa*: 3-5 dias para implementar framework + refatorar top 20 services

- [ ] **Dynamic Module Priority** 🎯
  - *Gap*: Prioridade dos módulos é estática (10-50)
  - *Ação*: Ajustar prioridade baseado em contexto (histórico longo = compression first)
  - *Impacto*: Otimização adaptativa de token budget

- [ ] **Expand Intent Types** 🌐
  - *Gap*: Apenas 13 intents definidos
  - *Ação*: Adicionar: `REFACTORING`, `DOCUMENTATION_QUERY`, `ARCHITECTURE_DESIGN`, `DATA_ANALYSIS`
  - *Impacto*: Prompts mais especializados para casos edge

- [ ] **Multi-Language Protocol Support** 🌍
  - *Gap*: Protocolos misturados PT/EN
  - *Ação*: Separar templates por idioma, detectar idioma do usuário
  - *Impacto*: Melhor UX para usuários não-PT

- [ ] **Adaptive Token Budget** 💰
  - *Gap*: Token budget fixo por módulo
  - *Ação*: Alocar budget dinamicamente baseado em complexidade da tarefa
  - *Impacto*: Usar tokens onde mais importam

- [ ] **Auto-tuning via Feedback** 📊
  - *Gap*: Não há loop de feedback sobre qualidade de prompts
  - *Ação*: Coletar user feedback (👍/👎) e A/B test variantes
  - *Impacto*: Otimização contínua de templates

### Concluído (Jan/2026)

- [x] **Eliminação de Código Legado** ✅
  - Removidas 504 linhas de código monolítico (`_build_prompt_legacy`)
  - Arquivo reduzido de 583 → 115 linhas
  - 100% modular, zero fallbacks legados

- [x] **Arquitetura Modular** ✅
  - 5 módulos composíveis criados
  - Intent-based module selection
  - Token reduction: 44-54% (2500 → 1200-1400 tokens)

- [x] **Intent Classifier** ✅
  - Extraído de lógica de prompt
  - Keyword-based com confidence scoring
  - 13 categorias de intent

- [x] **Context Compression (Basic)** ✅
  - Chain-of-Density simples implementado
  - Bypass para históricos curtos (≤3 msgs)
  - Compressão para 150-200 tokens

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
