# Janus: AI Architect & Software Engineer Agent

O **Janus** é um sistema de Agente Autônomo para desenvolvimento de software, utilizando uma arquitetura Meta-Agent baseada em LangGraph e um loop de autonomia OODA (Observe, Orient, Decide, Act). O sistema combina memória híbrida (Vetorial + Grafo de Conhecimento) e execução segura em sandbox para realizar tarefas complexas de engenharia.

## 🏗️ Arquitetura

O sistema é composto por dois componentes principais:

*   **Frontend (`front/`)**: Interface web em Angular 20, focada em observabilidade e interação com o agente.
*   **Backend (`janus/`)**: Motor de inteligência em Python (FastAPI + LangGraph), responsável pela orquestração de agentes, memória (Neo4j/Qdrant) e execução de ferramentas.

Para detalhes específicos de cada componente, consulte:
*   [Frontend README](front/README.md)
*   [Backend README](janus/README.md)

## 🚀 Como Começar

### Pré-requisitos
*   Docker & Docker Compose (para infraestrutura: Neo4j, Qdrant, Redis, RabbitMQ)
*   Python 3.11+
*   Node.js 20+

### Execução Rápida

1.  **Infraestrutura**:
    ```bash
    docker-compose up -d
    ```

2.  **Backend**:
    ```bash
    cd janus
    pip install -r requirements.txt
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

3.  **Frontend**:
    ```bash
    cd front
    npm install
    npm start
    ```

Acesse a interface em `http://localhost:4200`.

---

## 📚 Documentação e Inventário

*   **[Inventário de API e Componentes](docs/INVENTORY.md)**: Detalhamento completo de rotas, endpoints e dívidas técnicas.
*   **Guias Específicos**:
    *   [RAG com HyDE](janus/docs/RAG_HYDE.md)
    *   [Resiliência Qdrant](janus/docs/qdrant_resilience_improvements.md)

---

## 🗺️ Roadmap & Technical Debt (V1 Launch)

> *Última atualização: 14/01/2026 (Scientific & V1 Focus)*

Este roadmap define o caminho crítico para o lançamento da **Janus V1**, priorizando robustez, embasamento científico e prontidão para produção.

### 🧱 Backlog por Dificuldade

#### 🟢 Throughput (Baixo Risco)
- Ajustar CSP para produção (`unsafe-inline`/`unsafe-eval`).
- Padronizar toasts de sucesso/erro/warn.
- Varredura de hardcoded settings para `environment.ts`.
- Higienizar `eslint-report.json` e travar regressões no CI.

#### 🟡 Médias (Contexto Necessário)
- Completar UI Coverage (telas faltantes, empty states).
- Resolver Autonomy 500 Error.
- Implementar Input Sanitization por endpoint.
- Evoluir Smart Model Routing com classificação de complexidade.

#### 🔴 Difíceis (Estrutural)
- Corrigir Broken Thought Stream (RabbitMQ → SSE → UI).
- Eliminar State Desync (Backend/Frontend).
- Substituir Ad-hoc State Management por store robusta.
- Unificar Design System (Remover Material, adotar Shadcn/Tailwind).
- Implementar Audit Log Imutável e Database Migration Pipeline (Alembic).

### 🔬 Scientific Foundation (State-of-the-Art)

O Janus baseia-se em papers seminais para sua inteligência:

*   **Raciocínio**: LATS (Language Agent Tree Search), Reflexion, Graph of Thoughts (GoT).
*   **Memória**: Generative Agents (Recência/Importância), MemGPT (Paginação), Voyager (Skill Library).
*   **RAG**: Self-RAG, HyDE (Hypothetical Document Embeddings), RAPTOR (Indexação recursiva).
*   **Multi-Agent**: MetaGPT (SOPs), CAMEL (Role-Playing).

### 🧪 Scientific Frontier (Post-V1)

*   **Self-Evolving Toolset**: Agente cria suas próprias ferramentas (`ToolSynthesizerAgent`).
*   **Swarm Intelligence**: Dynamic Handoffs entre agentes sem supervisor central.
*   **Active Memory Management**: LLM gerencia sua própria janela de contexto.
*   **Code Generation**: Flow Engineering (AlphaCodium) e Hippocampal Memory Replay.

### 🏛️ Infrastructure Strategy (Phase 3)

*   **Model Routing**: DeepSeek V3 (Coding), Qwen 2.5 72B (Architect), Llama-3-Local (Speedster).
*   **Budget Strategy**: Uso de Dual-Wallet e Free Tiers reais (Google Gemini, Groq).
*   **Privacy**: "Nightmare" Risk (OpenAI Data Sharing) desativado por padrão.
*   **Protocol**: Strict Structured Outputs obrigatórios.

### 🚨 V1 Critical Path (Launch Blockers)

#### Security & Enterprise Ready
*   [x] Security Headers Middleware.
*   [ ] Input Sanitization & Rate Limiting (Cost-Based).
*   [ ] Audit Log Imutável.

#### Frontend V1 (Refactor)
*   [ ] UI Overhaul (Professional SaaS aesthetics).
*   [ ] UX Improvements (Real-time feedback, onboarding).
*   [ ] **Bugs Críticos**: Broken Thought Stream, Autonomy 500 Error, State Desync.

#### Stability & Ops
*   [ ] Database Migration Pipeline (Alembic).
*   [ ] Smart Model Routing & Graceful Degradation.

### ✅ Histórico de Conclusões

*   [x] Hybrid Agent Architecture (LangGraph + PydanticAI).
*   [x] Native GraphRAG (neo4j-graphrag).
*   [x] Centralized HITL (Human-in-the-loop).
*   [x] Observability (LangSmith).
*   [x] Secure Sandbox (Docker).
*   [x] Redis State Backend & PostgreSQL Vector.

---

## 🧱 Levantamentos (Status)

*   [x] **Lote 1 — Boot & Kernel**: Mapeado (ver [Inventário](docs/INVENTORY.md)).
*   [x] **Lote 2 — API & Endpoints**: Mapeado (ver [Inventário](docs/INVENTORY.md)).
*   [ ] **Lote 3 — Serviços**: Em andamento.
*   [ ] **Lote 4 — Repositórios**: Em andamento.
*   [ ] **Lote 5 — Agentes & Sandbox**: Em andamento.
