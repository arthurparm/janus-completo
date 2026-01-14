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

---

## 🚨 V1 Critical Path (Launch Blockers)

*Itens obrigatórios para o lançamento da versão 1.0.*

### 🛡️ Security & Enterprise Ready

- [ ] **Security Headers Middleware**: Implementar CSP, HSTS, X-Frame-Options e X-Content-Type-Options.
* [ ] **Input Sanitization**: Validar e sanitizar todos os inputs da API (prevenção de injeção).
* [ ] **Rate Limiting (Cost-Based)**: Limitar usuários por **gasto em dólares**, não apenas requisições.
* [ ] **Audit Log Imutável**: Garantir que logs de ações críticas não possam ser alterados.

### 🖥️ Frontend V1 (Finish the Job)

- [ ] **Complete UI Coverage**: Criar telas para os 82% de endpoints restantes (Tools, Workers, RAG).
* [ ] **Real-time Feedback**: Toasts de erro/sucesso universais.
* [ ] **Onboarding Flow**: Wizard inicial para configuração de chaves e preferências.

### ⚙️ Stability & Ops

- [ ] **Database Migration Pipeline**: Finalizar transição para Alembic (abandonar scripts manuais).
* [ ] **Smart Model Routing**: Router que escolhe entre Local/API baseado na complexidade da task (Economia).
* [ ] **Graceful Degradation**: Fallbacks claros quando serviços (ex: Redis, Neo4j) caem.

---

## ✅ Histórico de Conclusões (Arquivado)

### Foundation & Architecture

- [x] **Hybrid Agent Architecture** (LangGraph + PydanticAI).
* [x] **Native GraphRAG** (neo4j-graphrag).
* [x] **Centralized HITL** (Human-in-the-loop via Postgres Checkpoints).
* [x] **Graph Versioning** (Schema Migration & Purge).
* [x] **Observability** (LangSmith Tracing & Setup).
* [x] **Async Database Pool** (asyncpg + SQLAlchemy).
* [x] **Secure Sandbox** (Docker-based execution).
* [x] **Migração MySQL → PostgreSQL** (pgvector).
* [x] **Redis State Backend**.
