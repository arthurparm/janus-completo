# Janus AI Architect

Janus is an advanced AI Architect system built with a hybrid architecture combining **LangGraph**, **Neo4j**, **Qdrant**, and other modern technologies to provide intelligent reasoning, planning, and execution capabilities.

## 🚀 Overview

Janus utilizes a **"Bicameral" architecture**:
- **Fast Thinking (System 1)**: Vector memory (Qdrant) for quick retrieval and association.
- **Slow Thinking (System 2)**: Knowledge Graph (Neo4j) for deep reasoning and structural understanding.

It features a **Multi-Agent System (MAS)** orchestrated by LangGraph, enabling complex workflows like "Plan-Execute-Reflect".

## 🏗️ Architecture

- **Backend**: Python (FastAPI), LangGraph, SQLAlchemy, PydanticAI.
- **Frontend**: Angular 20, TailwindCSS.
- **Infrastructure**: Docker, RabbitMQ, Redis, Neo4j, Qdrant.
- **AI Core**:
    - **Reasoning**: Graph of Thoughts (GoT), Tree of Thoughts (ToT).
    - **Memory**: Hybrid (Vector + Graph).
    - **Retrieval**: Native GraphRAG with HyDE.

## 🛠️ Prerequisites

- **Python**: >= 3.11 and < 3.13
- **Node.js**: 20 (for frontend)
- **Docker**: For running infrastructure services.

## 🚦 Getting Started

### Infrastructure
Start the required services using Docker Compose:
```bash
docker-compose up -d
```

### Backend (Janus)
See [janus/README.md](janus/README.md) for detailed setup instructions.
```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation: `http://localhost:8000/docs`

### Frontend
See [front/README.md](front/README.md) for detailed setup instructions.
```bash
cd front
npm install
npm start
```
Frontend URL: `http://localhost:4200`

## 🗺️ Roadmap & Status (V1 Launch)

> *Last Update: Jan 14, 2026 (Scientific & V1 Focus)*

This roadmap defines the critical path for the **Janus V1** launch, prioritizing robustness, scientific grounding, and production readiness.

### 🧱 Backlog by Difficulty

#### 🟢 Throughput (Low Risk)
- Adjust CSP for production (reduce `unsafe-inline`/`unsafe-eval`) in *Security Headers Middleware*.
- Standardize success/error/warn toasts in critical flows (*UX Improvements*).
- Scan and centralize hardcoded settings/URLs in `environment.ts` (*Hardcoded Settings*).
- Sanitize `eslint-report.json` and lock regressions in CI (*Linter Bankruptcy*).

#### 🟡 Medium
- Complete *UI Coverage* (missing screens, empty/error/loading states).
- Resolve *Autonomy 500 Error* (reproduce, fix, test).
- Implement *Input Sanitization* (policy per endpoint + extra validation for free payloads).
- Evolve *Smart Model Routing* with complexity classification (heuristic/embedding).

#### 🔴 Hard (High Risk)
- Fix *Broken Thought Stream* (RabbitMQ → SSE → UI) with E2E test.
- Eliminate *State Desync* (define single source of truth and migrate).
- Replace *Ad-hoc State Management* with a robust store (SignalStore/Elf/NgRx).
- Unify Design System (*Design System Conflict*: remove Material gradually).
- Implement *Immutable Audit Log* (append-only + tamper-evident + access).
- Finalize *Database Migration Pipeline* (Alembic + CI/deploy).
- Implement *Graceful Degradation* (degradation matrix + health/alerts).

### 🔬 Scientific Foundation (State-of-the-Art)

Based on 13+ seminal papers grounding Janus's intelligence.

#### 🧠 Reasoning & Planning
- [ ] **LATS (Language Agent Tree Search)**: `Planner` node simulating scenarios via MCTS.
- [x] **Reflexion**: Self-correction loop in `CoderAgent`.
- [x] **Graph of Thoughts (GoT)**: Non-linear orchestration in LangGraph.
- [ ] **Tree of Thoughts (ToT)**: Deliberate exploration of reasoning branches.
- [ ] **Chain of Thought (CoT)**: Mandatory pattern in all system prompts.

#### 💾 Memory & Learning
- [ ] **Generative Agents**: Memory with Recency, Importance, Relevance + Consolidation.
- [ ] **MemGPT**: Infinite context management via pagination.
- [ ] **Voyager**: Skill Library persistence.

#### 🔍 Retrieval & RAG
- [ ] **Self-RAG**: Model critiques its own retrieval.
- [x] **HyDE**: Hypothetical Document Embeddings for better search.
- [ ] **RAPTOR**: Recursive tree indexing.

### 🚨 V1 Critical Path (Launch Blockers)

#### 🛡️ Security & Enterprise Ready
- [x] **Security Headers Middleware**: Applied CSP, HSTS, XFO, etc.
- [ ] **Input Sanitization**: Validate all API inputs.
- [ ] **Rate Limiting (Cost-Based)**: Limit by USD spend, not just requests.
- [ ] **Immutable Audit Log**: Tamper-evident logs for critical actions.

#### 🖥️ Frontend V1
- [ ] **UI Overhaul**: Migrate to professional SaaS aesthetic (Shadcn/UI + Tailwind).
- [ ] **Complete UI Coverage**: Implement missing screens.
- [ ] **UX Improvements**: Real-time feedback, Onboarding.

#### 🐛 Critical Bugs
- [ ] **Broken Thought Stream**: Fix SSE event consumption from RabbitMQ.
- [ ] **Autonomy 500 Error**: Fix internal server error in Strategic Goals.
- [ ] **State Desync**: Fix reactivity between Backend and Frontend.

#### 🏚️ Technical Debt
- [ ] **Linter Bankruptcy**: Fix massive eslint report.
- [ ] **Hardcoded Settings**: Move to environment variables.
- [ ] **Test Coverage Zero**: Add unit and E2E tests for frontend.
- [x] **Legacy Testing Stack**: Migrated to Vitest/Jest.
- [ ] **Ad-hoc State Management**: Migrate to SignalStore/Elf/NgRx.

## ✅ Completed History (Archived)

- [x] **Hybrid Agent Architecture** (LangGraph + PydanticAI).
- [x] **Native GraphRAG** (neo4j-graphrag).
- [x] **Centralized HITL** (Human-in-the-loop).
- [x] **Graph Versioning**.
- [x] **Observability** (LangSmith).
- [x] **Async Database Pool**.
- [x] **Secure Sandbox** (Docker).
- [x] **Migration MySQL → PostgreSQL**.
- [x] **Redis State Backend**.

## 📋 Detailed Tasks

### API & Endpoints
- [ ] Remove duplicate routes (/optimization/* and /productivity/*).
- [ ] Standardize route naming (e.g., /rag/user-chat → /rag/user_chat).
- [ ] Define size limits for free inputs (prompt/message/code/query).
- [ ] Hard gate critical endpoints with JWT/role (admin).
- [ ] Enforce budget limits (USD) at the HTTP gateway level.

### Services (LLM, Chat, RAG, Observability, Autonomy)
- [ ] Enforce size limits in LLMService (prompt + output) and ChatService.
- [ ] Standardize cost estimation logging in Chat → LLM path.
- [ ] Enforce `user_id`/`project_id` server-side before RAG/LLM calls.
- [ ] Implement backoff and cancellation in AutonomyLoop.

### Repositories & Persistence
- [ ] Standardize Postgres sessions (100% async).
- [ ] Fix `db.get_session_direct` calls.
- [ ] Persist repositories for collaboration/tool/optimization/context/sandbox.
- [ ] Define consistency strategy between SQL, Qdrant, and Neo4j.

### Agents, Tools & Sandbox
- [ ] Apply PolicyEngine and rate limiting to all tool-calls.
- [ ] Add timeouts and concurrency limits per tool in ToolExecutorService.
- [ ] Fix missing awaits in `core/autonomy/planner.py`.
- [ ] Unify sandbox and integrate Docker executor into service flow.

### Infrastructure & Resilience
- [ ] Separate plans: move workers to their own processes/containers.
- [ ] Robust messaging: ensure DLX/DLQ and publish fail-fast for RabbitMQ.
- [ ] Lightweight startup: make heavy auto-index/warm-up opt-in via job.
- [ ] Production security profile: strict CORS, mandatory API-Key/Bearer.
- [ ] Worker supervision: monitor/restart/backoff for `asyncio.create_task`.

## 📚 Documentation
- [RAG with HyDE](janus/docs/RAG_HYDE.md)
- [Qdrant Resilience](janus/docs/qdrant_resilience_improvements.md)
