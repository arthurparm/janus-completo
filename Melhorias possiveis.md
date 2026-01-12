# Melhorias Possíveis (Roadmap Janus)

Este documento rastreia dívidas técnicas, melhorias de arquitetura e funcionalidades planejadas.

## Visão Geral

- Itens marcados com `[x]` já foram entregues.
- Itens com `[ ]` fazem parte do backlog.
- As seções estão agrupadas por domínio (segurança, performance, backend, frontend, etc.).

## Índice por Área

- ✅ Concluídas (Entregas Recentes)
- 🚨 Alta Prioridade & Riscos Críticos
- 🧠 Autonomia & Arquitetura Agêntica (SOTA 2025)
- 🏗️ Backend & Infraestrutura
- 🎨 Frontend (Angular)
- 📚 Documentação & Processos
- 🔄 Parlamento (Multi-Agent Pipeline) — Auditoria Jan/2026
- 🛡️ Resiliência & Messaging — Auditoria Jan/2026
- 🖥️ Frontend — Gaps Operacionais
- 🌐 Pesquisa & Inovação (Requere Internet/SOTA)
- 🤖 Recomendação de Modelos (2025/2026)
- 🏛️ Evolução Arquitetural (Pós-DeepSeek)
- 🧪 Testing & Quality Assurance — Gaps Identificados
- 🌙 Evolution & Dream Mode — Melhorias no Sistema de Auto-Evolução

## ✅ Concluídas (Entregas Recentes)

- [x] **SOTA Planning (Reflexion)**: O `planner.py` implementa um pipeline **Reflexion** (Draft -> Critique -> Refine) que gera planos auto-corrigidos de alta fidelidade. O sistema de execução suporta `critical`, `retry` e `fallback_tool`.
- [x] **Runtime Self-Correction (OODA)**: O `AutonomyService` implementa um loop de **Observe-Orient-Decide-Act**. Se uma ação falhar criticamente, o sistema invoca o `Replanner` (LLM) que decide dinamicamente entre IGNORE, RETRY ou NEW_PLAN.

---

## 🚨 Alta Prioridade & Riscos Críticos

### Segurança & Integridade de Dados

#### Abertas (Segurança)

- [ ] **Prompt Injection Risk**: `PolicyEngine` não sanitiza o *conteúdo* de prompts de planejamento.
- [ ] **Security Headers**: Implementar middleware para HSTS, CSP, X-Content-Type-Options em `main.py`.
- [ ] **Dependency Audit**: Executar auditoria em `package.json` e `requirements.txt` (deps misturadas/antigas).
- [ ] **Data Retention & Purge Policy**: Não há política automatizada de expiração/anonimização para conversas, logs e metadados antigos (LGPD/GDPR exigem retenção mínima e máxima configuráveis).
- [ ] **PII em Logs**: Logs de requests/respostas podem conter PII (e-mail, IDs de usuário, tokens). Falta redaction/masking centralizado em middleware antes de persistir ou exportar.
- [ ] **Audit Log Imutável**: Ações administrativas críticas (mudança de políticas, chaves de API, limites de orçamento) não são registradas em trilha de auditoria imutável/assinada.
- [ ] **Access Control Matrix**: Falta um modelo claro de autorização por recurso/ação (RBAC/ABAC) que cubra API, Parlamento e UI de administração.
- [ ] **Secret Rotation Policy**: Chaves de API, tokens e segredos não têm política formal de rotação/revogação nem tooling para rotação segura sem downtime.

#### Concluídas (Segurança)

- [x] **Ghost Data Risk (Critical)**: `user_models.py` usa `ON DELETE CASCADE` no MySQL, mas Qdrant (Vetores) e Neo4j (Grafo) não sincronizam a deleção. Risco de dados órfãos (Violação LGPD/GDPR).
- [x] **Secret Management**: `config.py` possui senhas padrão. Garantir falha na inicialização em produção se ENV VARs não estiverem definidas.

### Performance

#### Abertas (Performance)

- [ ] **N+1 Queries em Listagens**: Endpoints de listagem (conversas, sprints, tasks) potencialmente executam queries N+1; falta profiling e uso consistente de `selectinload`/paginação agressiva.
- [ ] **LLM Cost & Latency Observability**: Não há dashboards padronizados de custo/latência por modelo e tipo de tarefa; tuning de prompts/modelos é feito "no escuro".
- [ ] **Cold/Warm Start Simples Demais**: Inicialização dos clientes de LLM/brokers não considera pré-aquecimento ou pools; picos de tráfego sofrem com cold-starts desnecessários.

#### Concluídas (Performance)

- [x] **Event Loop Blocking (Critical)**: `ChatService.send_message` chama métodos síncronos do SQLAlchemy sem `await asyncio.to_thread`. Bloqueia o servidor com >1 usuário.
- [x] **Docker Resource Limits**: `docker-compose.yml` sem limites de CPU/Memória (risco de OOM no host).

---

## 🧠 Autonomia & Arquitetura Agêntica (SOTA 2025)

### Backlog (Autonomia)

- [ ] **Agent "Hardcoded Minds"**: Prompts de `multi_agent_system.py` estão hardcoded. Extrair para sistema de templates/DB.
- [ ] **Projeto Aprendiz Neural (Long Prazo)**: Planejamento para treinar um modelo local robusto (Sucessor/Clone) usando **Imitation Learning** a partir de +1000 trajetórias de alta qualidade (`training_data.jsonl`) do modelo atual. Foco em "regras da casa" e especialização proprietária.
- [ ] **Métricas de Sucesso por Objetivo**: Falta atribuir métricas de sucesso/fracasso por tipo de goal (refatoração, bugfix, docs) para avaliar qualidade real dos planos do Meta-Agent.
- [ ] **Policy-Aware Planning**: O planejamento ainda não consome regras de política (budget, escopo, segurança) como primeira classe; risco de planos "bons" tecnicamente, mas inválidos operacionalmente.

### Concluídas (Autonomia)

- [x] **Volatile Memory (Solved)**: Implementação **Local-First** com **SQLite WAL**. Inclui **Integrity Checks**, **Rolling Backups** e **Self-Healing** no boot. Robustez Máxima.
- [x] **Meta-Agent Architecture (SOTA Graph)**: Refatoração completa de `MetaAgent` para usar fluxos baseados em **Grafos de Estado**. Inclui Nodes de Monitoramento, Diagnóstico, Planejamento, **Reflexão (Crítica)** e Execução com **Pydantic Validation**.
- [x] **Robustness Layers**: State Checkpointing, Node Timeouts, Reflexion Loops (Retry) e Pydantic Validation.
- [x] **Industry Benchmark (LangGraph)**: Migração concluída para `langgraph.graph.StateGraph` com checkpoints (SQLite), Type Safety (`TypedDict`) e Reflexion Loops nativos.

---

## 🏗️ Backend & Infraestrutura

### Qualidade de Código & Refatoração

#### Backlog (Qualidade de Código)

- [ ] **ChatService Refactor**: Quebrar monolito (+1600 linhas) em `PromptBuilderService`, `ToolExecutorService`, `RAGService`.
- [ ] **Loose Typing**: Migrar `Dict[str, Any]` em modelos críticos (`Experience`, `TaskState`) para Pydantic Models.
- [ ] **Weak Testing Patterns**: Substituir uso de repositórios reais em testes unitários por Mocks.
- [ ] **Orquestração WebRTC**: Implementar lógica de sinalização no backend para parear com o frontend.
- [ ] **Auto-Analysis com Métricas Reais**: `_analyze_performance` em `auto_analysis.py` ignora `ObservabilityService` e sempre retorna insight “verde”. Conectar a métricas reais de latência, erro e throughput antes de concluir que está tudo saudável.
- [ ] **Auto-Analysis da Qualidade de Respostas**: `_analyze_response_quality` hoje devolve texto estático; deve usar `LLMRepository` (histórico de conversas, retries, falhas do Parlamento) para inferir qualidade percebida.
- [ ] **Modelo de Saúde Geral (Auto-Analysis)**: `_calculate_overall_health` só agrega severities. Definir janela temporal, pesos por tipo de insight e thresholds configuráveis para “healthy/warning/critical”.
- [ ] **Config Sprawl**: Flags e parâmetros de configuração espalhados entre `.env`, `config.py` e constantes hardcoded. Centralizar em um único sistema de config tipado por ambiente (dev/stage/prod).
- [ ] **Feature Flags Ausentes**: Experimentos (novos modelos, caminhos do Parlamento, ferramentas) exigem deploy para ativar/desativar. Implementar feature flags por ambiente/usuário para toggles seguros.
- [ ] **Cross-Cutting Concerns Espalhados**: Logging, tracing, métricas e tratamento de erros estão duplicados em vários módulos; falta camada transversal única (middlewares/hooks) para reduzir inconsistência.
- [ ] **Persistência de Métricas de UX**: endpoint `/observability/metrics/ux` hoje apenas faz log das métricas (`UxMetricItem`). Armazenar em tabela/TSDB para permitir análise de UX, correlação com incidentes e dashboards de produto.

### Infraestrutura

#### Backlog (Infraestrutura)

- [ ] **Migration System**: Migrar de `db_migration_service.py` para **Alembic**.
- [ ] **Distributed Rate Limiting**: Migrar de memória local para Redis.
- [ ] **Tooling Modernization**: Considerar migração de `poetry` para `uv` (Astral).
- [ ] **Detecção de Drift entre Ambientes**: Não há ferramenta/processo automatizado para detectar divergências de config/migrations entre dev/stage/prod (risco de "works on my machine").

---

## 🎨 Frontend (Angular)

### Arquitetura & State

#### Backlog (Backend State)

- [ ] **State Management**: Migrar de "God Service" (`janus-api.service.ts`) para **Angular Signals** ou **SignalStore**.
- [ ] **God Components**: Refatorar `conversations.ts` (+800 linhas) separando Store e Service.
- [ ] **RxJS Anti-patterns**: Eliminar "subscribe inside subscribe" (ex: `conversations.ts`).
- [x] **Dual-PaaS Conflict**: ~~Decidir entre Firebase e Supabase como SSOT.~~ **Decisão: Firebase é o SSOT.** Dependência Supabase removida.
- [x] **Design System Fragmentado**: ~~Falta um Design System/Lib de componentes única.~~ **Criado `_design-system.scss`** em `shared/` com tokens completos (cores, tipografia, espaçamento, sombras, z-index), 8 mixins reutilizáveis e classes base.
- [ ] **Modo Demo/Offline com Mock Data Otimista Demais**: `DemoService` + `arquitetura.ts` carregam dados de demo sempre saudáveis (`status: healthy`, uptimes altos). Em incidentes reais, a UI pode mascarar problemas e dar falsa percepção de saúde.
- [x] **Agent Events sem UI Completa**: ~~agent-events.service.ts consome eventos em tempo real...~~ **Implementado `/agent-events`**: Dashboard em tempo real com timeline, filtros por agente/tipo, busca e visualização de payloads JSON.

### UI/UX & Acessibilidade

#### Backlog (UI/UX)

- [ ] **Feedback de Erros Invisível**: Adicionar `<app-notification-banner>` ao `app.html` para exibir erros globais.
- [ ] **A11y Violations**: Adicionar `<main>` e landmarks ARIA em `app.html` e dashboard.
- [ ] **Empty States**: Adicionar estados vazios em Listagens (Sprints, Tools).
- [ ] **Feedback de Carregamento**: Padronizar Skeleton Loaders.
- [ ] **Internacionalização**: Implementar `@ngx-translate` (hoje hardcoded pt-BR/EN).
- [ ] **Atalhos de Teclado e Power-User Flows**: UI não oferece atalhos nem fluxos otimizados para heavy users (switch rápido de conversas, busca global, etc.).
- [ ] **Fallback de Auto-Analysis Sempre “Happy Path”**: `auto-analysis.component.ts` usa `MockAutoAnalysisService` com dados sempre saudáveis como fallback. Em produção, isso pode esconder problemas reais de saúde se o backend cair.

---

## 📚 Documentação & Processos

### Backlog (Documentação)

- [ ] **Inconsistência de Versões**: Unificar versionamento (Código diz 0.x, Docs diz 1.0).
- [ ] **Documentação Duplicada**: Renderizar Markdown de `docs/` no frontend em vez de hardcode no HTML.
- [ ] **SEO Básico**: Melhorar meta tags em `index.html`.
- [ ] **CI/CD Void**: Implementar pipeline básico em `.github/workflows`.
- [ ] **Manual v2 sem diagrama Mermaid**: O fluxo do Parlamento é descrito em texto ASCII. Adicionar diagrama Mermaid (sequência) para clareza.
- [ ] **Falta runbook de Troubleshooting**: Criar runbook com comandos específicos (investigar poison pills, resetar filas, reconciliar políticas, etc).
- [ ] **ADRs Ausentes**: Decisões arquiteturais importantes não estão registradas em Architecture Decision Records; dificulta entender "por que" certas escolhas foram feitas.

---

## 🔄 Parlamento (Multi-Agent Pipeline) — Auditoria Jan/2026

### Robustez & Proteções

- [ ] **Planner Hardcoded no Router**: `_infer_first_agent()` em `router_worker.py` chama `build_plan_for_goal()` mas ignora o resultado e sempre retorna `"coder"`. O plano gerado é desperdiçado (custo LLM).
- [ ] **Falta de Circuit Breaker no Parlamento**: Os workers (`coder`, `professor`, `sandbox`, `router`) não têm proteção contra loops infinitos de reentrega entre agentes. Um bug pode criar ciclo: `coder → professor → coder → ...` indefinidamente.
- [ ] **TaskState sem validação de transições**: O `TaskState` permite qualquer string em `next_agent_role`. Não há enum ou validação; erros de typo (`"codder"`) causam perda silenciosa da tarefa.
- [ ] **Parlamento sem timeout global**: Não há limite de tempo ou número máximo de iterações para um `TaskState` completar o pipeline. Tarefas podem ficar "presas" indefinidamente.
- [ ] **History bloat no TaskState**: `state.history.append()` cresce indefinidamente. Tarefas com muitas iterações podem estourar memória do broker/worker.
- [ ] **Meta-Agent não integrado ao Parlamento**: O Meta-Agent monitora LLM e infra, mas não observa métricas do Parlamento (latência por agente, taxa de loops, filas acumuladas).
- [ ] **Hardcoded Logic no Coder**: `code_agent_worker.py` usa heurística fixa de complexidade (`lines // 80`) e prompts hardcoded. Extrair para configuração/templates.
- [ ] **Observabilidade Limitada**: `TaskState` não propaga `trace_id` do OpenTelemetry explicitamente, dificultando rastreio distribuído (API -> RabbitMQ -> Worker).
- [ ] **Idempotência dos Workers**: Handlers de `TaskState` não são explicitamente idempotentes; reentregas pelo broker podem causar efeitos colaterais duplicados (commits, notificações, updates de estado).
- [ ] **Prioridade de Tarefas no Parlamento**: Tarefas interativas e jobs longos compartilham filas/prioridades; falta QoS diferenciando requisições de usuário em tempo real de tarefas batch/lentas).
- [ ] **Replay & Re-run de Tarefas**: Falta mecanismo oficial para reprocessar um `TaskState` a partir de um checkpoint conhecido (para debugging ou correção) sem "hackear" a fila.
- [ ] **Human-in-the-Loop Configurável**: Não existe estágio de aprovação humana configurável por tipo de task/criticidade (ex.: mudanças em segurança/infra deveriam exigir confirmação).

---

## 🛡️ Resiliência & Messaging — Auditoria Jan/2026

### Message Broker & DLX

- [ ] **DLX/DLQ não configurado por padrão**: `_get_queue_arguments()` só inclui `x-dead-letter-exchange` se configurado em settings. Sem isso, `nack(requeue=False)` descarta mensagens silenciosamente em vez de encaminhar para dead-letter.
- [ ] **Lack of Backpressure no Broker**: Se consumidores ficam lentos, o broker continua aceitando mensagens sem limite. Falta configurar `x-max-length` + alerta quando atingido.
- [ ] **Auto-Healer não reconcilia todas as filas**: `_reconcile_queue_policies()` só reconcilia filas do `QueueName` enum. Filas dinâmicas ou legadas ficam de fora.
- [ ] **Poison Pill Handler sem alerta**: Mensagens em quarentena não disparam alertas (Slack/Email/PagerDuty). Operador só descobre via Prometheus/logs manuais.
- [ ] **Inconsistent DLX Type**: `MessageBroker` declara DLX como `FANOUT` em `publish` mas `DIRECT` no fallback. Padronizar para `FANOUT` para evitar `PRECONDITION_FAILED`.
- [ ] **RabbitMQ Connection String Unsafe**: A construção da URL AMQP usa f-string simples. Senhas com caracteres especiais (`@`, `/`) quebram a conexão. Necessário `urllib.parse.quote`.
- [ ] **Retry Policy Inconsistente**: Estratégias de retry (backoff, jitter, max attempts) variam entre produtores e consumidores; documentar e padronizar políticas de reentrega por tipo de fila.
- [ ] **Health Checks Superficiais do Broker**: `health-check` atual só valida conexão com RabbitMQ. Não monitora filas críticas (tamanho, consumidores ativos, taxa de dead-letter) para detectar degradação precoce.
- [ ] **Disaster Recovery / Multi-Region**: Não há estratégia documentada para falha total do cluster de RabbitMQ ou da região cloud (backup/restore, RPO/RTO).

### Kernel & Lifecycle

- [ ] **Kernel Workers sem Graceful Shutdown**: `Kernel._start_background_workers()` inicia tasks sem tracking centralizado. No shutdown do daemon, não há cancelamento explícito → possível perda de trabalho em progresso ou vazamento de tasks.
- [ ] **Kernel Singleton global**: `Kernel.get_instance()` retorna singleton global, dificultando testes unitários e cenários multi-tenant futuros.

---

## 🖥️ Frontend — Gaps Operacionais

- [ ] **Sem UI para Parlamento**: O fluxo multi-agente (`TaskState`) não tem visualização no frontend. Operador não consegue ver em qual agente a tarefa está, nem o histórico de passagens.
- [ ] **Sem UI para Poison Pills**: Mensagens em quarentena (poison pills) não são visíveis na UI de administração. Operador precisa consultar Prometheus ou logs diretamente.
- [ ] **Sem UI para Limite de Orçamento**: O usuário não enxerga claramente o consumo de tokens/custo nem quando o `Dynamic Budget Guardrails` está próximo ou ativo. Falta painel com uso por período/modelo.
- [ ] **Modo Read-Only Operacional**: UI não possui modo read-only para janelas de manutenção ou incidentes (apenas visualização de estado, bloqueando ações destrutivas).

---

## 🌐 Pesquisa & Inovação (Requere Internet/SOTA)

Pontos que necessitam de validação externa ou estudo de "State of the Art" (2025/2026).

### Protocolos & Integrações

- [ ] **Model Context Protocol (MCP)**: O Janus tem sistema proprietário de tools. Pesquisar viabilidade de adotar MCP (padronização Anthropic) para consumir servers externos ou expor o Janus como server.
- [ ] **Angular SignalStore (NGRX)**: Pesquisar padrões enterprise de `ngrx/signals` para substituir o gerenciamento manual e verboso em `conversations.ts` e `chat.ts`.

### Modelos & Performance

- [ ] **Benchmark DeepSeek-V3/R1**: Investigar modelos DeepSeek para substituir GPT-4o.
  - **Custo V3**: $0.27/M (in) e $1.10/M (out). ~10x mais barato que GPT-4o.
  - **Custo R1 (Reasoning)**: $0.55/M (in) e $2.19/M (out).
  - **Cache**: Hits custam ~1/4 do preço ($0.07/M). Ideal para contextos longos.
- [ ] **Qdrant Binary Quantization**: Pesquisar impacto de precisão vs economia de RAM ao ativar quantização binária (1-bit/bitpacking) para vetores de documentos antigos/frios.

### Tooling & DevEx

- [ ] **UV Package Manager**: Validar migração de Poetry para `uv` (Astral). Promete installs 10-100x mais rápidos. Verificar suporte a `pyproject.toml` complexos e `lock` cross-platform.

---

## 🤖 Recomendação de Modelos (2025/2026)

Combinar o melhor da API barata com a potência local (16GB VRAM é o "sweet spot" para modelos médios).

### 1. API Cloud (Intel & Raciocínio Pesado)

Para tarefas que exigem contexto massivo ou inteligência "SOTA" que não cabe na GPU.

- [ ] **DeepSeek R1 (API)**:
  - *Função*: **"Thinker Agent"**. O cérebro principal.
  - *Custo*: Irrisório ($0.55/M).
  - *Justificativa*: Imbatível em lógica matemática e planejamento complexo.
- [ ] **Claude 3.7 Sonnet (API)**:
  - *Função*: **"Coder & UI"**. O especialista em sintaxe.
  - *Justificativa*: Melhor que GPT-4o para gerar código front-end limpo (Angular/Tailwind).

### 2. Local "On-Device" (Privacidade & Latência Zero)

Aproveitando sua RTX 4060Ti (16GB VRAM) + 64GB RAM

- [x] **Qwen 2.5 32B Coder (Q4_K_M GGUF)**: O "sweet spot" para sua 4060Ti.
  - **Split Inference**: Configuramos `OLLAMA_GPU_LAYERS=50` no `.env`. Isso coloca ~12GB na VRAM (rápido) e o restante na RAM (DDR5), permitindo rodar modelos maiores que a GPU comportaria sozinha com performance aceitável.llover". Será um "Coder Local" extremamente competente.

- [x] **DeepSeek-R1-Distill-Qwen-14B (Full GPU)**:
  - *Setup*: Cabe *inteiro* nos 16GB de VRAM (sobra espaço).
  - *Performance*: Velocidade extrema (+50 t/s).
  - *Uso*: **Router Agent**, **Reflexion Loop Rápido** e **Summarizer**.
- [x] **Ferramenta de Execução**: Usar **Ollama** ou **LM Studio** com configurações de offloading de camadas ajustadas manualmente para saturar os 16GB de VRAM.

### 3. Fallback / Rascunho

- [ ] **Llama 3.3 70B (Q2_K ou Q3_K - Extreme Quant)**:
  - *Setup*: Requer ~30-40GB de RAM de sistema. Cabe nos seus 64GB.
  - *Uso*: Apenas se precisar de um modelo "grande" localmente e puder esperar (será lento, ~3-5 t/s).

---

## 🏛️ Evolução Arquitetural (Pós-DeepSeek)

Mudanças estruturais viabilizadas pelo custo marginal do DeepSeek-V3/R1.

- [x] **Novo Node: "Thinker" (Reasoning)**: Inserir um node `ThinkerAgent` (R1) *antes* do `CoderAgent`.
  - **Atual**: Router -> Coder (Gera direto) -> Professor -> Sandbox.
  - **Novo**: Router -> Thinker (Planeja/Raciocina) -> Coder (Apenas traduz p/ código) -> Professor.
  - *Benefício*: Separa o "planejamento algorítmico" da "sintaxe", aproveitando o R1 para lógica difícil.
- [x] **Deep Reflexion Unlocked**: Remover limites rígidos de retry no `ProfessorAgent` (hoje evita loops pelo custo).
  - Permitir até 10 iterações (auto-correction loops) quando a complexidade for alta.
  - O custo de 10 loops no V3 ainda é menor que 1 loop no GPT-4o.
- [x] **Stateful Workers (Context Caching)**: Otimizar o `MessageBroker` para enviar apenas *deltas* de `TaskState`, mantendo o contexto estático (regras, codebase) cacheado na sessão do LLM (se API suportar stateful sessions), maximizando o desconto de Cache Hit ($0.07/M).
- [x] **Reasoning Logs (Auditabilidade)**: Capturar e estruturar o bloco de "Chain of Thought" do DeepSeek-R1 no banco de dados (MySQL/Neo4j).
  - Permitir que o usuário veja *como* a IA chegou à conclusão, não apenas a resposta final.
- [x] **Adversarial Red Team (Local)**: Usar o Qwen Local (sem custo) para tentar "quebrar" ou encontrar falhas de segurança no código gerado pelo modelo Cloud antes de aprovar.
  - *Fluxo*: Cloud Gera -> Local Ataca -> Se sobreviver -> Professor Revisa.
- [ ] **Deep Async Lane (Slow Thinking)**: Criar uma fila RabbitMQ dedicada (`queue:deep_thinking`) com timeout de 10+ minutos.
  - Para tarefas como "Refatoração Arquitetural" onde o R1 pode precisar "pensar" por minutos sem travar a API de chat síncrona.
- [x] **Knowledge Distillation Pipeline (Auto-Dataset)**: Salvar automaticamente pares de [Pergunta Complexa] + [Reasoning do R1] em um `dataset.jsonl`.
  - *Objetivo*: Usar esses dados futuramente para fazer Fine-Tuning de um modelo Qwen menor (7B/14B), tornando-o "especialista no seu projeto" sem depender da nuvem.
- [ ] **Proactive Maintenance (Night Watch)**: Agendar um worker recorrente (ex: 3h da manhã) que usa o DeepSeek V3 (barato) para varrer arquivos modificados no dia e sugerir refatorações, docs ou testes faltantes.
- [x] **Dynamic Budget Guardrails**: Se o `spending_usd` mensal atingir 90%, forçar automaticamente o roteamento para `LOCAL_ONLY` em todas as tarefas não-críticas, evitando surpresas no cartão de crédito.
  - [x] **Budget Threshold Config**: `BUDGET_THRESHOLD_PERCENT` in `config.py`.
- [x] **Deep Self-Healing (Compiler Loop)**: Como o *Input Cache* do DeepSeek é barato, podemos permitir que o `CoderAgent` tenha um loop de "tentativa e erro" com o compilador/linter de 20+ iterações (hoje limitamos a 3).
  - *Impacto*: O agente pode corrigir erros obscuros de tipagem ou importação sozinho, sem desistir e pedir ajuda humana.
- [x] **Reasoning RAG (HyDE & Re-Ranking)**: Usar o R1 para "alucinar" uma resposta ideal antes de buscar no Qdrant (HyDE), e depois usar o V3 para re-ranquear os chunks encontrados.
  - *Impacto*: Aumenta drasticamente a precisão da memória de longo prazo, pois a busca é feita por "conceito" e não por palavras-chave soltas.
- [ ] **Autonomous TDD (Test-First Agent)**: Criar um estágio onde o R1 escreve os testes unitários (`test_*.py`) cobrindo edge-cases *antes* de escrever o código.
  - *Justificativa*: Modelos de raciocínio são excelentes QA managers. Eles pensam em cenários de falha que modelos comuns ignoram.
- [ ] **Speculative Decoding (Draft-Verify)**: Usar Qwen local para gerar um "rascunho" rápido, depois V3 apenas valida/corrige.
  - *Impacto*: Reduz tokens de output cloud em 50-70% (paga-se só pela verificação, não geração).
- [ ] **Multi-Model Consensus (Voting)**: Para decisões críticas, rodar a mesma query em 3 modelos (Qwen, V3, R1) e usar votação majoritária.
  - *Justificativa*: Aumenta confiabilidade sem depender de um único modelo. DeepSeek barato viabiliza redundância.
- [ ] **Proactive Bug Hunting (Static Analysis Agent)**: Worker que roda periodicamente analisando código com regras de linting + LLM para detectar bugs sutis.
  - *Fluxo*: Cron -> Analisa arquivos modificados -> LLM identifica potenciais bugs -> Cria issues automaticamente.
- [ ] **Documentation Auto-Generation (DocAgent)**: Após cada PR aprovado, gerar/atualizar docstrings e README automaticamente com V3.
  - *Benefício*: Documentação sempre atualizada sem esforço manual.
- [x] **Semantic Commit Messages (Git Integration)**: LLM analisa diff e sugere mensagens de commit semânticas (feat/fix/refactor).
  - *Impacto*: Changelog automático e histórico git legível.
- [ ] **Context-Aware Code Completion (Local RAG)**: Usar embeddings locais + Qdrant para sugerir código baseado no contexto do projeto.
  - *Diferencial*: Vai além do autocomplete genérico, conhece as convenções do seu projeto.
- [x] **Async LLM Router**: Refatorar `get_llm()` de sync para async nativo, evitando `run_in_executor` workarounds.
  - *Impacto*: Melhor throughput no FastAPI, menos overhead de threads.
- [x] **Git Tools in Container**: Adicionar `git` ao Dockerfile do `janus_api` para permitir operações git dentro do container.
  - *Benefício*: Semantic commits, análise de diff, e outras features git funcionam no container.

---

## 🧪 Testing & Quality Assurance — Gaps Identificados

### Cobertura & Estrutura de Testes

### Backlog

- [ ] **Cobertura de Testes Fragmentada**: A pasta `tests/` tem 16 arquivos raiz + 6 subpastas (`unit`, `integration`, `e2e`, `smoke`, `manual`, `chaos_harness`), mas muitos módulos críticos (`chat_service.py`, `autonomy_service.py`, `multi_agent_system.py`) não têm testes unitários correspondentes.
- [ ] **Testes Dependentes de Infraestrutura**: Muitos testes de integração dependem de Neo4j/Qdrant/RabbitMQ rodando em Docker. Falta abstração via Mocks/Fixtures para permitir execução rápida em CI.
- [ ] **Chaos Testing Incompleto**: `chaos_harness.py` existe mas não está integrado ao CI/CD. Deveria rodar periodicamente para validar resiliência.
- [ ] **Test Coverage Reporting**: Não há configuração de `pytest-cov` nem threshold mínimo de cobertura definido.
- [ ] **Contract Testing Ausente**: APIs entre `janus-api` e `janus-angular` não têm testes de contrato (OpenAPI/Pact).
- [ ] **Property-Based Testing**: Não há uso de `hypothesis` para testar edge-cases em parsers de JSON, sanitizadores, ou handlers de mensagens.
- [ ] **Test Data Management**: Fixtures/dados de teste são duplicados entre módulos. Falta estratégia única (factories/builders) para criar entidades consistentes e fáceis de manter.
- [ ] **Flaky Tests sem Quarentena**: Testes intermitentes quebram o CI de forma aleatória. Implementar marcação de flaky, rerun automático e/quarentena até correção.
- [ ] **Security Regression Suite**: Não existe suíte dedicada de regressão de segurança (authz, rate limiting, injection, fuga de dados) rodando em cada release.
- [ ] **Smoke Tests de Observabilidade Simplistas**: `test_janus_comprehensive.py` e `test_janus_services.py` apenas verificam imports/prints para HealthMonitor, PoisonPillHandler, OptimizationService e ObservabilityService. Substituir por asserts de comportamento, cenários de falha e validação de métricas.

### Verificação Automatizada

- [ ] **Arquivos `verify_*.py` Manuais**: 12 scripts de verificação em `tests/` são executados manualmente. Integrar ao CI como smoke tests pós-deploy.
- [ ] **Linting Incompleto**: `ruff` configurado, mas não há pre-commit hooks para garantir execução antes de cada commit.
- [ ] **Type Checking Ausente no CI**: `mypy` não está configurado. Muitos `Dict[str, Any]` poderiam ser detectados com type checking estrito.

---

## 🌙 Evolution & Dream Mode — Melhorias no Sistema de Auto-Evolução

### SafeEvolutionManager & JanusLab

### Backlog

- [ ] **Lab Cleanup Incompleto**: `JanusLabManager` cria containers Docker para testar evoluções, mas não há garantia de limpeza em caso de crash. Implementar `atexit` handler ou finalizer.
- [ ] **Evolution Session Persistence**: `SafeEvolutionSession` é salva em log, mas não há UI para visualizar histórico de evoluções. Expor via endpoint `/evolution/sessions`.
- [ ] **Dry Run Limitado**: O modo `dry_run=True` não simula todo o fluxo (LLM, Lab, etc.). Deveria retornar estimativa de custo e tempo sem executar.
- [ ] **Evolution Rollback**: Se uma evolução aplicada causa degradação, não há mecanismo automático de rollback. Implementar snapshot antes de aplicar + auto-revert se health score cair.
- [ ] **Guardrails de Segurança nas Evoluções**: SafeEvolutionManager não aplica política mínima de segurança (ex.: bloquear alterações em diretórios sensíveis ou rotas críticas sem aprovação humana explícita).
- [ ] **Dataset Sintético de Teste**: Não há geração de datasets sintéticos/anonimizados para testar evoluções de forma segura sem tocar dados reais de usuários.

### LogAwareReflector

- [ ] **Log Parsing Limitado**: `LogAwareReflector` lê logs estruturados, mas não suporta logs multi-linha (stack traces). Implementar parser de exceções Python.
- [ ] **Log Retention**: Não há configuração de retenção de logs analisados. Logs antigos podem consumir disco indefinidamente.
- [ ] **Reflection Triggers**: Reflexão só ocorre em ciclo programado. Adicionar trigger reativo baseado em taxa de erros (ex: >5 erros/min → reflexão imediata).

### Self-Study Manager

- [ ] **Self-Study Scope Limitado**: `SelfStudyManager` analisa apenas arquivos Python. Expandir para suportar TypeScript (frontend Angular), YAML (configs), e Markdown (docs).
- [ ] **Study Results Não Persistidos**: Resultados de auto-estudo não são salvos estruturadamente. Persistir em Neo4j como nós de conhecimento técnico.

---

## 🧭 LLM Router — Aprimoramentos de Roteamento

### Seleção Adaptativa

- [ ] **Exploration Bias**: `LLM_EXPLORATION_PERCENT` (10%) pode ser alto demais para produção. Implementar decay dinâmico após período de aprendizado inicial.
- [ ] **Multi-Armed Bandit**: O algoritmo de seleção atual é baseado em score ponderado. Considerar implementar UCB1 ou Thompson Sampling para balancear exploration/exploitation.
- [ ] **Model Quality Metrics**: Score de seleção considera apenas custo e latência. Adicionar métricas de qualidade (taxa de retry, feedback humano, precisão de respostas).
- [ ] **Fallback Chain Configurável**: Fallback entre provedores é hardcoded. Extrair para configuração (`LLM_FALLBACK_CHAIN`).

### Rate Limiting & Quotas (P0 - Crítico)

- [ ] **Rate Limit In-Memory (Unsafe for Scale)** - 🔥 CRÍTICO
  - *Problema*: Contadores estão em memória. Múltiplas instâncias do Janus multiplicam o limite efetivo (risco de banimento).
  - *Solução*: Implementar `RedisUsageTracker` com scripts Lua para controle atômico distribuído.
  - *Impacto*: Segurança para escalar (Docker/K8s) sem violar regras dos providers.
- [ ] **Ausência de Wait Time Feedback** - Retries ineficientes
  - *Problema*: `is_available()` retorna apenas True/False. Router não sabe quanto tempo esperar.
  - *Solução*: Retornar struct `{ available: bool, wait_seconds: float }` para backoff inteligente.
  - *Impacto*: Redução de retries cegos e latência percebida.
- [ ] **Quota Consumption Visibility**: Não há endpoint para visualizar consumo de quotas por usuário/projeto em tempo real.
- [ ] **Quota Alerts**: Orçamentos mensais (`OPENAI_MONTHLY_BUDGET_USD`, etc.) não disparam alertas quando atingem thresholds (50%, 80%, 100%).

### Cache & Performance

- [ ] **Response Cache Key Collision**: Cache key inclui `hash(prompt)`, mas prompts similares podem gerar respostas iguais. Investigar semantic caching (embeddings).
- [ ] **Cache Warming**: Não há mecanismo para pré-carregar cache com queries frequentes após restart.
- [ ] **Streaming Support Incompleto**: `get_llm` retorna modelo para invocação síncrona. Adicionar `get_llm_streaming` para suporte nativo a SSE no chat.

### Features Avançadas (P0 - Crítico)

- [ ] **Streaming Ausente** - BLOCKER para UX moderna
  - *Problema*: Apenas completion síncrono. Sem streaming de tokens em tempo real.
  - *Solução*: Implementar `async def astream(prompt)` no `LLMClient` + endpoint SSE `/api/v1/chat/stream`.
  - *Impacto*: UX 10x melhor (perceived latency: 5s → 0.5s), interface mais responsiva.
- [ ] **Batch Processing Ausente** - 50% de economia!
  - *Problema*: Cada request é individual. OpenAI Batch API oferece 50% desconto mas não é usado.
  - *Solução*: `async def abatch(prompts: list[str])` com integração ao Batch API para processamento offline.
  - *Impacto*: 50% desconto em consolidação de conhecimento, analytics em lote.

### Optimization & Analytics (P1 - Alto)

- [ ] **A/B Testing Manual** - Otimização data-driven ausente
  - *Problema*: Experimentos de modelo são manuais. Não há framework de A/B testing automático.
  - *Solução*: Auto A/B testing com traffic split e coleta automática de métricas (latency, cost, quality).
  - *Impacto*: Otimização contínua baseada em dados reais, ROI mensurável.
- [ ] **Token Usage Forecasting** - Prevenção de surpresas de custo
  - *Problema*: Não prevê token usage e custo antes de chamar LLM.
  - *Solução*: `forecast_tokens(prompt, role)` usando tiktoken + EMA histórico de output tokens por role.
  - *Impacto*: Alertas antecipados para prompts muito longos, prevenção de custos inesperados.
- [ ] **Cost Anomaly Detection** - Detecção de spikes
  - *Problema*: Não detecta spikes anômalos de custo (ataques, bugs).
  - *Solução*: Detector baseado em média móvel + desvio padrão (alerta se cost > avg + 3σ).
  - *Impacto*: Detecção precoce de ataques/bugs, proteção financeira.

---

## 🧠 Memory & Knowledge Graph — Aprimoramentos de Memória

### MemoryCore (Qdrant)

- [ ] **PII Redaction Incompleto**: `MEMORY_PII_REDACT` usa regex básico. Implementar NER (Named Entity Recognition) com spaCy para detecção mais precisa.
- [ ] **Memory Compaction**: Não há mecanismo de compactação de memórias antigas. Implementar agregação de experiências similares para reduzir volume.
- [ ] **Memory Export/Import**: Não há funcionalidade para exportar/importar memórias (backup, migração entre ambientes).
- [ ] **Memory Deduplication**: `DedupeService` existe mas não é chamado automaticamente em `amemorize`. Integrar para evitar duplicatas.

### GraphGuardian (Neo4j)

- [ ] **Graph Consistency Check**: Não há verificação periódica de consistência do grafo (nós órfãos, relações quebradas).
- [ ] **Graph Pruning**: Não há mecanismo para remover nós antigos ou pouco acessados. Implementar política de retenção baseada em acesso.
- [ ] **Semantic Relation Matcher Performance**: `semantic_relation_matcher.py` usa fuzzy matching síncrono. Considerar cache de embeddings de tipos de relação.

### Knowledge Consolidator

- [ ] **Consolidation Conflicts**: Se dois workers tentam consolidar o mesmo conhecimento simultaneamente, pode haver conflitos. Implementar locking distribuído.
- [ ] **Consolidation Metrics**: Não há métricas de eficácia da consolidação (conhecimentos aceitos vs rejeitados, confiança média).
- [ ] **Cross-Modal Consolidation**: Consolidação é apenas text-to-text. Expandir para suportar consolidação de conhecimento de imagens/áudio.

### Knowledge Graph (Neo4j) — Gaps para Perfeição

#### P0 - Crítico (Search & Reasoning)

- [ ] **Vector Search Ausente**: Não há integração de embeddings no Neo4j. Busca semântica é apenas text matching simples, impossibilitando encontrar conceitos similares por vetorização.
  - *Solução*: Implementar Vector Index (Neo4j v5.11+) com embeddings automáticos via LLM em `GraphEmbeddingsManager`.
  - *Impacto*: Unlock de semantic search real com similarity scoring.
- [ ] **GraphRAG Básico**: Sem graph traversal inteligente para RAG. Não explora relacionamentos multi-hop nem rankeia contexto por relevância topológica.
  - *Solução*: Criar `GraphRAG` class com multi-hop reasoning, context ranking (PageRank/HITS) e path explanation.
  - *Impacto*: Aumenta drasticamente a qualidade da memória de longo prazo para contextos complexos.
- [ ] **Hybrid Search Incompleto**: Não combina vector search + text search + graph traversal em uma única query inteligente.
  - *Solução*: Implementar `HybridGraphSearch` que combina os 3 modos e re-rankeia resultados.
  - *Impacto*: Precisão máxima em retrieval, aproveitando o melhor de cada paradigma.

#### P1 - Alto (Temporal & Analytics)

- [ ] **Temporal Queries Ausentes**: Sem versionamento de nós/relacionamentos. Impossível fazer time-travel queries ou rastrear evolução do conhecimento.
  - *Solução*: Implementar bitemporal model (transaction time + valid time) com propriedades `valid_from`, `valid_to`, `version`.
  - *Impacto*: Auditoria completa, rollback de conhecimento, análise de evolução temporal.
- [ ] **Graph Analytics Limitados**: Sem algoritmos de graph analytics (PageRank, Community Detection, Centrality).
  - *Solução*: Integrar Neo4j GDS (Graph Data Science) com `GraphAnalytics` class para PageRank, Louvain, Betweenness.
  - *Impacto*: Descoberta de conhecimentos centrais, detecção de comunidades, identificação de padrões.
- [ ] **Anomaly Detection Inexistente**: Não detecta padrões anômalos (nós isolados, hubs excessivos, ciclos suspeitos).
  - *Solução*: Worker periódico de `AnomalyDetector` usando heurísticas + ML para flaggear anomalias.
  - *Impacto*: Qualidade do grafo, detecção de erros de consolidação.

#### P2 - Médio (Schema & UX)

- [ ] **Schema Implícito**: Schema não é declarativo, validação apenas pós-inserção no Graph Guardian.
  - *Solução*: Criar `GraphSchemaManager` com schemas Pydantic para nós e relacionamentos, validação pre-write.
  - *Impacto*: Governança, detecção precoce de erros, documentação auto-gerada.
- [ ] **Graph Visualization Ausente**: Sem UI para explorar grafo visualmente no frontend.
  - *Solução*: Criar endpoint `/api/v1/graph/visualize` + componente Angular com Cytoscape.js para exploração interativa.
  - *Impacto*: UX revolucionária, debugabilidade, descoberta de conhecimento.
- [ ] **GraphQL Integration Faltando**: Apenas REST endpoints disponíveis, dificultando queries complexas do frontend.
  - *Solução*: Adicionar plugin Neo4j GraphQL ou implementar resolver custom.
  - *Impacto*: Developer experience, queries eficientes, schema-first development.
- [ ] **Real-time Graph Updates**: Frontend não recebe atualizações em tempo real quando grafo muda.
  - *Solução*: Implementar WebSocket/SSE stream para mudanças no grafo + CDC (Change Data Capture).
  - *Impacto*: Colaboração em tempo real, dashboards live.

#### P3 - Baixo (Advanced)

- [ ] **Graph Neural Networks (GNN)**: Não há embeddings aprendidos via GNN para nós/relacionamentos.
  - *Solução*: Pesquisar PyTorch Geometric + Neo4j GDS para treinar node embeddings.
  - *Impacto*: Embeddings contextuais superiores, link prediction, node classification.
- [ ] **Graph Compression**: Sem compactação de subgrafos ou agregação de padrões repetitivos.
  - *Solução*: Implementar materializações de subgrafos frequentemente acessados.
  - *Impacto*: Escalabilidade, performance em grafos massivos.

### Vector Store (Qdrant) — Gaps para Perfeição

#### P0 - Crítico (Performance & Scalability)

- [ ] **Quantization Ausente**: Todos os vetores usam float32 completo (1536 dims × 4 bytes = 6KB/vetor). Com 100K+ experiências, consome >600MB RAM.
  - *Solução*: Habilitar Scalar Quantization (INT8) em `vector_store.py` para reduzir de 6KB → 1.5KB por vetor.
  - *Impacto*: 75% menos RAM, busca 2-3x mais rápida, perda de precisão <1%.
- [ ] **HNSW Parameters Não Otimizados**: Usa defaults (`m=16`, `ef_construct=100`). Para datasets >100K, parâmetros subótimos.
  - *Solução*: Aumentar `m=32`, `ef_construct=200` para melhor recall em grafos grandes.
  - *Impacto*: Recall@10 melhora de ~92% → ~97%, latency +10-20ms.
- [ ] **Sem Caching de Embeddings**: Query embedding é gerado **a cada busca**, mesmo para queries repetidas.
  - *Solução*: LRU cache para top 500 query embeddings em `MemoryCore`.
  - *Impacto*: 50-200ms salvos por query repetida, cache hit rate 15-30%.

#### P1 - Alto (Advanced Search)

- [ ] **Hybrid Search Inexistente**: Apenas busca vetorial. Não combina keyword search + semantic search.
  - *Solução*: Implementar `ahybrid_search()` com Reciprocal Rank Fusion (RRF) para merge de resultados.
  - *Impacto*: Recall melhora 10-15% em queries com keywords específicos.
- [ ] **Reranking Ausente**: Usa ranking puro do Qdrant (cosine similarity). Não re-rankeia resultados com cross-encoder.
  - *Solução*: Adicionar reranker (cross-encoder/ms-marco-MiniLM) para top-N candidates.
  - *Impacto*: nDCG@10 melhora ~15-25%, adiciona 100-200ms latência.
- [ ] **Sparse Vectors Não Usados**: Apenas dense vectors (embeddings). Sparse vectors (BM25-style) não aproveitados.
  - *Solução*: Usar multi-vector (dense + sparse) com SPLADE ou BM25 para hybrid nativo.
  - *Impacto*: Melhor em queries com termos raros/específicos.

#### P2 - Médio (Data Management)

- [ ] **Sem Data Lifecycle**: Experiências nunca são arquivadas ou deletadas. Collection cresce indefinidamente.
  - *Solução*: Worker `MemoryLifecycleManager` para mover experiências >90 dias para collection "archived" com quantização agressiva.
  - *Impacto*: Reduz collection principal 50-70%, busca 2-3x mais rápida.
- [ ] **Deduplicação Incompleta**: `DedupeService` existe mas não é chamado automaticamente em `amemorize`.
  - *Solução*: Verificar duplicata (cosine >0.98) antes de insert.
  - *Impacto*: Elimina 5-10% de duplicatas, economiza storage.
- [ ] **Snapshots & Backup Ausente**: Não há backup automático do Qdrant.
  - *Solução*: Usar Qdrant Snapshots API com upload para S3/GCS, cron diário.
  - *Impacto*: Disaster recovery, point-in-time restore.

#### P3 - Baixo (Integration & Features)

- [ ] **Multi-Tenancy Ausente**: Uma única collection para todos os usuários. Sem isolamento de dados.
  - *Solução*: Payload filtering com `user_id` em todas as queries (preferível) ou collection per user.
  - *Impacto*: Isolamento de dados, pronto para multi-tenancy B2B.
- [ ] **Semantic Caching Faltando**: Cache é por query string exato. Queries semanticamente iguais não compartilham cache.
  - *Solução*: Cache por embedding similarity (cosine >0.95) ao invés de hash(query).
  - *Impacto*: Cache hit rate de 15% → 40-50%.

### Message Broker (RabbitMQ) — Gaps para Perfeição

#### P0 - Crítico (Observabilidade)

- [ ] **Distributed Tracing Incompleto**: Trace propagation via OpenTelemetry existe, mas não injeta `trace_id` nos headers das mensagens para propagação cross-worker.
  - *Solução*: Adicionar `x-trace-id` nos headers de mensagens em `message_broker.py` e extrair no consumer para propagação de contexto.
  - *Impacto*: Rastreamento end-to-end completo (API → Queue → Worker), debug facilitado, APM completo.
- [ ] **Queue Metrics Limitados**: Apenas 3 metrics básicos (`published`, `connection_errors`, `consume_errors`). Faltam métricas de profundidade de fila, lag, throughput.
  - *Solução*: `QueueMetricsCollector` periódico via Management API para coletar depth, lag, consumer count.
  - *Impacto*: Dashboards Grafana ricos, alertas de backpressure, capacity planning.

#### P1 - Alto (Resiliência Avançada)

- [ ] **Sem Backup/Restore de Mensagens**: Se RabbitMQ crashar, mensagens em memória são perdidas. Não há backup/restore de filas.
  - *Solução*: `RabbitMQBackupManager` para backup de filas em JSON comprimido e restore a partir de arquivo.
  - *Impacto*: Disaster recovery, migração entre ambientes, replay de mensagens para debugging.
- [ ] **Retry Policy Não Configurável**: `nack(requeue=False)` envia direto para DLX. Não há delayed retry (ex: tentar novamente após 5min).
  - *Solução*: Criar retry queues com TTL que roteiam de volta para fila original após delay.
  - *Impacto*: Retry automático com backoff, diferencia erros transientes de fatais, reduz poison pills.

#### P2 - Médio (Gestão de Filas)

- [ ] **Sem Stream Processing**: Apenas point-to-point queues. Não usa RabbitMQ Streams para event sourcing ou high-throughput.
  - *Solução*: Usar `x-queue-type: stream` para event sourcing com retention (ex: agent_events para frontend).
  - *Impacto*: Event sourcing nativo com replay, throughput 10x maior, múltiplos consumers lendo mesma mensagem.
- [ ] **Prioridade Não Usada**: Suporte a `x-max-priority` existe, mas nenhum publisher usa `priority` parameter.
  - *Solução*: Adicionar `TaskPriority` enum e usar `priority=9` para tasks de usuário, `priority=1` para background jobs.
  - *Impacto*: Tasks de usuário processadas primeiro, background jobs não bloqueiam interatividade.

#### P3 - Baixo (Performance)

- [ ] **Prefetch Fixo**: `prefetch_count=10` hardcoded. Ideal varia por worker (CPU-bound vs I/O-bound).
  - *Solução*: Config dinâmico `QUEUE_PREFETCH_CONFIG` por queue (ex: coder=3, consolidation=20, training=1).
  - *Impacto*: CPU-bound workers não sobrecarregam, I/O-bound maximizam throughput.
- [ ] **Sem Batching**: Mensagens processadas uma a uma. Não há batch processing para operações bulk.
  - *Solução*: `BatchConsumer` que acumula N mensagens antes de processar em lote.
  - *Impacto*: Throughput 5-10x maior para bulk ops, reduz custos de API LLM.
- [ ] **Msgpack Não Otimizado**: Usa `msgpack.packb()` default. Não ativa compressão.
  - *Solução*: Adicionar compressão zlib para payloads >1KB com flag no primeiro byte.
  - *Impacto*: 60-80% redução para payloads grandes (LLM outputs), menos tráfego de rede.

### Database (MySQL → PostgreSQL) — Migração Recomendada

#### 🚨 Limitações Críticas do MySQL

- [ ] **Sem JSON Indexável**: MySQL armazena JSON como TEXT. Impossível fazer analytics em `optimization_history.old_value/new_value`.
  - *Problema*: Queries em JSON são full table scans, extremamente lentas.
  - *PostgreSQL*: JSONB com índice GIN, queries 100x mais rápidas.
- [ ] **Full-Text Search Fraco**: MySQL FTS é básico, sem ranking, sem stemming PT-BR.
  - *Problema*: Busca de prompts por texto é `LIKE '%...%'` sem relevância.
  - *PostgreSQL*: `to_tsvector('portuguese')` com ranking nativo.
- [ ] **Sem Arrays Nativos**: MySQL não tem tipo ARRAY. Listas requerem tabelas separadas com FK.
  - *PostgreSQL*: `ARRAY(String)` nativo com operadores `@>`, `&&`.
- [ ] **Transactional DDL Ausente**: MySQL não suporta DDL em transações. Migrations arriscadas (se falhar, DB fica inconsistente).
  - *PostgreSQL*: DDL dentro de `BEGIN/COMMIT`, rollback automático em erros.
- [ ] **Sem Extensões**: MySQL não tem sistema de extensões.
  - *PostgreSQL*: `pgvector` (embeddings!), `pg_trgm` (fuzzy search), `uuid-ossp`, etc.

#### ✨ Benefícios PostgreSQL (Game Changers)

- [ ] **pgvector Extension** - DIFERENCIAL MATADOR
  - *Feature*: Armazena embeddings de prompts direto no DB com busca por cosine similarity.
  - *Impacto*: Elimina necessidade de Qdrant para prompt embeddings, busca de prompts similares nativa.
  - *Código*: `ALTER TABLE prompts ADD COLUMN embedding vector(1536);`
- [ ] **JSONB Indexável** - Analytics desbloqueados
  - *Feature*: Queries complexas em `optimization_history` com índice GIN.
  - *Impacto*: Analytics de "qual temperatura performa melhor?" 100x mais rápido.
- [ ] **Partial Indexes** - Economia de espaço
  - *Feature*: Índice apenas em `WHERE is_active=true`.
  - *Impacto*: Índices 90% menores (apenas rows ativas).
- [ ] **Concurrent Indexes** - Zero downtime
  - *Feature*: `CREATE INDEX CONCURRENTLY` sem lock da tabela.
  - *Impacto*: Criar índices em produção sem parar o sistema.

#### 🎯 Recomendação Final

**Status**: ✅ **MIGRAR AGORA**

**Razões**:

1. **pgvector** - Prompt similarity search é único ao PostgreSQL
2. **JSONB** - Unlock analytics que são impossíveis no MySQL
3. **Transactional DDL** - Migrations 10x mais seguras
4. **Volume pequeno** - Migração ~1h (antes de acumular milhões de rows)

**Effort**: ~5 dias  
**ROI**: 🚀🚀🚀 ALTÍSSIMO

**Roadmap**: Export MySQL → Import PostgreSQL → Adicionar pgvector → Gerar embeddings para prompts

---

## ⚙️ Configuration & DevOps — Operações e Configuração

### Configuration Management

- [ ] **Config Drift Detection**: Configurações em `config.py` vs `.env` vs Docker podem divergir. Implementar validação de consistência no startup.
- [ ] **Hot Reload de Configuração**: Mudanças em configuração exigem restart. Implementar endpoint `/admin/config/reload` para configs não-sensíveis.
- [ ] **Environment-Based Defaults**: Todos os defaults são os mesmos para dev/staging/prod. Implementar profiles de configuração.
- [ ] **Secret Rotation**: Secrets (API keys, passwords) não têm mecanismo de rotação. Integrar com Vault/AWS Secrets Manager.

### Observabilidade Avançada

- [ ] **Distributed Tracing Incompleto**: `OTEL_ENABLED` existe mas trace propagation entre serviços (API → RabbitMQ → Workers) não está implementado.
- [ ] **Custom Metrics Dashboard**: Prometheus exporta muitas métricas, mas não há dashboard Grafana pré-configurado.
- [ ] **Log Correlation**: Logs não incluem `trace_id` consistentemente, dificultando correlação de requisições end-to-end.
- [ ] **Error Aggregation**: Não há integração com Sentry/Rollbar para agregação e alerta de erros.

### CI/CD e Deployment

- [ ] **Blue-Green Deployment**: Não há suporte para deploys sem downtime. Implementar em `docker-compose` ou migrar para K8s.
- [ ] **Database Migrations**: `db_migration_service.py` é custom. Migrar para Alembic (já listado) com suporte a rollback.
- [ ] **Container Health Checks**: `docker-compose.yml` não define healthchecks adequados para todos os serviços.
- [ ] **Multi-Instance Locking**: Operações singleton (scheduler, auto-healer) assumem instância única. Implementar leader election para multi-instância.

---

## 🎤 Multi-Modal & Senses — Expansão Multi-Modal

### Voz (Audio)

- [ ] **Wake Word Detection Limitado**: Estrutura em `senses/audio/` existe, mas wake word detection não está integrado ao pipeline principal.
- [ ] **Voice Circuit Breaker**: Testes em `test_voice_circuit_breaker.py` existem, mas implementação parece incompleta ou mock.
- [ ] **Real-Time Transcription**: Não há suporte para transcrição em tempo real (streaming STT). Implementar com Whisper local ou API.
- [ ] **Voice Response Synthesis**: Não há TTS integrado. Adicionar suporte a ElevenLabs/Azure TTS para respostas por voz.

### Visão (Vision)

- [ ] **Vision Pipeline Básico**: Estrutura em `senses/vision/` existe mas parece incompleta. Documentar casos de uso pretendidos.
- [ ] **Screenshot Analysis**: Não há ferramenta para analisar screenshots do desktop (útil para automação de OS).
- [ ] **OCR Integration**: Não há integração com OCR (Tesseract/Cloud Vision) para extração de texto de imagens.

### Integração Multi-Modal

- [ ] **Multi-Modal Memory**: Memória episódica é apenas texto. Expandir para armazenar embeddings de imagens/áudio.
- [ ] **Cross-Modal Search**: Busca semântica não suporta queries de imagem para texto ou vice-versa.
- [ ] **Multi-Modal LLM Support**: Preparar router para suportar modelos multi-modais (GPT-4V, Gemini Vision, etc.).

---

## 🔐 Segurança Avançada — Melhorias de Segurança

### Autenticação & Autorização

- [ ] **JWT Refresh Token**: Apenas access token implementado. Adicionar refresh token para sessões longas.
- [ ] **Role-Based Access Control (RBAC)**: Permissões são binárias (admin/user). Implementar RBAC granular.
- [ ] **API Key Management**: Não há sistema de API keys para integrações externas.
- [ ] **Audit Trail Completo**: `AUDIT_RETENTION_DAYS` configurado, mas audit trail não captura todas as operações sensíveis.

### Hardening

- [ ] **Input Validation Layer**: Validação de input é feita em cada endpoint. Centralizar em middleware com schemas Pydantic.
- [ ] **Output Sanitization Consistente**: `sanitizer.py` existe, mas não é aplicado consistentemente em todas as respostas.
- [ ] **Dependency Scanning**: Não há scan automático de vulnerabilidades em dependências (Snyk, Dependabot).
- [ ] **Container Scanning**: Imagens Docker não são escaneadas para vulnerabilidades antes do deploy.

---

## 📊 Analytics & Business Intelligence — Insights do Sistema

### Usage Analytics

- [ ] **User Behavior Tracking**: Não há coleta de métricas de uso (features mais usadas, tempo de sessão, etc.).
- [ ] **Cost Attribution**: Custos de LLM são agregados globalmente. Implementar atribuição por usuário/projeto/feature.
- [ ] **Performance Insights**: Não há dashboard de performance histórica (tendências de latência, throughput).

### Model Performance

- [ ] **Response Quality Scoring**: Não há mecanismo para avaliar qualidade das respostas LLM (além de feedback explícito).
- [ ] **A/B Testing Framework**: `LLM_AB_EXPERIMENT_ID` existe mas framework de A/B testing não está completo.
- [ ] **Model Comparison Reports**: Não há relatórios automáticos comparando performance entre modelos/provedores.

---

## 💾 Data Management — Gerenciamento de Dados

### Backup & Recovery

- [ ] **Automated Backups**: SQLite tem WAL, mas não há backup automático para Neo4j/Qdrant/MySQL.
- [ ] **Point-in-Time Recovery**: Não há suporte para recuperação point-in-time.
- [ ] **Cross-Region Replication**: Para disaster recovery, não há replicação para região secundária.

### Data Lifecycle

- [ ] **Data Retention Policies**: `data_retention_service.py` existe mas políticas não são configuráveis por tipo de dado.
- [ ] **GDPR/LGPD Compliance**: Deleção de dados (`ON DELETE CASCADE`) cobre MySQL, mas Qdrant/Neo4j precisam de sincronização (já documentado).
- [ ] **Data Anonymization**: Não há pipeline para anonimização de dados para ambientes de teste/desenvolvimento.

---

## 🚀 Performance Optimization — Otimizações de Performance

### Database

- [ ] **Query Optimization**: Não há análise periódica de queries lentas no Neo4j/MySQL.
- [ ] **Index Management**: Índices em Neo4j/MySQL são criados manualmente. Implementar auto-index baseado em query patterns.
- [ ] **Connection Pooling**: Pooling de conexões não é configurável para todos os databases.

### Caching

- [ ] **Redis Integration**: Rate limiting e caching são in-memory. Migrar para Redis para persistência e multi-instância.
- [ ] **Cache Invalidation Strategy**: Estratégia de invalidação é TTL-based. Implementar invalidação baseada em eventos.

### Async/Concurrency

- [ ] **Thread Pool Tuning**: `LLM_EXECUTOR_MAX_WORKERS=32` é fixo. Implementar auto-tuning baseado em carga.
- [ ] **Event Loop Profiling**: Não há profiling do event loop asyncio para detectar operações bloqueantes.
- [ ] **Concurrent Request Limiting**: Não há limite global de requisições concorrentes por serviço.
