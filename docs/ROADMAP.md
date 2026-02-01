# 🗺️ Janus Roadmap & Technical Debt (V1 Launch)
>
> *Última atualização: 14/01/2026 (Scientific & V1 Focus)*

Este documento define o caminho crítico para o lançamento da **Janus V1**, priorizando robustez, embasamento científico e prontidão para produção.

## 📌 Índice

- Backlog por Dificuldade (Throughput / Médias / Difíceis)
- Scientific Foundation (State-of-the-Art)
- Scientific Frontier (Post-V1 Evolution)
- Infrastructure Strategy (Phase 3)
- V1 Critical Path (Launch Blockers)
- Histórico de Conclusões (Arquivado)

> **Nota:** Os levantamentos técnicos detalhados e o inventário de rotas foram movidos para [docs/INVENTORY.md](INVENTORY.md).

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
