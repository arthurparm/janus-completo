# 🗺️ System Inventory & Technical Debt

> *Source: Originally from `Melhorias possiveis.md` (Updated 14/01/2026)*

This document maintains the detailed lists of technical debt, system inventory (API routes), backlog, and completed tasks for the Janus project.

For high-level architecture and roadmap, see the root [README.md](../README.md).

## 📌 Índice

- [Backlog por Dificuldade](#-backlog-por-dificuldade-throughput--médias--difíceis)
- [Scientific Foundation (State-of-the-Art)](#-scientific-foundation-state-of-the-art)
- [Scientific Frontier (Post-V1 Evolution)](#-scientific-frontier-post-v1-evolution)
- [Infrastructure Strategy (Phase 3)](#-infrastructure-strategy-phase-3)
- [V1 Critical Path (Launch Blockers)](#-v1-critical-path-launch-blockers)
- [Histórico de Conclusões (Arquivado)](#-histórico-de-conclusões-arquivado)
- [Levantamentos (Tasks)](#-levantamentos-tasks)
- [Anexos — Levantamentos detalhados](#-anexos--levantamentos-detalhados)

---

## 🧱 Backlog por Dificuldade (Throughput / Médias / Difíceis)

Critério prático:
- **Throughput**: mudanças bem definidas, mecânicas e de baixo risco (boa para Mini).
- **Médias**: exigem contexto do sistema e algum design, mas com escopo controlável.
- **Difíceis**: risco alto, dependências cruzadas, refatoração estrutural, concorrência ou segurança.

### 🟢 Throughput

- Ajustar CSP para produção (reduzir `unsafe-inline`/`unsafe-eval`) em *Security Headers Middleware*.
- Padronizar toasts de sucesso/erro/warn em fluxos críticos em *UX Improvements*.
- Varredura e centralização de settings/URLs hardcoded em `environment.ts` em *Hardcoded Settings*.
- Higienizar `eslint-report.json` e travar regressões no CI em *Linter Bankruptcy*.

### 🟡 Médias

- Completar *UI Coverage* (telas faltantes, empty/error/loading states).
- Resolver *Autonomy 500 Error* (reproduzir, corrigir, testar).
- Implementar *Input Sanitization* (política por endpoint + validação extra de payloads livres).
- Evoluir *Smart Model Routing* com classificação de complexidade (heurística/embedding).

### 🔴 Difíceis

- Corrigir *Broken Thought Stream* (RabbitMQ → SSE → UI) com teste E2E.
- Eliminar *State Desync* (definir fonte única de estado e migrar).
- Substituir *Ad-hoc State Management* por store robusta (SignalStore/Elf/NgRx).
- Unificar Design System (*Design System Conflict*: remover Material gradualmente).
- Implementar *Audit Log Imutável* (append-only + tamper-evident + acesso).
- Finalizar *Database Migration Pipeline* (Alembic + CI/deploy).
- Implementar *Graceful Degradation* (matriz de degradação + health/alertas).
- Scientific Foundation/Frontier: itens pendentes de pesquisa/implementação (LATS/ToT/Self-RAG/RAPTOR/etc).

---

## 🔬 Scientific Foundation (State-of-the-Art)

*Arquitetura baseada em 13+ papers seminais que fundamentam a inteligência do Janus.*

### 🧠 Reasoning & Planning (O Cérebro)

* [ ] **LATS (Language Agent Tree Search)** - *Zhou et al., 2023*
  * **Conceito**: Combina LLM com Monte Carlo Tree Search (MCTS) para explorar múltiplos caminhos de solução.
  * **No Janus**: Nó `Planner` que simula cenários antes de executar ações críticas (ex: deploy).
* [x] **Reflexion** - *Shinn et al., 2023*
  * **Conceito**: Agentes que verbalizam erros e guardam lições em memória de curto prazo.
  * **No Janus**: Loop de auto-correção no `CoderAgent` para erros de compilação.
* [x] **Graph of Thoughts (GoT)** - *Besta et al., 2023*
  * **Conceito**: Modela o pensamento como um grafo (DAG), permitindo combinar e refinar ideias.
  * **No Janus**: Orquestração não-linear no LangGraph (Supervisor Node).
* [ ] **Tree of Thoughts (ToT)** - *Yao et al., 2023*
  * **Conceito**: Exploração deliberada de múltiplos ramos de raciocínio.
  * **No Janus**: Base para o processo de decisão do `Meta-Agent`.
* [ ] **Chain of Thought (CoT)** - *Wei et al., 2022*
  * **Conceito**: "Let's think step by step".
  * **No Janus**: Padrão obrigatório em todos os prompts de sistema.

### 💾 Memory & Learning (A Alma)

* [ ] **Generative Agents** - *Park et al., 2023*
  * **Conceito**: Memória com Recência, Importância e Relevância + "Sonho" (Consolidação).
  * **No Janus**: Arquitetura do `MemoryService` e worker noturno de consolidação no Neo4j.
* [ ] **MemGPT** - *Packer et al., 2023*
  * **Conceito**: Gestão de contexto infinito via paginação (OS-like memory management).
  * **No Janus**: Estratégia de paginação de contexto para conversas longas.
* [ ] **Voyager** - *Wang et al., 2023*
  * **Conceito**: Aprendizado contínuo via biblioteca de habilidades (Skill Library).
  * **No Janus**: Persistência de ferramentas e scripts de sucesso para reuso.

### 🔍 Retrieval & RAG (O Conhecimento)

* [ ] **Self-RAG** - *Asai et al., 2023*
  * **Conceito**: O modelo critica sua própria recuperação (`[IsREL]`, `[IsSUP]`).
  * **No Janus**: Pipeline de `NativeGraphRAG` com etapa de verificação.
* [x] **HyDE (Hypothetical Document Embeddings)** - *Gao et al., 2022*
  * **Conceito**: Gerar resposta ideal hipótetica para buscar documentos similares.
  * **No Janus**: Melhoria na busca vetorial do Qdrant.
* [ ] **RAPTOR** - *Sarthi et al., 2024*
  * **Conceito**: Indexação recursiva em árvore (resumos de resumos).
  * **No Janus**: Estrutura hierárquica de conhecimento no Neo4j.

### 🤖 Multi-Agent (O Corpo)

* [ ] **MetaGPT** - *Hong et al., 2023*
  * **Conceito**: SOPs (Standard Operating Procedures) codificados para agentes.
  * **No Janus**: Definição rígida de papéis (Product Manager, Architect, Engineer).
* [ ] **CAMEL** - *Li et al., 2023*
  * **Conceito**: Arquitetura de "Role-Playing" para comunicação comunicativa.
  * **No Janus**: Protocolo de comunicação entre Supervisor e Workers.

### 🛡️ Safety & Alignment (A Consciência)

* [ ] **Constitutional AI** - *Bai et al., 2022 (Anthropic)*
  * **Conceito**: Controle de comportamento através de uma "Constituição" (regras naturais) em vez de RLHF manual extensivo.
  * **No Janus**: Extensão do `ReflectorAgent` para validar outputs contra regras de segurança (`security.yaml`) antes da entrega.

### ⚡ Optimization & Economy (A Eficiência)

* [ ] **FrugalGPT (LLM Cascades)** - *Chen et al., 2023*
  * **Conceito**: Chamar modelos menores/baratos primeiro; escalar para modelos SOTA apenas se a confiança for baixa.
  * **No Janus**: `ModelRouter` na infraestrutura que tenta resolver com Llama-3-Locall/Mini antes de chamar DeepSeek/GPT-4.
* [ ] **DSPy (Programming with Prompts)** - *Khattab et al., 2023*
  * **Conceito**: Abstrair prompts como parâmetros otimizáveis. O sistema "compila" e melhora seus próprios prompts baseado em métricas.
  * **No Janus**: Pipeline de auto-ajuste dos prompts dos Workers baseado no feedback de erro/sucesso.

### 🎨 HCI & Experience (A Interface)

* [ ] **Generative UI** - *Vercel AI SDK v5 / Dynaboard*
  * **Conceito**: A UI é gerada dinamicamente pelo LLM para se adaptar à intenção do usuário (tabelas, gráficos, formulários on-the-fly).
  * **No Janus**: Utilização de `Angular Dynamic Components` + `ViewContainerRef` para renderizar componentes visuais baseados em tool-calls.

---

## 🧪 Scientific Frontier (Post-V1 Evolution)

*Conceitos de vanguarda (2025/2026) para transformar o Janus em uma AGI embrionária.*

### 🧩 Self-Evolving Toolset (Agent-0 Style)

* **Conceito**: O agente não apenas usa ferramentas, ele **cria** suas próprias ferramentas.
* **Implementação**: `ToolSynthesizerAgent`. Quando o Janus identifica uma tarefa repetitiva sem ferramenta, ele escreve um script Python, valida no Sandbox, e se funcionar, salva no DB como uma nova `Tool` permanente.

### 🐝 Swarm Intelligence (Descentralização)

* **Conceito**: Abandono da orquestração centralizada para um modelo de enxame.
* **Implementação**: **Dynamic Handoffs**. Agentes podem transferir a execução diretamente para outros especialistas (`transfer_to_agent`) sem passar pelo Supervisor, reduzindo latência e gargalos.

### 💾 Active Memory Management (OS-Level)

* **Conceito**: O LLM gerencia ativamente sua janela de contexto como um Sistema Operacional gerencia RAM.
  * **Implementação**: Token de controle `<memory_warning>`. Quando o contexto enche, o agente é forçado a decidir o que "esquecer" (apagar) ou "arquivar" (salvar no Neo4j) antes de continuar.

### 🧬 Code Generation & Rigor

1. **Flow Engineering / AlphaCodium** - *CodiumAI, 2024*
    * **Conceito**: Substituir o "zero-shot coding" por um fluxo iterativo rígido: *Análise yaml -> Plan -> Tests -> Code -> Fix*.
    * **No Janus**: Refatoração do `CoderAgent` para seguir este StateFlow rígido (aumenta acurácia de ~19% para ~44%).
2. **Hippocampal Memory Replay** - *DeepMind/Stanford*
    * **Conceito**: Consolidação offline. O agente "sonha" (simula tasks) durante o idle time para reforçar conexões no Grafo.
    * **No Janus**: Upgrade no `SelfStudyManager` para rodar replays de experiências passadas.

### ⏱️ Latency & UX

1. **Skeleton-of-Thought** - *Ning et al., 2023*
    * **Conceito**: Gerar primeiro o esqueleto (tópicos) da resposta, depois preencher o conteúdo em paralelo.
    * **No Janus**: Otimização para respostas longas no chat, reduzindo a latência percebida.

---

## 🏛️ Infrastructure Strategy (Phase 3)

### 🧠 Model Routing Strategy (The "Brains")

* **DeepSeek V3/R1** (The Workhorse):
  * *Uso*: Coding pesado, refatoração, generation.
  * *Por que*: Melhor custo-benefício para código (bate GPT-4 em benchmarks de dev).
  * *Custo*: ~$0.14/1M input | ~$0.28/1M output.

* **Qwen 2.5 72B** (The Architect):
  * *Uso*: Review crítico, Design de Sistema, Validação de lógica.
  * *Por que*: Performance de coding nível SOTA (similar ao Claude/GPT-4), mas extremamente acessível.
  * *Custo*: ~$0.12/1M input | ~$0.39/1M output.
  * *Comparativo*: **GPT-5.2 Mini** custa **$2.00/1M output** (5x mais caro) e não oferece cota grátis real.

* **Llama-3-Local / Flash** (The Speedster):
* *Uso*: Chat rápido, Classificação, Roteamento.

### 💰 Budget & Rate Limiting Strategy (Dual-Wallet)

* **Wallet A (DeepSeek API - $9.50)**:
  * **Uso**: Dedicado 100% ao **Workhorse (DeepSeek V3)**.
  * **Vantagem**: Menor latência (direto na fonte) e não consome saldo do OpenRouter.

* **Wallet B (OpenRouter - $10.00)**:
  * **Uso Primário**: **Architect (Qwen 2.5 72B)** (Reviews e Decisões).
  * **Perk**: Ter crédito >$0 desbloqueia **1000 requests/dia** em modelos Free/Trial.
  * **Uso Secundário**: Speedster (Llama 3 Free) via quota diária gratuita.

* **Distribuição Diária Sugerida**:
    1. **Workhorse (Via Direct API)**: ~700 requests (Consome saldo A).
    2. **Architect (Via OpenRouter)**: ~200 requests (Consome saldo B).
    3. **Speedster (Via OpenRouter Free)**: ~100 requests (Consome quota diária, zero custo).

### ☢️ The Privacy Dilemma (Option C)

* **OpenAI Data Sharing (Complimentary Tokens)**:
  * **O que é**: OpenAI oferece tokens grátis (ex: 250k/dia) se você permitir que eles treinem com seus dados.
  * **O Risco "Nightmare"**: Todo código, prompt e estratégia do Janus passa a ser propriedade de treino da OpenAI. Se o Janus criar algo inovador, a OpenAI aprende.
  * **Veredito**: **Habilitar SOMENTE se o projeto não tiver segredos comerciais/IP críticos.** Caso contrário, o custo da privacidade violada >>> economia de $10.

### 🛡️ The Free-Tier Army (Option D - Risk Free)

As melhores quotas gratuitas *reais* de 2026 (Sem custo de privacidade):

1. **Google Gemini (Free Tier)**:
    * **Quota**: ~1500 requests/dia (Flash 2.5).
    * **Uso**: Resumos de textos longos, processamento multimodal (imagens/vídeo).
2. **Groq (Free Tier)**:
    * **Quota**: ~14.4k requests/dia (Llama 3.1 8B) ou ~1k/dia (modelos maiores).
    * **Uso**: Roteamento ultra-rápido, chat simples.
3. **Cohere (Trial)**: ~1000 calls/mês (Limitado, bom apenas para Reranking esporádico).

### 📜 Protocol: Strict Structured Outputs

* **Decisão**: Abandonar "JSON Mode" genérico.
* **Novo Padrão**: **Native Structured Outputs** (OpenAI `response_format` / Anthropic `tool_use` com `strict: true`).
* **DeepSeek Specifics**: O DeepSeek V3 suporta *Strict Mode* (Function Calling) via endpoint `beta` ou prompt engineering avançado. Vamos usar o padrão OpenAI-compatible da DeepSeek.
* **Motivo**: Garante 100% de adesão ao Schema (zero parse errors), eliminando loops de retry e validadores manuais.

---

## 🚨 V1 Critical Path (Launch Blockers)

*Itens obrigatórios para o lançamento da versão 1.0.*

### 🛡️ Security & Enterprise Ready

* [x] **Security Headers Middleware**: Implementar CSP, HSTS, X-Frame-Options e X-Content-Type-Options.
  - [x] Middleware criado (`SecurityHeadersMiddleware`).
  - [x] Registrado no FastAPI (`app.add_middleware(SecurityHeadersMiddleware)`).
  - [x] Headers aplicados na resposta (CSP, HSTS, XFO, X-CTO, Referrer/Permissions).
  - [ ] Ajustar CSP para produção (reduzir/evitar `unsafe-inline` e `unsafe-eval` quando possível).

* [ ] **Input Sanitization**: Validar e sanitizar todos os inputs da API (prevenção de injeção).
  - [ ] Definir política de sanitização por endpoint (query/body/path).
  - [ ] Aplicar validação extra para payloads livres (ex.: prompts, URLs, markdown).
  - [ ] Padronizar erros de validação (Problem+JSON) e métricas.
* [ ] **Rate Limiting (Cost-Based)**: Limitar usuários por **gasto em dólares**, não apenas requisições.
  - [x] Orçamento diário por usuário/projeto aplicado nas chamadas de LLM (corte de `max_tokens` por USD).
  - [x] Tracking de gasto por tenant/provedor em Redis (spend USD).
  - [ ] Propagar enforcement para o gateway HTTP (bloqueio por orçamento por endpoint/usuário).
* [ ] **Audit Log Imutável**: Garantir que logs de ações críticas não possam ser alterados.
  - [ ] Definir formato de evento (append-only) e categorias de ação crítica.
  - [ ] Persistir eventos com hash encadeado (tamper-evident).
  - [ ] Expor auditoria/consulta com controle de acesso.

### 🖥️ Frontend V1 (Refactor & Finish)

* [ ] **UI Overhaul (Clean/Professional)**: Migrar de "Magicpunk" para uma estética SaaS profissional/minimalista (Shadcn/UI + Tailwind).
  - [ ] Consolidar tokens (cores/spacing/typography) e remover estilos legacy.
  - [ ] Substituir componentes principais por equivalents no design system novo.
  - [ ] Definir layout base (header/sidebar/cards/tables) consistente.
* [ ] **Complete UI Coverage**: Implementar telas faltantes (80%+) seguindo o novo Design System (Tools, Workers, RAG).
  - [ ] Mapear páginas/telas faltantes e priorizar por uso.
  - [ ] Implementar rotas e estados vazios (empty/error/loading).
  - [ ] Garantir consistência visual e de interação (botões, tabelas, dialogs).

* [ ] **UX Improvements**:
  * Real-time Feedback (Toasts globais).
  * Onboarding Flow (Wizard de setup).
  * Tratamento de erros amigável.
  - [x] Infra de Toast global disponível (UiToastService/UiToasterComponent).
  - [ ] Padronizar toasts para sucesso/erro/warn em fluxos críticos.
  - [ ] Criar wizard de onboarding (primeiro acesso / setup).
  - [ ] Normalizar mensagens de erro vindas da API (Problem+JSON) para UI.

#### 🐛 Critical Bugs & Failures (Prioridade Alta)

* [ ] **Broken Thought Stream**: O stream de pensamentos do agente (SSE) não está recebendo eventos do RabbitMQ (Tela de Chat).
  - [ ] Confirmar consumo de eventos (RabbitMQ) no backend e fanout para SSE.
  - [ ] Validar contrato de eventos (tipos/payload) e ordenação.
  - [ ] Testar E2E: publicar evento -> UI recebe e renderiza.
* [ ] **Autonomy 500 Error**: Erro interno de servidor (500) impossibilita criação de Objetivos Estratégicos.
  - [ ] Reproduzir erro e capturar stacktrace.
  - [ ] Corrigir validação/DI/repos e adicionar teste.
  - [ ] Garantir retorno com Problem+JSON para erro controlado.
* [ ] **State Desync**: Falta de reatividade entre Backend (Redis) e Frontend (NgRx/Signals).
  - [ ] Identificar fontes de verdade duplicadas (store/local state/cache).
  - [ ] Definir estratégia única de estado (SignalStore/Elf/NgRx) e migração.
  - [ ] Adicionar testes de reatividade (component/store).

#### 🏚️ Technical Debt & Clean Code

* [ ] **Linter Bankruptcy**: `eslint-report.json` gigante (>400KB). Necessário correção massiva e regras mais estritas.
  - [ ] Reduzir violações críticas primeiro (rules de segurança/bug-prone).
  - [ ] Garantir lint no CI e bloquear regressões.
  - [ ] Remover/gerar `eslint-report.json` apenas sob demanda.
* [ ] **Hardcoded Settings**: Remover chaves e URLs hardcoded; mover para `environment.ts`.
  - [ ] Varredura por URLs/chaves fixas no frontend.
  - [ ] Centralizar em `environment.ts` + `api.config.ts`.
  - [ ] Garantir fallback por ambiente (dev/prod/tailscale).
* [ ] **Test Coverage Zero**: Não há testes de unidade ou e2e rodando no frontend atualmente.
  - [ ] Garantir suite mínima rodando no CI (unit).
  - [ ] Adicionar smoke e2e (login + chat).
  - [ ] Definir meta de cobertura (por módulo crítico).
* [x] **Legacy Testing Stack**: Atualizar de Karma/Jasmine para Vitest/Jest + Testing Library (Padrão 2026).
  - [x] Vitest configurado no frontend (`vitest.config.ts` / script `npm test`).
  - [x] Testing Library presente (`@testing-library/angular`).
* [ ] **Ad-hoc State Management**: Substituir `GlobalStateStore` (Signals manuais com high cognitive load) por uma lib robusta (NgRx SignalStore ou Elf) para evitar "State Desync".
  - [ ] Definir alvo (NgRx SignalStore vs Elf) e guideline.
  - [ ] Migrar módulos críticos (Chat, Goals, Autonomy) primeiro.
  - [ ] Remover padrões manuais redundantes após migração.
* [ ] **Design System Conflict**: Remover Angular Material gradual e unificar no Shadcn/UI (Tailwind) para reduzir bundle size e inconsistências visuais.
  - [ ] Mapear pontos de uso do Angular Material e priorizar substituições.
  - [ ] Remover dependências/estilos quando a migração atingir massa crítica.

### ⚙️ Stability & Ops

* [ ] **Database Migration Pipeline**: Finalizar transição para Alembic (abandonar scripts manuais).
  - [ ] Introduzir Alembic (config + env) e primeira migração.
  - [ ] Integrar migrações no deploy/CI.
  - [ ] Documentar fluxo de upgrade/downgrade operacional.

* [ ] **Smart Model Routing**: Router que escolhe entre Local/API baseado na complexidade da task (Economia).
  - [x] Roteamento por papel/prioridade disponível (Local vs Cloud).
  - [x] Guardrails de orçamento e fallback de custo no pipeline de LLM.
  - [ ] Classificar complexidade automaticamente (heurística/embedding) e ajustar prioridade.
* [ ] **Graceful Degradation**: Fallbacks claros quando serviços (ex: Redis, Neo4j) caem.
  - [ ] Definir matriz de degradação por dependência (Redis/Neo4j/Qdrant/RabbitMQ).
  - [ ] Garantir comportamento fail-open/fail-closed por endpoint conforme criticidade.
  - [ ] Expor status e alertas (health checks + métricas) para cada modo degradado.

---

## ✅ Histórico de Conclusões (Arquivado)

### Foundation & Architecture

* [x] **Hybrid Agent Architecture** (LangGraph + PydanticAI).

* [x] **Native GraphRAG** (neo4j-graphrag).
* [x] **Centralized HITL** (Human-in-the-loop via Postgres Checkpoints).
* [x] **Graph Versioning** (Schema Migration & Purge).
* [x] **Observability** (LangSmith Tracing & Setup).
* [x] **Async Database Pool** (asyncpg + SQLAlchemy).
* [x] **Secure Sandbox** (Docker-based execution).
* [x] **Migração MySQL → PostgreSQL** (pgvector).
* [x] **Redis State Backend**.

---

## 🧱 Levantamentos (Tasks)

* [x] **Lote 1 — Boot & Kernel** (levantamento fechado)
* [x] **Lote 2 — API & Endpoints** (levantamento fechado)
* [ ] **Lote 3 — Serviços (LLM, Chat, RAG, Observabilidade, Autonomia)** (levantamento + correções)
* [ ] **Lote 4 — Repositórios e persistência** (levantamento + correções)
* [ ] **Lote 5 — Agentes, Ferramentas e Sandbox** (levantamento + correções)
* [ ] **Lote 6 — TBD** (definir escopo)

---

## 📎 Anexos — Levantamentos detalhados

### ✅ Lote 1 — Boot & Kernel (FECHADO)

**Escopo coberto**: ciclo de vida da aplicação (lifespan), inicialização do Kernel, infraestrutura crítica, DI manual, warm-up, auto-indexação, workers e shutdown.

**Entregáveis concluídos**:

1) **Mapa do fluxo de startup (pipeline textual e criticidade)**
   - Lifespan do FastAPI inicializa o Kernel e mapeia serviços no `app.state` com compatibilidade com rotas antigas.
   - O Kernel executa: infraestrutura → MAS agents → DI → OS tools → workers → auto-index → warm-up → senses.
   - Etapas críticas (falhas interrompem): infraestrutura e MAS agents; etapas “best-effort”: workers, warm-up, voice.

2) **Inventário de infra e impacto operacional**
   - Infra inicializada em paralelo: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
   - Firebase é opcional e não bloqueia o boot (falha não crítica).

3) **Análise de acoplamento (DI manual)**
   - Kernel concentra a criação de repositórios e serviços, aumentando acoplamento e dificultando testes isolados.
   - O fluxo de injeção é “eager” e não lazy, elevando custo de startup.

4) **Workers e scheduler**
   - Workers iniciam de forma global (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
   - Não há flags globais para desativar por ambiente, elevando custo em dev/CI.

5) **Warm-up e auto-indexação**
   - `AUTO_INDEX_ON_STARTUP=True` pode causar custo elevado em bases grandes.
   - Warm-up de LLM em background é assíncrono, porém ainda consome recursos no boot.

**Recomendações técnicas (com foco em custo e desempenho)**

- [ ] Paralelizar carga de prompts (reduz latência de cold start).
- [ ] Indexação incremental baseada em hash/commit (evita O(N) desnecessário).
- [ ] Criar feature flags para workers por ambiente (reduz custo operacional).
- [ ] Introduzir container de DI leve (reduz acoplamento e melhora testabilidade).

---

### 🔍 Lote 2 — API & Endpoints (FECHADO)

**Objetivo**: mapear contratos, endpoints, validacoes e impactos de performance da camada HTTP (FastAPI), incluindo governanca de rotas e seguranca.

#### Resultados (rigor do "coracao")

1) **Inventario completo de rotas v1**
   - Total (Full API): 212 rotas unicas; 65 com request model Pydantic; 2 com upload File/Form.
   - Rotas definidas, mas nao expostas no router v1: admin_graph, meta, resources.
   - Duplicidades reais (mesmo metodo/path): /optimization/* e /productivity/* (detalhe no inventario).
   - Modo PUBLIC_API_MINIMAL exposto: /chat, /users, /profiles, /autonomy, /assistant, /autonomy/history, /consents, /pending_actions, /evaluation, /deployment, /auth, /auto-analysis, /feedback.

#### Inventario completo de rotas (Full API)

##### /admin
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| PATCH | /api/v1/admin/config | admin_config.update_config | ConfigUpdateRequest | ConfigUpdateResponse | ConfigService | nao |

##### /agent
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/agent/execute | agent.agent_execute | AgentExecutionRequest | AgentResponse | AgentService | nao |

##### /assistant
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/assistant/execute | assistant.assistant_execute | AssistantExecuteRequest | AssistantExecutionResult | AssistantService | nao |

##### /auth
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/supabase/exchange | auth.supabase_exchange | SupabaseExchangeRequest | TokenResponse | UserRepository | nao |
| POST | /api/v1/auth/token | auth.issue_token | TokenRequest | TokenResponse | UserRepository | nao |

##### /auto-analysis
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/auto-analysis/health-check | auto_analysis.auto_analyze | query/path | AutoAnalysisResponse | LLMRepository, LLMService, ObservabilityService | nao |

##### /autonomy
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/autonomy/goals | autonomy.list_goals | query/path | list[GoalResponse] | GoalManager | nao |
| POST | /api/v1/autonomy/goals | autonomy.create_goal | GoalCreateRequest | GoalResponse | GoalManager | nao |
| DELETE | /api/v1/autonomy/goals/{goal_id} | autonomy.delete_goal | query/path | raw/dict | GoalManager | nao |
| GET | /api/v1/autonomy/goals/{goal_id} | autonomy.get_goal | query/path | GoalResponse | GoalManager | nao |
| PATCH | /api/v1/autonomy/goals/{goal_id}/status | autonomy.update_goal_status | GoalStatusUpdateRequest | GoalResponse | GoalManager | nao |
| GET | /api/v1/autonomy/history/runs | autonomy_history.list_runs | query/path | list[RunSummary] | AutonomyRepository | nao |
| GET | /api/v1/autonomy/history/runs/{run_id} | autonomy_history.get_run | query/path | RunSummary | AutonomyRepository | nao |
| GET | /api/v1/autonomy/history/runs/{run_id}/steps | autonomy_history.list_steps | query/path | list[StepItem] | AutonomyRepository | nao |
| GET | /api/v1/autonomy/plan | autonomy.get_autonomy_plan | query/path | raw/dict | AutonomyService | nao |
| PUT | /api/v1/autonomy/plan | autonomy.update_autonomy_plan | PlanUpdateRequest | raw/dict | AutonomyService | nao |
| PUT | /api/v1/autonomy/policy | autonomy.update_policy | PolicyUpdateRequest | raw/dict | AutonomyService | nao |
| POST | /api/v1/autonomy/start | autonomy.start_autonomy | AutonomyStartRequest | raw/dict | AutonomyService | nao |
| GET | /api/v1/autonomy/status | autonomy.autonomy_status | query/path | AutonomyStatusResponse | AutonomyService | nao |
| POST | /api/v1/autonomy/stop | autonomy.stop_autonomy | query/path | raw/dict | AutonomyService | nao |

##### /chat
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/chat/conversations | chat.list_conversations | query/path | list[ChatListResponse] | ChatService | nao |
| GET | /api/v1/chat/health | chat.chat_health | query/path | raw/dict | ChatService | nao |
| POST | /api/v1/chat/message | chat.send_message | ChatMessageRequest | ChatMessageResponse | ChatService, MemoryService | nao |
| POST | /api/v1/chat/start | chat.start_chat | ChatStartRequest | ChatStartResponse | ChatService | nao |
| GET | /api/v1/chat/stream/{conversation_id} | chat.stream_message | query/path | raw/dict | ChatService | nao |
| DELETE | /api/v1/chat/{conversation_id} | chat.delete_conversation | query/path | raw/dict | ChatService | nao |
| GET | /api/v1/chat/{conversation_id}/events | chat.stream_agent_events | query/path | raw/dict | ChatService | nao |
| GET | /api/v1/chat/{conversation_id}/history | chat.chat_history | query/path | ChatHistoryResponse | ChatService | nao |
| GET | /api/v1/chat/{conversation_id}/history/paginated | chat.chat_history_paginated | query/path | ChatHistoryPaginatedResponse | ChatService | nao |
| PUT | /api/v1/chat/{conversation_id}/rename | chat.rename_conversation | ChatRenameRequest | raw/dict | ChatService | nao |

##### /collaboration
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/collaboration/agents | collaboration.list_agents | query/path | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/agents/create | collaboration.create_agent | CreateAgentRequest | CreateAgentResponse | CollaborationService | nao |
| GET | /api/v1/collaboration/agents/{agent_id} | collaboration.get_agent_details | query/path | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/health | collaboration.health_check | query/path | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/projects/execute | collaboration.execute_project | ExecuteProjectRequest | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/system/shutdown | workspace.shutdown_system | query/path | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/tasks | collaboration.list_tasks | query/path | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/tasks/create | collaboration.create_task | CreateTaskRequest | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/tasks/execute | collaboration.execute_task | ExecuteTaskRequest | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/tasks/execute_parallel | collaboration.execute_tasks_parallel | ExecuteTasksParallelRequest | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/tasks/{task_id} | collaboration.get_task_details | query/path | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/workspace/artifacts/add | workspace.add_artifact | AddArtifactRequest | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/workspace/artifacts/{key} | workspace.get_artifact | query/path | raw/dict | CollaborationService | nao |
| POST | /api/v1/collaboration/workspace/messages/send | workspace.send_message | SendMessageRequest | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/workspace/messages/{agent_id} | workspace.get_messages_for | query/path | raw/dict | CollaborationService | nao |
| GET | /api/v1/collaboration/workspace/status | collaboration.get_workspace_status | query/path | raw/dict | CollaborationService | nao |

##### /consents
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/consents/ | consents.list_consents | query/path | list[ConsentResponse] | - | nao |
| POST | /api/v1/consents/ | consents.grant_consent | ConsentRequest | ConsentResponse | - | nao |
| POST | /api/v1/consents/{consent_id}/revoke | consents.revoke_consent | query/path | ConsentResponse | - | nao |

##### /context
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/context/current | context.get_current_context | query/path | ContextInfo | ContextService | nao |
| POST | /api/v1/context/enriched | context.get_enriched_context | EnrichedContextRequest | raw/dict | ContextService | nao |
| GET | /api/v1/context/format-prompt | context.format_context_for_prompt | query/path | raw/dict | ContextService | nao |
| POST | /api/v1/context/web-cache/invalidate | context.invalidate_web_cache | InvalidateCacheRequest | raw/dict | ContextService | nao |
| GET | /api/v1/context/web-cache/status | context.get_web_cache_status | query/path | raw/dict | ContextService | nao |
| GET | /api/v1/context/web-search | context.search_web | query/path | WebSearchResult | ContextService | nao |

##### /deployment
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/deployment/precheck | deployment.precheck | query/path | raw/dict | DeploymentRepository | nao |
| POST | /api/v1/deployment/publish | deployment.publish | query/path | raw/dict | DeploymentRepository | nao |
| POST | /api/v1/deployment/rollback | deployment.rollback | query/path | raw/dict | DeploymentRepository | nao |
| POST | /api/v1/deployment/stage | deployment.stage | StageRequest | raw/dict | DeploymentRepository | nao |

##### /documents
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/documents/link-url | documents.link_url | Form | LinkUrlResponse | DocumentIngestionService | nao |
| GET | /api/v1/documents/list | documents.list_documents | query/path | DocListResponse | - | nao |
| GET | /api/v1/documents/search | documents.search_documents | query/path | DocSearchResponse | - | nao |
| GET | /api/v1/documents/status/{doc_id} | documents.document_status | query/path | DocStatusResponse | - | nao |
| POST | /api/v1/documents/upload | documents.upload_document | File, Form | UploadResponse | DocumentIngestionService, KnowledgeService | nao |
| DELETE | /api/v1/documents/{doc_id} | documents.delete_document | query/path | raw/dict | - | nao |

##### /evaluation
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/evaluation/experiments | evaluation.list_experiments | query/path | list[ExperimentResponse] | ABExperimentRepository | nao |
| POST | /api/v1/evaluation/experiments | evaluation.create_experiment | ExperimentCreateRequest | ExperimentResponse | ABExperimentRepository | nao |
| POST | /api/v1/evaluation/experiments/{experiment_id}/arms | evaluation.add_arm | ArmCreateRequest | ArmResponse | ABExperimentRepository | nao |
| POST | /api/v1/evaluation/experiments/{experiment_id}/results | evaluation.add_result | ResultCreateRequest | raw/dict | ABExperimentRepository | nao |
| GET | /api/v1/evaluation/experiments/{experiment_id}/winner | evaluation.experiment_winner | query/path | raw/dict | - | nao |

##### /feedback
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/feedback/ | feedback.record_feedback | FeedbackRequest | FeedbackResponse | - | nao |
| GET | /api/v1/feedback/conversation/{conversation_id} | feedback.get_conversation_feedback | query/path | raw/dict | - | nao |
| GET | /api/v1/feedback/report | feedback.get_satisfaction_report | query/path | SatisfactionReportResponse | - | nao |
| GET | /api/v1/feedback/stats | feedback.get_feedback_stats | query/path | FeedbackStatsResponse | - | nao |
| GET | /api/v1/feedback/suggestions | feedback.get_improvement_suggestions | query/path | raw/dict | - | nao |
| POST | /api/v1/feedback/thumbs-down | feedback.thumbs_down | QuickFeedbackRequest | FeedbackResponse | - | nao |
| POST | /api/v1/feedback/thumbs-up | feedback.thumbs_up | QuickFeedbackRequest | FeedbackResponse | - | nao |

##### /knowledge
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/knowledge/classes/implementations | knowledge.classes_implementations | query/path | list[CodeEntity] | KnowledgeService | nao |
| DELETE | /api/v1/knowledge/clear | knowledge.clear_knowledge_graph | query/path | ClearGraphResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/concepts/reindex | knowledge.reindex_concepts | ReindexRequest | ReindexResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/concepts/related | knowledge.related_concepts | RelatedConceptsRequest | RelatedConceptsResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/consolidate | knowledge.publish_consolidation | ConsolidationRequest | ConsolidationResponse | - | nao |
| POST | /api/v1/knowledge/consolidate/document | knowledge.consolidate_document | DocConsolidationRequest | ConsolidationResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/entities | knowledge.get_code_entities | query/path | list[CodeEntity] | KnowledgeService | nao |
| GET | /api/v1/knowledge/entity/{entity_name}/relationships | knowledge.get_entity_relationships | query/path | EntityRelationshipsResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/files/importing | knowledge.files_importing | query/path | list[CodeEntity] | KnowledgeService | nao |
| GET | /api/v1/knowledge/functions/calling | knowledge.functions_calling | query/path | list[CodeEntity] | KnowledgeService | nao |
| GET | /api/v1/knowledge/health | knowledge.knowledge_health | query/path | KnowledgeHealthResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/health/detailed | knowledge.detailed_health_check | query/path | raw/dict | KnowledgeService | nao |
| POST | /api/v1/knowledge/health/reset-circuit-breaker | knowledge.reset_circuit_breaker | query/path | raw/dict | - | nao |
| POST | /api/v1/knowledge/index | knowledge.trigger_indexing | query/path | IndexResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/node-types | knowledge.get_node_types | query/path | NodeTypesResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/quarantine | knowledge.list_quarantine | query/path | QuarantineListResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/quarantine/promote | knowledge.promote_quarantine | PromoteQuarantineRequest | PromoteQuarantineResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/query | knowledge.query_knowledge | KnowledgeQueryRequest | KnowledgeQueryResponse | KnowledgeService | nao |
| POST | /api/v1/knowledge/relationship-types/register | knowledge.register_relationship_type | RegisterRelTypeRequest | RegisterRelTypeResponse | KnowledgeService | nao |
| GET | /api/v1/knowledge/stats | knowledge.get_knowledge_stats | query/path | raw/dict | KnowledgeService | nao |

##### /learning
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/learning/dataset/preview | learning.preview_dataset | query/path | raw/dict | LearningService | nao |
| GET | /api/v1/learning/dataset/version | learning.get_dataset_version | query/path | DatasetVersionResponse | LearningService | nao |
| POST | /api/v1/learning/evaluate | learning.evaluate_model | EvaluateRequest | EvaluationResponse | LearningService | nao |
| GET | /api/v1/learning/experiments | learning.list_experiments | query/path | ExperimentListResponse | LearningService | nao |
| GET | /api/v1/learning/experiments/{experiment_id} | learning.get_experiment_details | query/path | ExperimentInfo | LearningService | nao |
| POST | /api/v1/learning/harvest | learning.trigger_harvesting | HarvestRequest | LearningResponse | LearningService | nao |
| GET | /api/v1/learning/health | learning.learning_health | query/path | raw/dict | LearningService | nao |
| GET | /api/v1/learning/models | learning.list_models | query/path | ModelListResponse | LearningService | nao |
| GET | /api/v1/learning/models/{model_id} | learning.get_model_details | query/path | ModelInfo | LearningService | nao |
| GET | /api/v1/learning/stats | learning.get_learning_stats | query/path | raw/dict | LearningService | nao |
| POST | /api/v1/learning/train | learning.trigger_training | TrainRequest | TrainingAckResponse | LearningService | nao |
| GET | /api/v1/learning/training/status | learning.get_training_status | query/path | TrainingStatusResponse | LearningService | nao |

##### /llm
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/llm/ab/set-experiment | llm.set_ab_experiment | ABExperimentSetRequest | raw/dict | - | nao |
| GET | /api/v1/llm/budget/summary | llm.get_budget_summary | query/path | raw/dict | - | nao |
| POST | /api/v1/llm/cache/invalidate | llm.invalidate_llm_cache | query/path | raw/dict | LLMService | nao |
| GET | /api/v1/llm/cache/status | llm.get_cache_status | query/path | LLMCacheStatusResponse | LLMService | nao |
| GET | /api/v1/llm/circuit-breakers | llm.get_circuit_breaker_status | query/path | list[CircuitBreakerStatus] | LLMService | nao |
| POST | /api/v1/llm/circuit-breakers/{provider}/reset | llm.reset_circuit_breaker | query/path | raw/dict | LLMService | nao |
| GET | /api/v1/llm/health | llm.llm_health | query/path | raw/dict | LLMService | nao |
| POST | /api/v1/llm/invoke | llm.invoke_llm | LLMInvokeRequest | LLMInvokeResponse | LLMService | nao |
| GET | /api/v1/llm/pricing/providers | llm.get_provider_pricing | query/path | raw/dict | - | nao |
| GET | /api/v1/llm/providers | llm.list_llm_providers | query/path | raw/dict | LLMService | nao |
| POST | /api/v1/llm/response-cache/invalidate | llm.invalidate_response_cache | InvalidateResponseCacheRequest | raw/dict | LLMService | nao |
| GET | /api/v1/llm/response-cache/status | llm.get_response_cache_status | query/path | LLMCacheStatusResponse | LLMService | nao |

##### /memory
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/memory/generative | memory.get_generative_memories | query/path | list[ScoredExperience] | - | nao |
| POST | /api/v1/memory/generative | memory.add_generative_memory | query/path | Experience | - | nao |
| GET | /api/v1/memory/timeline | memory.get_memories_timeline | query/path | list[ScoredExperience] | MemoryService | nao |

##### /meta-agent
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/meta-agent/analyze | meta_agent.run_analysis | query/path | raw/dict | MetaAgentService | nao |
| GET | /api/v1/meta-agent/health | meta_agent.health_check | query/path | raw/dict | MetaAgentService | nao |
| POST | /api/v1/meta-agent/heartbeat/start | meta_agent.start_heartbeat | StartHeartbeatRequest | raw/dict | MetaAgentService | nao |
| GET | /api/v1/meta-agent/heartbeat/status | meta_agent.get_heartbeat_status | query/path | raw/dict | MetaAgentService | nao |
| POST | /api/v1/meta-agent/heartbeat/stop | meta_agent.stop_heartbeat | query/path | raw/dict | MetaAgentService | nao |
| GET | /api/v1/meta-agent/report/latest | meta_agent.get_latest_report | query/path | raw/dict | MetaAgentService | nao |

##### /observability
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/observability/activity/user | observability.user_activity | query/path | UserActivityResponse | ObservabilityService | nao |
| GET | /api/v1/observability/graph/audit | observability.graph_audit | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/graph/quarantine | observability.graph_quarantine_list | query/path | raw/dict | ObservabilityService | nao |
| POST | /api/v1/observability/graph/quarantine/promote | observability.graph_quarantine_promote | PromoteQuarantineRequest | raw/dict | ObservabilityService | nao |
| POST | /api/v1/observability/health/check-all | observability.check_all_components | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/health/components/llm_manager | observability.health_llm_manager | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/health/components/multi_agent_system | observability.health_multi_agent | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/health/components/poison_pill_handler | observability.health_poison_pill_handler | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/health/system | observability.get_system_health | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/llm/usage | observability.llm_usage | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/metrics/summary | observability.get_metrics_summary | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/metrics/user | observability.user_metrics | query/path | UserMetricsResponse | ObservabilityService | nao |
| POST | /api/v1/observability/metrics/ux | observability.record_ux_metric | UxMetricItem | raw/dict | ObservabilityService | nao |
| POST | /api/v1/observability/poison-pills/cleanup | observability.cleanup_quarantine | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/poison-pills/quarantined | observability.get_quarantined_messages | query/path | raw/dict | ObservabilityService | nao |
| POST | /api/v1/observability/poison-pills/release | observability.release_from_quarantine | ReleaseQuarantineRequest | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/poison-pills/stats | observability.get_poison_pill_stats | query/path | raw/dict | ObservabilityService | nao |
| GET | /api/v1/observability/user_summary | observability.user_summary | query/path | UserSummaryResponse | - | nao |

##### /optimization
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/optimization/analyze | optimization.analyze_system | query/path | SystemAnalysisResponse | OptimizationService | sim |
| GET | /api/v1/optimization/health | optimization.get_system_health | query/path | SystemHealthResponse | OptimizationService | sim |
| GET | /api/v1/optimization/issues | optimization.get_detected_issues | query/path | list[DetectedIssueResponse] | OptimizationService | sim |
| GET | /api/v1/optimization/metrics/history | optimization.get_metrics_history | query/path | raw/dict | OptimizationService | sim |
| POST | /api/v1/optimization/run-cycle | optimization.run_optimization_cycle | OptimizationCycleRequest | OptimizationCycleResponse | OptimizationService | sim |
| GET | /api/v1/optimization/status | optimization.get_optimization_status | query/path | raw/dict | OptimizationService | sim |

##### /pending_actions
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/pending_actions/ | pending_actions.list_pending | query/path | List[PendingActionDTO] | - | nao |
| POST | /api/v1/pending_actions/{thread_id}/approve | pending_actions.approve | query/path | PendingActionDTO | - | nao |
| POST | /api/v1/pending_actions/{thread_id}/reject | pending_actions.reject | query/path | PendingActionDTO | - | nao |

##### /productivity
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/productivity/calendar/events | productivity.calendar_list_events | query/path | raw/dict | ConsentRepository | sim |
| POST | /api/v1/productivity/calendar/events/add | productivity.calendar_add_event | CalendarAddRequest | raw/dict | ConsentRepository | sim |
| GET | /api/v1/productivity/limits/status | productivity.limits_status | query/path | raw/dict | - | sim |
| GET | /api/v1/productivity/mail/messages | productivity.mail_list | query/path | raw/dict | ConsentRepository | sim |
| POST | /api/v1/productivity/mail/messages/send | productivity.mail_send | MailSendRequest | raw/dict | ConsentRepository | sim |
| GET | /api/v1/productivity/notes | productivity.notes_list | query/path | raw/dict | ConsentRepository | sim |
| POST | /api/v1/productivity/notes/add | productivity.notes_add | NoteAddRequest | raw/dict | ConsentRepository | sim |
| POST | /api/v1/productivity/oauth/google/callback | productivity.google_oauth_callback, productivity.oauth_google_callback | GoogleOAuthCallbackRequest, OAuthCallbackRequest | raw/dict | - | sim |
| POST | /api/v1/productivity/oauth/google/refresh | productivity.google_oauth_refresh, productivity.oauth_google_refresh | OAuthRefreshRequest | raw/dict | - | sim |
| GET | /api/v1/productivity/oauth/google/start | productivity.google_oauth_start | query/path | raw/dict | - | sim |
| POST | /api/v1/productivity/oauth/google/start | productivity.oauth_google_start | OAuthStartRequest | raw/dict | - | sim |

##### /profiles
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/profiles/ | profiles.upsert_profile | UpsertProfileRequest | ProfileResponse | ProfileRepository | nao |
| GET | /api/v1/profiles/{user_id} | profiles.get_profile | query/path | ProfileResponse | ProfileRepository | nao |

##### /rag
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/rag/hybrid_search | rag.rag_hybrid_search | query/path | RAGHybridResponse | MemoryService | nao |
| GET | /api/v1/rag/productivity | rag.rag_productivity_search | query/path | RAGProductivityResponse | - | nao |
| GET | /api/v1/rag/search | rag.rag_search | query/path | RAGSearchResponse | MemoryService | nao |
| GET | /api/v1/rag/user-chat | rag.rag_user_chat_search | query/path | RAGUserChatResponse | - | nao |
| GET | /api/v1/rag/user_chat | rag.rag_user_chat_search_v2 | query/path | RAGUserChatResponseV2 | - | nao |

##### /reflexion
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/reflexion/config | reflexion.get_reflexion_config | query/path | raw/dict | ReflexionService | nao |
| POST | /api/v1/reflexion/execute | reflexion.execute_with_reflexion | ReflexionRequest | ReflexionResponse | ReflexionService | nao |
| GET | /api/v1/reflexion/health | reflexion.reflexion_health | query/path | raw/dict | ReflexionService | nao |
| POST | /api/v1/reflexion/reset-circuit-breaker | reflexion.reset_circuit_breaker | query/path | raw/dict | ReflexionService | nao |
| GET | /api/v1/reflexion/summary/post_sprint | reflexion.get_post_sprint_summary | query/path | PostSprintSummaryResponse | MemoryService, MetaAgentService | nao |

##### /sandbox
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/sandbox/capabilities | sandbox.get_sandbox_capabilities | query/path | raw/dict | SandboxService | nao |
| POST | /api/v1/sandbox/evaluate | sandbox.evaluate_expression | ExpressionRequest | raw/dict | SandboxService | nao |
| POST | /api/v1/sandbox/execute | sandbox.execute_code | CodeExecutionRequest | raw/dict | SandboxService | nao |

##### /system
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/system/db/migrate | system_status.migrate_db_schema | query/path | raw/dict | - | nao |
| GET | /api/v1/system/db/validate | system_status.validate_db_schema | query/path | raw/dict | - | nao |
| GET | /api/v1/system/health/services | system_status.get_services_health | query/path | ServiceHealthResponse | KnowledgeService, LLMService, ObservabilityService, OptimizationService | nao |
| GET | /api/v1/system/overview | system_overview.get_system_overview | query/path | SystemOverviewResponse | KnowledgeService, LLMService, ObservabilityService, OptimizationService | nao |
| GET | /api/v1/system/status | system_status.get_system_status | query/path | StatusResponse | - | nao |
| GET | /api/v1/system/status/user | system_status.get_user_status | query/path | UserStatusResponse | ObservabilityService | nao |

##### /tasks
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/tasks/consolidation | tasks.create_consolidation_task | ConsolidationTaskRequest | TaskResponse | TaskService | nao |
| GET | /api/v1/tasks/health/rabbitmq | tasks.check_rabbitmq_health | query/path | raw/dict | TaskService | nao |
| GET | /api/v1/tasks/queue/{queue_name} | tasks.get_queue_info | query/path | QueueInfoResponse | TaskService | nao |
| GET | /api/v1/tasks/queue/{queue_name}/policy | tasks.get_queue_policy | query/path | QueuePolicyResponse | TaskService | nao |
| POST | /api/v1/tasks/queue/{queue_name}/policy/reconcile | tasks.reconcile_queue_policy | ReconcilePolicyRequest | ReconcilePolicyResponse | TaskService | nao |
| GET | /api/v1/tasks/queue/{queue_name}/policy/validate | tasks.validate_queue_policy | query/path | QueuePolicyValidationResponse | TaskService | nao |

##### /tools
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/tools/ | tools.list_tools | query/path | ToolListResponse | ToolService | nao |
| GET | /api/v1/tools/categories/list | tools.list_categories | query/path | raw/dict | ToolService | nao |
| POST | /api/v1/tools/create/from-api | tools.create_tool_from_api | CreateToolFromApiRequest | ToolInfo | ToolService | nao |
| POST | /api/v1/tools/create/from-function | tools.create_tool_from_function | CreateToolFromFunctionRequest | ToolInfo | ToolService | nao |
| GET | /api/v1/tools/permissions/list | tools.list_permissions | query/path | raw/dict | ToolService | nao |
| GET | /api/v1/tools/stats/usage | tools.get_tool_statistics | query/path | ToolStatsResponse | ToolService | nao |
| DELETE | /api/v1/tools/{tool_name} | tools.delete_tool | query/path | raw/dict | ToolService | nao |
| GET | /api/v1/tools/{tool_name} | tools.get_tool_details | query/path | ToolInfo | ToolService | nao |

##### /users
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/users/ | users.create_user | CreateUserRequest | UserResponse | UserRepository | nao |
| GET | /api/v1/users/{user_id} | users.get_user | query/path | UserResponse | UserRepository | nao |
| GET | /api/v1/users/{user_id}/consents | users.list_consents | query/path | raw/dict | ConsentRepository | nao |
| POST | /api/v1/users/{user_id}/consents | users.add_consent | ConsentRequest | ConsentResponse | ConsentRepository | nao |
| DELETE | /api/v1/users/{user_id}/consents/{scope} | users.revoke_consent | query/path | raw/dict | ConsentRepository | nao |
| POST | /api/v1/users/{user_id}/roles | users.assign_role | AssignRoleRequest | raw/dict | UserRepository | nao |

##### /workers
| Metodo | Path | Handler | Payload | Resposta | Servicos/Repos | Duplicado |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/workers/start-all | workers.start_workers | query/path | raw/dict | - | nao |
| GET | /api/v1/workers/status | workers.workers_status | query/path | raw/dict | - | nao |
| POST | /api/v1/workers/stop-all | workers.stop_workers | query/path | raw/dict | - | nao |

2) **Contratos e validacoes (Pydantic)**
   - models/schemas.py usado apenas em memory (Experience, ScoredExperience) e tasks (QueueName); o restante define DTOs locais.
   - Inputs livres/sensiveis sem limites claros:
     - /llm/invoke, /chat/message, /assistant/execute: prompt/message sem max_length (risco de custo/abuso).
     - /tools/create/from-function: code sem limite/validacao sintatica; /tools/create/from-api sem validacao de URL/headers.
     - /sandbox/execute e /sandbox/evaluate: codigo/expressao arbitrarios (exige hard gate e limites).
     - /documents/upload: tamanho limitado, mas sem whitelist MIME/extensao e sem scan.
     - /tasks/consolidation: metadata livre (dict) sem schema estrito.
     - /rag/* e /knowledge/*: query livre; falta sanitizacao e limites por usuario.
   - Ponto positivo: Autonomy valida plan steps e AgentExecutionRequest tem max_length.

3) **Performance HTTP e middlewares**
   - Middlewares globais: SecurityHeadersMiddleware, CorrelationMiddleware, RateLimitMiddleware, CORS, msgpack negotiation, Prometheus instrumentator.
   - RateLimit: token-bucket no Redis, fail-open se Redis cair; bypass apenas para /metrics, /healthz, /livez, /readyz.
   - msgpack negotiation faz JSON decode/encode quando Accept=application/msgpack; custo extra em respostas grandes.
   - /system/overview e /system/health/services fazem chamadas sequenciais; pode paralelizar para reduzir latencia.
   - SSE (/chat/stream, /chat/{id}/events) nao passa por msgpack, OK.

4) **Governanca e versionamento**
   - Rotas fora de /api/v1: /, /health, /healthz, /metrics, /static.
   - Endpoints com codigo, mas nao registrados: admin_graph, meta, resources.
   - Duplicidade de include_router em /optimization e /productivity (duplica routes e OpenAPI).
   - Inconsistencia de naming: /rag/user-chat vs /rag/user_chat; /pending_actions; /auto-analysis.

5) **Seguranca de API (chaves e headers)**
   - X-API-Key e opcional; quando ausente, API inteira fica exposta.
   - actor_user_id aceita X-User-Id sem verificacao; permite impersonacao se API key for compartilhada.
   - Endpoints criticos sem auth/admin:
     /system/db/migrate, /system/db/validate, /workers/start-all, /workers/stop-all,
     /collaboration/system/shutdown, /sandbox/execute, /tools/create/*, /knowledge/clear,
     /knowledge/index, /observability/poison-pills/*, /optimization/analyze/run-cycle,
     /llm/ab/set-experiment, /llm/cache/*, /llm/response-cache/*, /tasks/queue/*/policy/reconcile.
   - Recomendacao: separar rotas admin, exigir JWT/role, remover fallback X-User-Id, aplicar allowlist por metodo.

6) **Checklist de custos para endpoints LLM**
   - Core LLM tem budgets, mas user_id/project_id vem do payload; sem autenticar identidade, limites podem ser burlados.
   - RateLimitMiddleware e por IP/API key, nao por custo/tenant.
   - Chat/Assistant/Agent usam caminho LLM; precisam herdar identidade autenticada para custo real.
   - /llm/budget/summary e /llm/pricing/providers expostos; ideal restringir a admin.

#### Tasks

* [ ] Remover duplicidades de rotas (/optimization/* e /productivity/*)
* [ ] Decidir destino de rotas não expostas no router v1 (admin_graph/meta/resources)
* [ ] Padronizar naming de rotas e estabilizar compatibilidade (ex: /rag/user-chat → /rag/user_chat)
* [ ] Definir limites de tamanho para inputs livres (prompt/message/code/query) por endpoint
* [ ] Validar URL/headers em /tools/create/from-api e impor limites em /tools/create/from-function
* [ ] Hard gate de endpoints críticos com JWT/role (admin) e remover fallback X-User-Id
* [ ] Tornar X-API-Key obrigatória quando não houver JWT (remover modo exposto por padrão)
* [ ] Restringir endpoints administrativos de custo e cache (/llm/budget/summary, /llm/pricing/providers, /llm/*cache*)
* [ ] Adicionar allowlist MIME/extensão e varredura em /documents/upload
* [ ] Paralelizar chamadas em /system/overview e /system/health/services
* [ ] Propagar enforcement de budget (USD) para o gateway HTTP por usuário/tenant

### Lote 3 - Servicos (LLM, Chat, RAG, Observabilidade, Autonomia) (EM ANDAMENTO)

**Objetivo**: mapear a camada de servicos e explicitar pendencias criticas no fluxo do coracao do Janus.

#### Tasks

* [ ] Impor limites de tamanho no LLMService (prompt + output)
* [ ] Impor limites de tamanho no ChatService (message + attachments)
* [ ] Padronizar registro/estimativa de custo no caminho Chat → LLM
* [ ] Validar ownership de conversas no serviço e no repositório SQL
* [ ] Tornar user_id/project_id obrigatórios e server-side antes de RAG/LLM
* [ ] Persistir eventos do ChatEventPublisher (evitar db_logger=None silencioso)
* [ ] Expor telemetria de degradação em RAG e sumarização (falha explícita)
* [ ] Implementar backoff, limites e cancelamento no AutonomyLoop
* [ ] Unificar interfaces de repositórios usadas por ChatService e RAGService
* [ ] Centralizar resolução de identidade antes de chamar LLM/RAG/Autonomy

### Lote 4 - Repositorios e persistencia (EM ANDAMENTO)

**Objetivo**: mapear repositorios, fontes de dados e contratos de persistencia, destacando inconsistencias e dividas tecnicas.

#### Tasks

* [ ] Padronizar sessão do Postgres (100% async ou engine sync dedicado)
* [ ] Corrigir chamadas a db.get_session_direct (método inexistente) nos repositórios
* [ ] Alinhar ChatRepositorySQL com a infra de banco (evitar Session sync incompatível)
* [ ] Reescrever PromptRepository para fluxo coerente (async) ou separar sync/async
* [ ] Persistir collaboration/tool/optimization/context/sandbox repositories (evitar perda em restart)
* [ ] Persistir learning stats/experimentos (evitar perda parcial)
* [ ] Remover ou arquivar chat_repository file-based se não for usado
* [ ] Definir estratégia de consistência entre SQL, Qdrant e Neo4j (sem UoW)
* [ ] Adicionar retries/timeouts e confirmação em exclusões cross-store
* [ ] Tipar retornos de Memory/Knowledge repos e padronizar erros no nível repo
* [ ] Finalizar Alembic e garantir migrations para modelos novos (ex: ModelDeployment)
* [ ] Remover db.create_tables do boot em produção

### Lote 5 - Agentes, Ferramentas e Sandbox (EM ANDAMENTO)

**Objetivo**: mapear orquestracao de agentes, tool-calls e sandbox, destacando falhas de policy, execucao e isolamento.

#### Tasks

* [ ] Aplicar PolicyEngine, rate limit e confirmação em todas tool-calls do chat
* [ ] Garantir action_registry.record_call no fluxo de tool-calls (telemetria completa)
* [ ] Corrigir fallback do ChatAgentLoop (execute_tool_calls não aceita strict)
* [ ] Adicionar timeout e limite de concorrência por tool no ToolExecutorService
* [ ] Corrigir awaits ausentes em core/autonomy/planner.py (draft/critique/refine/replan/verify)
* [ ] Cobrir planner/autonomia com teste de regressão (coroutine/await)
* [ ] Unificar sandbox e integrar executor Docker ao fluxo de serviços
* [ ] Alinhar SandboxService.get_capabilities com enforcement real (timeout/CPU/mem/output)
* [ ] Persistir rate limit e stats por usuário/tenant (Redis/DB) e padronizar fluxo HITL

### Proximo passo apos Lote 5
- Lote 6: TBD (definir escopo).
