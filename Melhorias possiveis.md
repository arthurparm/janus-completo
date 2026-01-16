# 🗺️ Janus Roadmap & Technical Debt (V1 Launch)
>
> *Última atualização: 14/01/2026 (Scientific & V1 Focus)*

Este documento define o caminho crítico para o lançamento da **Janus V1**, priorizando robustez, embasamento científico e prontidão para produção.

---

## 🔬 Scientific Foundation (State-of-the-Art)

*Arquitetura baseada em 13+ papers seminais que fundamentam a inteligência do Janus.*

### 🧠 Reasoning & Planning (O Cérebro)

1. **LATS (Language Agent Tree Search)** - *Zhou et al., 2023*
    * **Conceito**: Combina LLM com Monte Carlo Tree Search (MCTS) para explorar múltiplos caminhos de solução.
    * **No Janus**: Nó `Planner` que simula cenários antes de executar ações críticas (ex: deploy).
2. **Reflexion** - *Shinn et al., 2023*
    * **Conceito**: Agentes que verbalizam erros e guardam lições em memória de curto prazo.
    * **No Janus**: Loop de auto-correção no `CoderAgent` para erros de compilação.
3. **Graph of Thoughts (GoT)** - *Besta et al., 2023*
    * **Conceito**: Modela o pensamento como um grafo (DAG), permitindo combinar e refinar ideias.
    * **No Janus**: Orquestração não-linear no LangGraph (Supervisor Node).
4. **Tree of Thoughts (ToT)** - *Yao et al., 2023*
    * **Conceito**: Exploração deliberada de múltiplos ramos de raciocínio.
    * **No Janus**: Base para o processo de decisão do `Meta-Agent`.
5. **Chain of Thought (CoT)** - *Wei et al., 2022*
    * **Conceito**: "Let's think step by step".
    * **No Janus**: Padrão obrigatório em todos os prompts de sistema.

### 💾 Memory & Learning (A Alma)

1. **Generative Agents** - *Park et al., 2023*
    * **Conceito**: Memória com Recência, Importância e Relevância + "Sonho" (Consolidação).
    * **No Janus**: Arquitetura do `MemoryService` e worker noturno de consolidação no Neo4j.
2. **MemGPT** - *Packer et al., 2023*
    * **Conceito**: Gestão de contexto infinito via paginação (OS-like memory management).
    * **No Janus**: Estratégia de paginação de contexto para conversas longas.
3. **Voyager** - *Wang et al., 2023*
    * **Conceito**: Aprendizado contínuo via biblioteca de habilidades (Skill Library).
    * **No Janus**: Persistência de ferramentas e scripts de sucesso para reuso.

### 🔍 Retrieval & RAG (O Conhecimento)

1. **Self-RAG** - *Asai et al., 2023*
    * **Conceito**: O modelo critica sua própria recuperação (`[IsREL]`, `[IsSUP]`).
    * **No Janus**: Pipeline de `NativeGraphRAG` com etapa de verificação.
2. **HyDE (Hypothetical Document Embeddings)** - *Gao et al., 2022*
    * **Conceito**: Gerar resposta ideal hipótetica para buscar documentos similares.
    * **No Janus**: Melhoria na busca vetorial do Qdrant.
3. **RAPTOR** - *Sarthi et al., 2024*
    * **Conceito**: Indexação recursiva em árvore (resumos de resumos).
    * **No Janus**: Estrutura hierárquica de conhecimento no Neo4j.

### 🤖 Multi-Agent (O Corpo)

1. **MetaGPT** - *Hong et al., 2023*
    * **Conceito**: SOPs (Standard Operating Procedures) codificados para agentes.
    * **No Janus**: Definição rígida de papéis (Product Manager, Architect, Engineer).
2. **CAMEL** - *Li et al., 2023*
    * **Conceito**: Arquitetura de "Role-Playing" para comunicação comunicativa.
    * **No Janus**: Protocolo de comunicação entre Supervisor e Workers.

### 🛡️ Safety & Alignment (A Consciência)

1. **Constitutional AI** - *Bai et al., 2022 (Anthropic)*
    * **Conceito**: Controle de comportamento através de uma "Constituição" (regras naturais) em vez de RLHF manual extensivo.
    * **No Janus**: Extensão do `ReflectorAgent` para validar outputs contra regras de segurança (`security.yaml`) antes da entrega.

### ⚡ Optimization & Economy (A Eficiência)

1. **FrugalGPT (LLM Cascades)** - *Chen et al., 2023*
    * **Conceito**: Chamar modelos menores/baratos primeiro; escalar para modelos SOTA apenas se a confiança for baixa.
    * **No Janus**: `ModelRouter` na infraestrutura que tenta resolver com Llama-3-Locall/Mini antes de chamar DeepSeek/GPT-4.
2. **DSPy (Programming with Prompts)** - *Khattab et al., 2023*
    * **Conceito**: Abstrair prompts como parâmetros otimizáveis. O sistema "compila" e melhora seus próprios prompts baseado em métricas.
    * **No Janus**: Pipeline de auto-ajuste dos prompts dos Workers baseado no feedback de erro/sucesso.

### 🎨 HCI & Experience (A Interface)

1. **Generative UI** - *Vercel AI SDK v5 / Dynaboard*
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

* [ ] **Security Headers Middleware**: Implementar CSP, HSTS, X-Frame-Options e X-Content-Type-Options.

* [ ] **Input Sanitization**: Validar e sanitizar todos os inputs da API (prevenção de injeção).
* [ ] **Rate Limiting (Cost-Based)**: Limitar usuários por **gasto em dólares**, não apenas requisições.
* [ ] **Audit Log Imutável**: Garantir que logs de ações críticas não possam ser alterados.

### 🖥️ Frontend V1 (Refactor & Finish)

* [ ] **UI Overhaul (Clean/Professional)**: Migrar de "Magicpunk" para uma estética SaaS profissional/minimalista (Shadcn/UI + Tailwind).
* [ ] **Complete UI Coverage**: Implementar telas faltantes (80%+) seguindo o novo Design System (Tools, Workers, RAG).

* [ ] **UX Improvements**:
  * Real-time Feedback (Toasts globais).
  * Onboarding Flow (Wizard de setup).
  * Tratamento de erros amigável.

#### 🐛 Critical Bugs & Failures (Prioridade Alta)

* [ ] **Broken Thought Stream**: O stream de pensamentos do agente (SSE) não está recebendo eventos do RabbitMQ (Tela de Chat).
* [ ] **Autonomy 500 Error**: Erro interno de servidor (500) impossibilita criação de Objetivos Estratégicos.
* [ ] **State Desync**: Falta de reatividade entre Backend (Redis) e Frontend (NgRx/Signals).

#### 🏚️ Technical Debt & Clean Code

* [ ] **Linter Bankruptcy**: `eslint-report.json` gigante (>400KB). Necessário correção massiva e regras mais estritas.
* [ ] **Hardcoded Settings**: Remover chaves e URLs hardcoded; mover para `environment.ts`.
* [ ] **Test Coverage Zero**: Não há testes de unidade ou e2e rodando no frontend atualmente.
* [x] **Legacy Testing Stack**: Atualizar de Karma/Jasmine para Vitest/Jest + Testing Library (Padrão 2026).
* [ ] **Ad-hoc State Management**: Substituir `GlobalStateStore` (Signals manuais com high cognitive load) por uma lib robusta (NgRx SignalStore ou Elf) para evitar "State Desync".
* [ ] **Design System Conflict**: Remover Angular Material gradual e unificar no Shadcn/UI (Tailwind) para reduzir bundle size e inconsistências visuais.

### ⚙️ Stability & Ops

* [ ] **Database Migration Pipeline**: Finalizar transição para Alembic (abandonar scripts manuais).

* [ ] **Smart Model Routing**: Router que escolhe entre Local/API baseado na complexidade da task (Economia).
* [ ] **Graceful Degradation**: Fallbacks claros quando serviços (ex: Redis, Neo4j) caem.

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

## 🧱 Levantamento em Lotes (Arquitetura e Melhorias)

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

- **Paralelizar carga de prompts** (reduz latência de cold start).
- **Indexação incremental** baseada em hash/commit (evita O(N) desnecessário).
- **Feature flags para workers** por ambiente (reduz custo operacional).
- **Container de DI leve** para reduzir acoplamento e melhorar testabilidade.

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
Observacao: caminhos listados ja incluem o prefixo `/api/v1`.
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

### Lote 3 - Servicos (LLM, Chat, RAG, Observabilidade, Autonomia) (EM ANDAMENTO)

**Objetivo**: mapear a camada de servicos e explicitar pendencias criticas no fluxo do coracao do Janus.

#### Pontas a resolver

1) **Guardrails de input e custo**
   - LLMService nao imp?e limite de tamanho de prompt; depende do endpoint/prompt_builder -> risco de custo/abuso.
   - ChatService (send_message) nao valida max_bytes; apenas o fluxo SSE aplica limite.
   - ChatService estima custo com _provider_pricing (best-effort) e pode divergir do custo real registrado no core LLM.

2) **Identidade e RBAC**
   - send_message/get_history usam get_conversation sem validar ownership; dependem do endpoint para RBAC.
   - ChatRepositorySQL nao valida ownership no get_conversation; se conversation_id vazar, acesso e possivel.
   - RAG indexa/recupera apenas com user_id; sem user_id o comportamento fica inconsistente (sem contexto e sem indexacao).

3) **Observabilidade e resiliencia**
   - ChatEventPublisher inicia com db_logger=None; eventos nao persistem e perdem rastreabilidade.
   - RAG e sumarizacao sao best-effort e silenciam falhas; falta telemetria explicita de degrados.
   - AutonomyLoop nao tem backoff/limites por falha; pode gerar ciclos ruidosos e custos indesejados.

4) **Consistencia entre servicos**
   - ChatService usa ChatRepositorySQL, mas RAGService recebe ChatRepository (interface diferente) e depende de adaptacao implicita.
   - Identidade do usuario (user_id/project_id) e passada pelo payload; falta validacao server-side consistente entre servicos.

5) **Acoes recomendadas**
   - Unificar limites de tamanho (chat e LLM) e aplicar validacao no servico, nao apenas no endpoint.
   - Reforcar RBAC no servico (ChatService) e garantir ownership no repositorio.
   - Persistir eventos de chat e expor metricas de falhas RAG/sumarizacao.
   - Centralizar resolucao de identidade do usuario (token -> user_id) antes de chamar LLM/RAG/Autonomy.

### Lote 4 - Repositorios e persistencia (EM ANDAMENTO)

**Objetivo**: mapear repositorios, fontes de dados e contratos de persistencia, destacando inconsistencias e dividas tecnicas.

#### Pontas a resolver

1) **Sessao/DI quebrado no Postgres**
   - db alias aponta para PostgresDatabase async, mas repositorios sync chamam db.get_session_direct (metodo inexistente).
   - ChatRepositorySQL usa Session sync enquanto a infra principal e async; risco de conexoes e locks inconsistentes.
   - PromptRepository mistura metodos async e sync: _get_session e async mas e chamado em metodos sync.

2) **Persistencia fragmentada**
   - collaboration_repository, tool_repository, optimization_repository, context_repository e sandbox_repository sao volateis (perda total em restart).
   - learning_repository guarda stats/experimentos em memoria e apenas modelos no filesystem -> perda parcial.
   - chat_repository file-based existe mas Kernel usa ChatRepositorySQL; risco de dados divergentes/abandonados.

3) **Consistencia cross-store**
   - Nao ha unidade de trabalho entre SQL, Qdrant e Neo4j; exclusoes usam sync_events best-effort sem retry/confirmacao.
   - ObservabilityRepository mistura SQL e Qdrant em chamadas sem timeouts dedicados.
   - Memory/Knowledge repos retornam dicts sem tipagem forte; erros propagam sem estrategia de retry no nivel repo.

4) **Migrations e schema**
   - ModelDeployment e outros modelos novos nao tem garantia de migration (Alembic nao finalizado).
   - db.create_tables no startup cria tabelas dinamicamente, mas repositorios usam sessao sync (incompatibilidade).

5) **Acoes recomendadas**
   - Padronizar sessao: ou 100% async (AsyncSession) ou criar engine sync dedicado com get_session_direct real.
   - Reescrever PromptRepository para fluxo 100% async (ou separar repos sync/async).
   - Persistir workspace/multi-agent e tool registry em DB/Redis para sobreviver a restart.
   - Formalizar migrations (Alembic) para modelos novos e remover create_tables do boot em prod.

### Lote 5 - Agentes, Ferramentas e Sandbox (EM ANDAMENTO)

**Objetivo**: mapear orquestracao de agentes, tool-calls e sandbox, destacando falhas de policy, execucao e isolamento.

#### Pontas a resolver

1) **Tool-calls sem policy no fluxo de chat**
   - ToolExecutorService executa tools sem PolicyEngine, sem check_rate_limit e sem requires_confirmation.
   - ChatAgentLoop usa ToolExecutorService diretamente; tool calls do LLM bypassam RBAC e confirmacao.
   - action_registry.record_call nao e chamado nesse fluxo; telemetria e rate limit ficam incompletos (por processo, nao por usuario).

2) **Fallback quebrado e execucao sem guardrails**
   - ChatAgentLoop._execute_tools_with_fallback chama execute_tool_calls(..., strict=False), mas o metodo nao aceita strict -> erro no fallback.
   - ToolExecutorService nao aplica timeout nem limite de concorrencia por tool; risco de bloqueio e custos.

3) **Planner/Replanner com awaits ausentes**
   - core/autonomy/planner.py chama llm_service.invoke_llm sem await (draft/critique/refine/replan/verify), retornando coroutine.
   - Resultado: build_plan_for_goal tende a cair em fallback e a verificacao semantica perde efeito.

4) **Sandbox divergente e limites nao enforceados**
   - APIs e tools usam python_sandbox in-process; nao ha timeout/CPU/mem limit real (apenas truncamento de output).
   - Existe SandboxExecutor com Docker (isolamento real), mas nao esta integrado ao fluxo de service/repo.
   - SandboxService.get_capabilities informa timeout/max_output_length fixos que nao batem com enforcement real.

5) **Acoes recomendadas**
   - Centralizar execucao de tools em um executor unico que aplique PolicyEngine, rate limit, confirmacao e telemetria.
   - Corrigir assinatura de execute_tool_calls e adicionar timeout/concorrencia por tool.
   - Ajustar planner.py para await em invoke_llm e cobrir com testes de regressao.
   - Unificar sandbox (preferir Docker) e alinhar get_capabilities com limites reais.
   - Persistir rate limit e stats por usuario/tenant (Redis/DB) e padronizar fluxo HITL.

### Proximo passo apos Lote 5
- Lote 6: TBD (definir escopo).
