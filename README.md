# Janus AI Architect

Janus AI Architect is a Meta-Agent Framework designed to orchestrate complex reasoning and autonomous tasks. It leverages a bicameral memory system (Qdrant for episodic memory, Neo4j for semantic memory) and uses a Graph of Thoughts (GoT) architecture for advanced planning and execution.

## Repository Structure

- `front/`: Angular 20 frontend application.
- `janus/`: Python/FastAPI backend application.

## Getting Started

### Prerequisites

- Python >= 3.11 and < 3.13
- Node.js 20
- Docker (for infrastructure components: Neo4j, Qdrant, RabbitMQ, Redis)

### Quick Start

1.  **Backend Setup**:
    Follow the instructions in [`janus/README.md`](janus/README.md) to set up and run the backend server.

2.  **Frontend Setup**:
    Follow the instructions in [`front/README.md`](front/README.md) to set up and run the frontend application.

## Contributing

Contributions are welcome! Please refer to the specific component directories for contribution guidelines:
- Frontend: [`front/CONTRIBUTING.md`](front/CONTRIBUTING.md)
- Backend: Follow standard Python practices and ensure tests pass.

---

## 🗺️ Roadmap & Technical Debt (V1 Launch)
>
> *Last update: 2026-01-14 (Scientific & V1 Focus)*

This document defines the critical path for the launch of **Janus V1**, prioritizing robustness, scientific foundation, and production readiness.

### 📌 Index

- Backlog by Difficulty (Throughput / Medium / Hard)
- Scientific Foundation (State-of-the-Art)
- Scientific Frontier (Post-V1 Evolution)
- Infrastructure Strategy (Phase 3)
- V1 Critical Path (Launch Blockers)
- Conclusion History (Archived)
- Assessments (Tasks)
- Attachments — Detailed Assessments

---

### 🧱 Backlog by Difficulty (Throughput / Medium / Hard)

Practical criteria:
- **Throughput**: Well-defined, mechanical changes with low risk (good for Mini).
- **Medium**: Require system context and some design, but with controllable scope.
- **Hard**: High risk, cross-dependencies, structural refactoring, concurrency, or security.

#### 🟢 Throughput

- Adjust CSP for production (reduce `unsafe-inline`/`unsafe-eval`) in *Security Headers Middleware*.
- Standardize success/error/warn toasts in critical flows in *UX Improvements*.
- Scan and centralize hardcoded settings/URLs in `environment.ts` in *Hardcoded Settings*.
- Sanitize `eslint-report.json` and lock regressions in CI in *Linter Bankruptcy*.

#### 🟡 Medium

- Complete *UI Coverage* (missing screens, empty/error/loading states).
- Resolve *Autonomy 500 Error* (reproduce, fix, test).
- Implement *Input Sanitization* (policy per endpoint + extra validation of free payloads).
- Evolve *Smart Model Routing* with complexity classification (heuristic/embedding).

#### 🔴 Hard

- Fix *Broken Thought Stream* (RabbitMQ → SSE → UI) with E2E test.
- Eliminate *State Desync* (define single source of state and migrate).
- Replace *Ad-hoc State Management* with robust store (SignalStore/Elf/NgRx).
- Unify Design System (*Design System Conflict*: remove Material gradually).
- Implement *Immutable Audit Log* (append-only + tamper-evident + access).
- Finalize *Database Migration Pipeline* (Alembic + CI/deploy).
- Implement *Graceful Degradation* (degradation matrix + health/alerts).
- Scientific Foundation/Frontier: pending research/implementation items (LATS/ToT/Self-RAG/RAPTOR/etc).

### 🔬 Scientific Foundation (State-of-the-Art)

*Architecture based on 13+ seminal papers that underpin Janus intelligence.*

#### 🧠 Reasoning & Planning (The Brain)

* [ ] **LATS (Language Agent Tree Search)** - *Zhou et al., 2023*
  * **Concept**: Combines LLM with Monte Carlo Tree Search (MCTS) to explore multiple solution paths.
  * **In Janus**: `Planner` node that simulates scenarios before executing critical actions (e.g., deploy).
* [x] **Reflexion** - *Shinn et al., 2023*
  * **Concept**: Agents that verbalize errors and keep lessons in short-term memory.
  * **In Janus**: Self-correction loop in `CoderAgent` for compilation errors.
* [x] **Graph of Thoughts (GoT)** - *Besta et al., 2023*
  * **Concept**: Models thought as a graph (DAG), allowing combining and refining ideas.
  * **In Janus**: Non-linear orchestration in LangGraph (Supervisor Node).
* [ ] **Tree of Thoughts (ToT)** - *Yao et al., 2023*
  * **Concept**: Deliberate exploration of multiple reasoning branches.
  * **In Janus**: Basis for the decision process of the `Meta-Agent`.
* [ ] **Chain of Thought (CoT)** - *Wei et al., 2022*
  * **Concept**: "Let's think step by step".
  * **In Janus**: Mandatory pattern in all system prompts.

#### 💾 Memory & Learning (The Soul)

* [ ] **Generative Agents** - *Park et al., 2023*
  * **Concept**: Memory with Recency, Importance, and Relevance + "Dreaming" (Consolidation).
  * **In Janus**: Architecture of `MemoryService` and nightly consolidation worker in Neo4j.
* [ ] **MemGPT** - *Packer et al., 2023*
  * **Concept**: Infinite context management via pagination (OS-like memory management).
  * **In Janus**: Context pagination strategy for long conversations.
* [ ] **Voyager** - *Wang et al., 2023*
  * **Concept**: Continuous learning via skill library (Skill Library).
  * **In Janus**: Persistence of tools and successful scripts for reuse.

#### 🔍 Retrieval & RAG (The Knowledge)

* [ ] **Self-RAG** - *Asai et al., 2023*
  * **Concept**: The model critiques its own retrieval (`[IsREL]`, `[IsSUP]`).
  * **In Janus**: `NativeGraphRAG` pipeline with verification step.
* [x] **HyDE (Hypothetical Document Embeddings)** - *Gao et al., 2022*
  * **Concept**: Generate ideal hypothetical answer to search for similar documents.
  * **In Janus**: Improvement in Qdrant vector search.
* [ ] **RAPTOR** - *Sarthi et al., 2024*
  * **Concept**: Recursive tree indexing (summaries of summaries).
  * **In Janus**: Hierarchical knowledge structure in Neo4j.

#### 🤖 Multi-Agent (The Body)

* [ ] **MetaGPT** - *Hong et al., 2023*
  * **Concept**: SOPs (Standard Operating Procedures) encoded for agents.
  * **In Janus**: Rigid definition of roles (Product Manager, Architect, Engineer).
* [ ] **CAMEL** - *Li et al., 2023*
  * **Concept**: "Role-Playing" architecture for communicative communication.
  * **In Janus**: Communication protocol between Supervisor and Workers.

#### 🛡️ Safety & Alignment (The Conscience)

* [ ] **Constitutional AI** - *Bai et al., 2022 (Anthropic)*
  * **Concept**: Behavior control through a "Constitution" (natural rules) instead of extensive manual RLHF.
  * **In Janus**: Extension of `ReflectorAgent` to validate outputs against safety rules (`security.yaml`) before delivery.

#### ⚡ Optimization & Economy (Efficiency)

* [ ] **FrugalGPT (LLM Cascades)** - *Chen et al., 2023*
  * **Concept**: Call smaller/cheaper models first; scale to SOTA models only if confidence is low.
  * **In Janus**: `ModelRouter` in infrastructure attempting to resolve with Llama-3-Local/Mini before calling DeepSeek/GPT-4.
* [ ] **DSPy (Programming with Prompts)** - *Khattab et al., 2023*
  * **Concept**: Abstract prompts as optimizable parameters. The system "compiles" and improves its own prompts based on metrics.
  * **In Janus**: Self-tuning pipeline for Worker prompts based on error/success feedback.

#### 🎨 HCI & Experience (The Interface)

* [ ] **Generative UI** - *Vercel AI SDK v5 / Dynaboard*
  * **Concept**: UI is dynamically generated by the LLM to adapt to user intent (tables, charts, on-the-fly forms).
  * **In Janus**: Utilization of `Angular Dynamic Components` + `ViewContainerRef` to render visual components based on tool-calls.

---

### 🧪 Scientific Frontier (Post-V1 Evolution)

*Vanguard concepts (2025/2026) to transform Janus into an embryonic AGI.*

#### 🧩 Self-Evolving Toolset (Agent-0 Style)

* **Concept**: The agent not only uses tools, it **creates** its own tools.
* **Implementation**: `ToolSynthesizerAgent`. When Janus identifies a repetitive task without a tool, it writes a Python script, validates it in the Sandbox, and if it works, saves it in the DB as a new permanent `Tool`.

#### 🐝 Swarm Intelligence (Decentralization)

* **Concept**: Abandon centralized orchestration for a swarm model.
* **Implementation**: **Dynamic Handoffs**. Agents can transfer execution directly to other specialists (`transfer_to_agent`) without going through the Supervisor, reducing latency and bottlenecks.

#### 💾 Active Memory Management (OS-Level)

* **Concept**: The LLM actively manages its context window like an Operating System manages RAM.
  * **Implementation**: Control token `<memory_warning>`. When context fills up, the agent is forced to decide what to "forget" (delete) or "archive" (save to Neo4j) before continuing.

#### 🧬 Code Generation & Rigor

1. **Flow Engineering / AlphaCodium** - *CodiumAI, 2024*
    * **Concept**: Replace "zero-shot coding" with a rigid iterative flow: *YAML Analysis -> Plan -> Tests -> Code -> Fix*.
    * **In Janus**: Refactoring of `CoderAgent` to follow this rigid StateFlow (increases accuracy from ~19% to ~44%).
2. **Hippocampal Memory Replay** - *DeepMind/Stanford*
    * **Concept**: Offline consolidation. The agent "dreams" (simulates tasks) during idle time to reinforce connections in the Graph.
    * **In Janus**: Upgrade in `SelfStudyManager` to run replays of past experiences.

#### ⏱️ Latency & UX

1. **Skeleton-of-Thought** - *Ning et al., 2023*
    * **Concept**: Generate the skeleton (topics) of the answer first, then fill in the content in parallel.
    * **In Janus**: Optimization for long answers in chat, reducing perceived latency.

---

### 🏛️ Infrastructure Strategy (Phase 3)

#### 🧠 Model Routing Strategy (The "Brains")

* **DeepSeek V3/R1** (The Workhorse):
  * *Usage*: Heavy coding, refactoring, generation.
  * *Why*: Best cost-benefit for code (beats GPT-4 in dev benchmarks).
  * *Cost*: ~$0.14/1M input | ~$0.28/1M output.

* **Qwen 2.5 72B** (The Architect):
  * *Usage*: Critical review, System Design, Logic validation.
  * *Why*: SOTA level coding performance (similar to Claude/GPT-4), but extremely accessible.
  * *Cost*: ~$0.12/1M input | ~$0.39/1M output.
  * *Comparative*: **GPT-5.2 Mini** costs **$2.00/1M output** (5x more expensive) and offers no real free quota.

* **Llama-3-Local / Flash** (The Speedster):
* *Usage*: Fast chat, Classification, Routing.

#### 💰 Budget & Rate Limiting Strategy (Dual-Wallet)

* **Wallet A (DeepSeek API - $9.50)**:
  * **Usage**: 100% dedicated to **Workhorse (DeepSeek V3)**.
  * **Advantage**: Lower latency (direct source) and does not consume OpenRouter balance.

* **Wallet B (OpenRouter - $10.00)**:
  * **Primary Usage**: **Architect (Qwen 2.5 72B)** (Reviews and Decisions).
  * **Perk**: Having credit >$0 unlocks **1000 requests/day** on Free/Trial models.
  * **Secondary Usage**: Speedster (Llama 3 Free) via free daily quota.

* **Suggested Daily Distribution**:
    1. **Workhorse (Via Direct API)**: ~700 requests (Consumes balance A).
    2. **Architect (Via OpenRouter)**: ~200 requests (Consumes balance B).
    3. **Speedster (Via OpenRouter Free)**: ~100 requests (Consumes daily quota, zero cost).

#### ☢️ The Privacy Dilemma (Option C)

* **OpenAI Data Sharing (Complimentary Tokens)**:
  * **What it is**: OpenAI offers free tokens (e.g., 250k/day) if you allow them to train on your data.
  * **The "Nightmare" Risk**: All Janus code, prompts, and strategy become OpenAI training property. If Janus creates something innovative, OpenAI learns it.
  * **Verdict**: **Enable ONLY if the project has no commercial secrets/critical IP.** Otherwise, the cost of violated privacy >>> saving $10.

#### 🛡️ The Free-Tier Army (Option D - Risk Free)

The best *real* free quotas of 2026 (No privacy cost):

1. **Google Gemini (Free Tier)**:
    * **Quota**: ~1500 requests/day (Flash 2.5).
    * **Usage**: Summaries of long texts, multimodal processing (images/video).
2. **Groq (Free Tier)**:
    * **Quota**: ~14.4k requests/day (Llama 3.1 8B) or ~1k/day (larger models).
    * **Usage**: Ultra-fast routing, simple chat.
3. **Cohere (Trial)**: ~1000 calls/month (Limited, good only for sporadic Reranking).

#### 📜 Protocol: Strict Structured Outputs

* **Decision**: Abandon generic "JSON Mode".
* **New Standard**: **Native Structured Outputs** (OpenAI `response_format` / Anthropic `tool_use` with `strict: true`).
* **DeepSeek Specifics**: DeepSeek V3 supports *Strict Mode* (Function Calling) via `beta` endpoint or advanced prompt engineering. We will use the OpenAI-compatible standard from DeepSeek.
* **Reason**: Guarantees 100% adherence to Schema (zero parse errors), eliminating retry loops and manual validators.

---

### 🚨 V1 Critical Path (Launch Blockers)

*Mandatory items for version 1.0 launch.*

#### 🛡️ Security & Enterprise Ready

* [x] **Security Headers Middleware**: Implement CSP, HSTS, X-Frame-Options, and X-Content-Type-Options.
  - [x] Middleware created (`SecurityHeadersMiddleware`).
  - [x] Registered in FastAPI (`app.add_middleware(SecurityHeadersMiddleware)`).
  - [x] Headers applied in response (CSP, HSTS, XFO, X-CTO, Referrer/Permissions).
  - [ ] Adjust CSP for production (reduce/avoid `unsafe-inline` and `unsafe-eval` when possible).

* [ ] **Input Sanitization**: Validate and sanitize all API inputs (injection prevention).
  - [ ] Define sanitization policy per endpoint (query/body/path).
  - [ ] Apply extra validation for free payloads (e.g., prompts, URLs, markdown).
  - [ ] Standardize validation errors (Problem+JSON) and metrics.
* [ ] **Rate Limiting (Cost-Based)**: Limit users by **spending in dollars**, not just requests.
  - [x] Daily budget per user/project applied in LLM calls (`max_tokens` cut by USD).
  - [x] Spend tracking by tenant/provider in Redis (spend USD).
  - [ ] Propagate enforcement to HTTP gateway (block by budget per endpoint/user).
* [ ] **Immutable Audit Log**: Ensure critical action logs cannot be altered.
  - [ ] Define event format (append-only) and critical action categories.
  - [ ] Persist events with chained hash (tamper-evident).
  - [ ] Expose audit/query with access control.

#### 🖥️ Frontend V1 (Refactor & Finish)

* [ ] **UI Overhaul (Clean/Professional)**: Migrate from "Magicpunk" to a professional/minimalist SaaS aesthetic (Shadcn/UI + Tailwind).
  - [ ] Consolidate tokens (colors/spacing/typography) and remove legacy styles.
  - [ ] Replace main components with equivalents in the new design system.
  - [ ] Define consistent base layout (header/sidebar/cards/tables).
* [ ] **Complete UI Coverage**: Implement missing screens (80%+) following the new Design System (Tools, Workers, RAG).
  - [ ] Map missing pages/screens and prioritize by usage.
  - [ ] Implement routes and empty states (empty/error/loading).
  - [ ] Ensure visual and interaction consistency (buttons, tables, dialogs).

* [ ] **UX Improvements**:
  * Real-time Feedback (Global Toasts).
  * Onboarding Flow (Setup Wizard).
  * Friendly error handling.
  - [x] Global Toast infra available (UiToastService/UiToasterComponent).
  - [ ] Standardize toasts for success/error/warn in critical flows.
  - [ ] Create onboarding wizard (first access / setup).
  - [ ] Normalize error messages from API (Problem+JSON) to UI.

##### 🐛 Critical Bugs & Failures (High Priority)

* [ ] **Broken Thought Stream**: Agent thought stream (SSE) is not receiving events from RabbitMQ (Chat Screen).
  - [ ] Confirm event consumption (RabbitMQ) in backend and fanout to SSE.
  - [ ] Validate event contract (types/payload) and ordering.
  - [ ] E2E Test: publish event -> UI receives and renders.
* [ ] **Autonomy 500 Error**: Internal Server Error (500) prevents creation of Strategic Goals.
  - [ ] Reproduce error and capture stacktrace.
  - [ ] Fix validation/DI/repos and add test.
  - [ ] Ensure return with Problem+JSON for controlled error.
* [ ] **State Desync**: Lack of reactivity between Backend (Redis) and Frontend (NgRx/Signals).
  - [ ] Identify duplicate sources of truth (store/local state/cache).
  - [ ] Define single state strategy (SignalStore/Elf/NgRx) and migration.
  - [ ] Add reactivity tests (component/store).

##### 🏚️ Technical Debt & Clean Code

* [ ] **Linter Bankruptcy**: Huge `eslint-report.json` (>400KB). Massive correction and stricter rules needed.
  - [ ] Reduce critical violations first (security/bug-prone rules).
  - [ ] Ensure lint in CI and block regressions.
  - [ ] Remove/generate `eslint-report.json` only on demand.
* [ ] **Hardcoded Settings**: Remove hardcoded keys and URLs; move to `environment.ts`.
  - [ ] Scan for fixed URLs/keys in frontend.
  - [ ] Centralize in `environment.ts` + `api.config.ts`.
  - [ ] Ensure fallback by environment (dev/prod/tailscale).
* [ ] **Test Coverage Zero**: No unit or e2e tests running in frontend currently.
  - [ ] Ensure minimal suite running in CI (unit).
  - [ ] Add smoke e2e (login + chat).
  - [ ] Define coverage goal (per critical module).
* [x] **Legacy Testing Stack**: Update from Karma/Jasmine to Vitest/Jest + Testing Library (2026 Standard).
  - [x] Vitest configured in frontend (`vitest.config.ts` / script `npm test`).
  - [x] Testing Library present (`@testing-library/angular`).
* [ ] **Ad-hoc State Management**: Replace `GlobalStateStore` (Manual Signals with high cognitive load) with a robust lib (NgRx SignalStore or Elf) to avoid "State Desync".
  - [ ] Define target (NgRx SignalStore vs Elf) and guideline.
  - [ ] Migrate critical modules (Chat, Goals, Autonomy) first.
  - [ ] Remove redundant manual patterns after migration.
* [ ] **Design System Conflict**: Remove Angular Material gradually and unify on Shadcn/UI (Tailwind) to reduce bundle size and visual inconsistencies.
  - [ ] Map Angular Material usage points and prioritize replacements.
  - [ ] Remove dependencies/styles when migration reaches critical mass.

### ⚙️ Stability & Ops

* [ ] **Database Migration Pipeline**: Finalize transition to Alembic (abandon manual scripts).
  - [ ] Introduce Alembic (config + env) and first migration.
  - [ ] Integrate migrations in deploy/CI.
  - [ ] Document operational upgrade/downgrade flow.

* [ ] **Smart Model Routing**: Router that chooses between Local/API based on task complexity (Economy).
  - [x] Routing by role/priority available (Local vs Cloud).
  - [x] Budget guardrails and cost fallback in LLM pipeline.
  - [ ] Automatically classify complexity (heuristic/embedding) and adjust priority.
* [ ] **Graceful Degradation**: Clear fallbacks when services (e.g., Redis, Neo4j) fail.
  - [ ] Define degradation matrix by dependency (Redis/Neo4j/Qdrant/RabbitMQ).
  - [ ] Ensure fail-open/fail-closed behavior per endpoint as per criticality.
  - [ ] Expose status and alerts (health checks + metrics) for each degraded mode.

---

### ✅ Conclusion History (Archived)

#### Foundation & Architecture

* [x] **Hybrid Agent Architecture** (LangGraph + PydanticAI).

* [x] **Native GraphRAG** (neo4j-graphrag).
* [x] **Centralized HITL** (Human-in-the-loop via Postgres Checkpoints).
* [x] **Graph Versioning** (Schema Migration & Purge).
* [x] **Observability** (LangSmith Tracing & Setup).
* [x] **Async Database Pool** (asyncpg + SQLAlchemy).
* [x] **Secure Sandbox** (Docker-based execution).
* [x] **Migration MySQL → PostgreSQL** (pgvector).
* [x] **Redis State Backend**.

---

### 🧱 Assessments (Tasks)

* [x] **Batch 1 — Boot & Kernel** (assessment closed)
* [x] **Batch 2 — API & Endpoints** (assessment closed)
* [ ] **Batch 3 — Services (LLM, Chat, RAG, Observability, Autonomy)** (assessment + fixes)
* [ ] **Batch 4 — Repositories and persistence** (assessment + fixes)
* [ ] **Batch 5 — Agents, Tools and Sandbox** (assessment + fixes)
* [ ] **Batch 6 — TBD** (define scope)
* [ ] **Structural Infra — Processes & Resilience** (new)
  * [ ] **Separate planes**: move workers (Parliament, meta-agent, consolidator, auto-healer, autonomy) to own processes/containers; flags per environment to disable in dev/CI.
  * [ ] **Robust messaging**: ensure effective DLX/DLQ and publish fail-fast (retry/backoff + alert) instead of silent drop when RabbitMQ is offline; health gating on dependent routes.
  * [ ] **Lightweight startup**: remove heavy auto-index/warm-up from HTTP boot; make it opt-in via scheduled job and healthy readiness before serving traffic.
  * [ ] **Security by profile**: production mode with restricted CORS, mandatory API-Key/Bearer, and blocking of DANGEROUS tools outside allowlist; document dev vs prod profile.
  * [ ] **Worker supervision**: add monitor/restart/backoff for tasks created via `asyncio.create_task` (MAS actors, autonomy/lifecycle loops), avoiding silent failures.
  * [ ] **Resilient broker**: complete DLX/DLQ configuration (fanout bindings) and replace silent drop with retry + alert when `_connection` is None; add dead-letter for all critical queues.
  * [ ] **Neo4j reconnect**: implement reconnect/health gating when driver goes offline, avoiding getting stuck until restart.
  * [ ] **Duplicate metrics**: fix duplicate counters in `productivity.py` (repeated declaration of `_PROD_REQUESTS_TOTAL`/noop), ensuring unique names and consistent exports.
  * [ ] **Dangerous tools**: enforce policy for `execute_shell`/`write_file .py` (require explicit allowlist per environment and log/audit) to avoid inadvertent use in production.
  * [ ] **Secure endpoints**: create "prod" profile with restricted CORS and mandatory authentication (API-Key/Bearer) and consistent sanitization of free payloads (prompts/URLs/markdown) before processing.
  * [ ] **Scheduled warm-up/index**: move LLM warm-up and auto-indexing to opt-in asynchronous jobs (scheduler), maintaining healthy readiness in HTTP.

---

### 📎 Attachments — Detailed Assessments

#### ✅ Batch 1 — Boot & Kernel (CLOSED)

**Scope covered**: application lifecycle (lifespan), Kernel initialization, critical infrastructure, manual DI, warm-up, auto-indexing, workers, and shutdown.

**Deliverables completed**:

1) **Startup flow map (textual pipeline and criticality)**
   - FastAPI Lifespan initializes the Kernel and maps services in `app.state` with compatibility with old routes.
   - Kernel executes: infrastructure → MAS agents → DI → OS tools → workers → auto-index → warm-up → senses.
   - Critical steps (failures interrupt): infrastructure and MAS agents; "best-effort" steps: workers, warm-up, voice.

2) **Infra inventory and operational impact**
   - Infra initialized in parallel: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
   - Firebase is optional and does not block boot (non-critical failure).

3) **Coupling analysis (manual DI)**
   - Kernel concentrates the creation of repositories and services, increasing coupling and hindering isolated tests.
   - Injection flow is "eager" and not lazy, increasing startup cost.

4) **Workers and scheduler**
   - Workers start globally (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
   - No global flags to disable per environment, increasing cost in dev/CI.

5) **Warm-up and auto-indexing**
   - `AUTO_INDEX_ON_STARTUP=True` can cause high cost in large bases.
   - Background LLM warm-up is asynchronous but still consumes resources at boot.

**Technical recommendations (focused on cost and performance)**

- [ ] Parallelize prompt loading (reduce cold start latency).
- [ ] Incremental indexing based on hash/commit (avoid unnecessary O(N)).
- [ ] Create feature flags for workers per environment (reduce operational cost).
- [ ] Introduce lightweight DI container (reduce coupling and improve testability).

---

#### 🔍 Batch 2 — API & Endpoints (CLOSED)

**Objective**: map contracts, endpoints, validations, and performance impacts of the HTTP layer (FastAPI), including route governance and security.

##### Results (heart rigor)

1) **Complete v1 route inventory**
   - Total (Full API): 212 unique routes; 65 with Pydantic request model; 2 with File/Form upload.
   - Routes defined but not exposed in v1 router: admin_graph, meta, resources.
   - Real duplicates (same method/path): /optimization/* and /productivity/* (detail in inventory).
   - PUBLIC_API_MINIMAL mode exposed: /chat, /users, /profiles, /autonomy, /assistant, /autonomy/history, /consents, /pending_actions, /evaluation, /deployment, /auth, /auto-analysis, /feedback.

##### Complete Route Inventory (Full API)
Note: paths listed already include `/api/v1` prefix.

[Table omitted for brevity, refer to source code or Swagger for details.]

2) **Contracts and validations (Pydantic)**
   - models/schemas.py used only in memory (Experience, ScoredExperience) and tasks (QueueName); the rest defines local DTOs.
   - Free/sensitive inputs without clear limits:
     - /llm/invoke, /chat/message, /assistant/execute: prompt/message without max_length (cost/abuse risk).
     - /tools/create/from-function: code without limit/syntax validation; /tools/create/from-api without URL/headers validation.
     - /sandbox/execute and /sandbox/evaluate: arbitrary code/expression (requires hard gate and limits).
     - /documents/upload: limited size, but without MIME/extension whitelist and without scan.
     - /tasks/consolidation: free metadata (dict) without strict schema.
     - /rag/* and /knowledge/*: free query; lack of sanitization and limits per user.
   - Positive point: Autonomy validates plan steps and AgentExecutionRequest has max_length.

3) **HTTP Performance and middlewares**
   - Global middlewares: SecurityHeadersMiddleware, CorrelationMiddleware, RateLimitMiddleware, CORS, msgpack negotiation, Prometheus instrumentator.
   - RateLimit: token-bucket in Redis, fail-open if Redis falls; bypass only for /metrics, /healthz, /livez, /readyz.
   - msgpack negotiation does JSON decode/encode when Accept=application/msgpack; extra cost in large responses.
   - /system/overview and /system/health/services make sequential calls; can parallelize to reduce latency.
   - SSE (/chat/stream, /chat/{id}/events) does not pass through msgpack, OK.

4) **Governance and versioning**
   - Routes outside /api/v1: /, /health, /healthz, /metrics, /static.
   - Endpoints with code, but not registered: admin_graph, meta, resources.
   - Duplicity of include_router in /optimization and /productivity (duplicates routes and OpenAPI).
   - Naming inconsistency: /rag/user-chat vs /rag/user_chat; /pending_actions; /auto-analysis.

5) **API Security (keys and headers)**
   - X-API-Key is optional; when absent, entire API is exposed.
   - actor_user_id accepts X-User-Id without verification; allows impersonation if API key is shared.
   - Critical endpoints without auth/admin:
     /system/db/migrate, /system/db/validate, /workers/start-all, /workers/stop-all,
     /collaboration/system/shutdown, /sandbox/execute, /tools/create/*, /knowledge/clear,
     /knowledge/index, /observability/poison-pills/*, /optimization/analyze/run-cycle,
     /llm/ab/set-experiment, /llm/cache/*, /llm/response-cache/*, /tasks/queue/*/policy/reconcile.
   - Recommendation: separate admin routes, require JWT/role, remove X-User-Id fallback, apply allowlist per method.

6) **Cost checklist for LLM endpoints**
   - Core LLM has budgets, but user_id/project_id comes from payload; without authenticating identity, limits can be bypassed.
   - RateLimitMiddleware is by IP/API key, not by cost/tenant.
   - Chat/Assistant/Agent use LLM path; need to inherit authenticated identity for real cost.
   - /llm/budget/summary and /llm/pricing/providers exposed; ideal to restrict to admin.

#### Tasks

* [ ] Remove route duplicates (/optimization/* and /productivity/*)
* [ ] Decide destination of routes not exposed in v1 router (admin_graph/meta/resources)
* [ ] Standardize route naming and stabilize compatibility (e.g., /rag/user-chat → /rag/user_chat)
* [ ] Define size limits for free inputs (prompt/message/code/query) per endpoint
* [ ] Validate URL/headers in /tools/create/from-api and impose limits in /tools/create/from-function
* [ ] Hard gate critical endpoints with JWT/role (admin) and remove X-User-Id fallback
* [ ] Make X-API-Key mandatory when no JWT (remove exposed by default mode)
* [ ] Restrict administrative cost and cache endpoints (/llm/budget/summary, /llm/pricing/providers, /llm/*cache*)
* [ ] Add MIME/extension allowlist and scan in /documents/upload
* [ ] Parallelize calls in /system/overview and /system/health/services
* [ ] Propagate budget enforcement (USD) to HTTP gateway per user/tenant

#### Batch 3 - Services (LLM, Chat, RAG, Observability, Autonomy) (IN PROGRESS)

**Objective**: map the service layer and explicit critical dependencies in the Janus heart flow.

##### Tasks

* [ ] Impose size limits in LLMService (prompt + output)
* [ ] Impose size limits in ChatService (message + attachments)
* [ ] Standardize cost registration/estimation in Chat → LLM path
* [ ] Validate conversation ownership in service and SQL repository
* [ ] Make user_id/project_id mandatory and server-side before RAG/LLM
* [ ] Persist ChatEventPublisher events (avoid silent db_logger=None)
* [ ] Expose degradation telemetry in RAG and summarization (explicit failure)
* [ ] Implement backoff, limits, and cancellation in AutonomyLoop
* [ ] Unify repository interfaces used by ChatService and RAGService
* [ ] Centralize identity resolution before calling LLM/RAG/Autonomy

#### Batch 4 - Repositories and persistence (IN PROGRESS)

**Objective**: map repositories, data sources, and persistence contracts, highlighting inconsistencies and technical debts.

##### Tasks

* [ ] Standardize Postgres session (100% async or dedicated sync engine)
* [ ] Fix calls to db.get_session_direct (non-existent method) in repositories
* [ ] Align ChatRepositorySQL with DB infra (avoid incompatible sync Session)
* [ ] Rewrite PromptRepository for coherent flow (async) or separate sync/async
* [ ] Persist collaboration/tool/optimization/context/sandbox repositories (avoid loss on restart)
* [ ] Persist learning stats/experiments (avoid partial loss)
* [ ] Remove or archive file-based chat_repository if not used
* [ ] Define consistency strategy between SQL, Qdrant, and Neo4j (no UoW)
* [ ] Add retries/timeouts and confirmation in cross-store deletions
* [ ] Type Memory/Knowledge repo returns and standardize errors at repo level
* [ ] Finalize Alembic and ensure migrations for new models (e.g., ModelDeployment)
* [ ] Remove db.create_tables from boot in production

#### Batch 5 - Agents, Tools, and Sandbox (IN PROGRESS)

**Objective**: map agent orchestration, tool-calls, and sandbox, highlighting policy, execution, and isolation failures.

##### Tasks

* [ ] Apply PolicyEngine, rate limit, and confirmation in all tool-calls from chat
* [ ] Ensure action_registry.record_call in tool-calls flow (full telemetry)
* [ ] Fix ChatAgentLoop fallback (execute_tool_calls does not accept strict)
* [ ] Add timeout and concurrency limit per tool in ToolExecutorService
* [ ] Fix missing awaits in core/autonomy/planner.py (draft/critique/refine/replan/verify)
* [ ] Cover planner/autonomy with regression test (coroutine/await)
* [ ] Unify sandbox and integrate Docker executor to service flow
* [ ] Align SandboxService.get_capabilities with real enforcement (timeout/CPU/mem/output)
* [ ] Persist rate limit and stats per user/tenant (Redis/DB) and standardize HITL flow

### Next step after Batch 5
- Batch 6: TBD (define scope).
