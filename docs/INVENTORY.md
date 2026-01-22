# 📋 System Inventory & Tasks
>
> *Last updated: 2026-01-14*

This document tracks detailed system surveys, task batches, and API inventories.

## 📌 Index

- [Task Surveys (Batches)](#-task-surveys-batches)
- [Detailed Appendices](#-detailed-appendices)
  - [Batch 1 — Boot & Kernel](#-batch-1--boot--kernel-closed)
  - [Batch 2 — API & Endpoints](#-batch-2--api--endpoints-closed)
  - [Batch 3 — Services](#batch-3---services-llm-chat-rag-observability-autonomy-in-progress)
  - [Batch 4 — Repositories](#batch-4---repositories-and-persistence-in-progress)
  - [Batch 5 — Agents](#batch-5---agents-tools-and-sandbox-in-progress)
  - [Structural Infra](#structural-infra--processes--resilience-new)

---

## 🧱 Task Surveys (Batches)

* [x] **Batch 1 — Boot & Kernel** (survey closed)
* [x] **Batch 2 — API & Endpoints** (survey closed)
* [ ] **Batch 3 — Services (LLM, Chat, RAG, Observability, Autonomy)** (survey + corrections)
* [ ] **Batch 4 — Repositories and persistence** (survey + corrections)
* [ ] **Batch 5 — Agents, Tools and Sandbox** (survey + corrections)
* [ ] **Batch 6 — TBD** (define scope)
* [ ] **Structural Infra — Processes & Resilience** (new)

---

## 📎 Detailed Appendices

### ✅ Batch 1 — Boot & Kernel (CLOSED)

**Scope covered**: application lifecycle (lifespan), Kernel initialization, critical infrastructure, manual DI, warm-up, auto-indexing, workers, and shutdown.

**Completed deliverables**:

1) **Startup flow map (textual pipeline and criticality)**
   - FastAPI Lifespan initializes the Kernel and maps services in `app.state` with legacy route compatibility.
   - Kernel executes: infrastructure → MAS agents → DI → OS tools → workers → auto-index → warm-up → senses.
   - Critical steps (failures interrupt): infrastructure and MAS agents; "best-effort" steps: workers, warm-up, voice.

2) **Infra inventory and operational impact**
   - Infra initialized in parallel: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
   - Firebase is optional and does not block boot (non-critical failure).

3) **Coupling analysis (manual DI)**
   - Kernel concentrates repository and service creation, increasing coupling and hindering isolated tests.
   - Injection flow is "eager" not lazy, increasing startup cost.

4) **Workers and scheduler**
   - Workers start globally (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
   - No global flags to disable per environment, raising cost in dev/CI.

5) **Warm-up and auto-indexing**
   - `AUTO_INDEX_ON_STARTUP=True` can cause high cost on large bases.
   - Background LLM warm-up is asynchronous but still consumes resources at boot.

**Technical recommendations (focused on cost and performance)**

- [ ] Parallelize prompt loading (reduce cold start latency).
- [ ] Incremental indexing based on hash/commit (avoid unnecessary O(N)).
- [ ] Create feature flags for workers per environment (reduce operational cost).
- [ ] Introduce lightweight DI container (reduce coupling and improve testability).

---

### 🔍 Batch 2 — API & Endpoints (CLOSED)

**Objective**: map contracts, endpoints, validations, and performance impacts of the HTTP layer (FastAPI), including route governance and security.

#### Results (Heart Rigor)

1) **Complete v1 route inventory**
   - Total (Full API): 212 unique routes; 65 with Pydantic request model; 2 with File/Form upload.
   - Routes defined but not exposed in v1 router: admin_graph, meta, resources.
   - Real duplicates (same method/path): /optimization/* and /productivity/* (detail in inventory).
   - PUBLIC_API_MINIMAL mode exposed: /chat, /users, /profiles, /autonomy, /assistant, /autonomy/history, /consents, /pending_actions, /evaluation, /deployment, /auth, /auto-analysis, /feedback.

#### Complete Route Inventory (Full API)
*Note: paths listed include `/api/v1` prefix.*

*(Refer to `Melhorias possiveis.md` or source code for the full table if needed, summarized below)*
*Key Findings:*
- `/optimization` and `/productivity` have duplicate route handlers.
- Many endpoints lack explicit Pydantic models for freeform payloads.
- Critical endpoints exposed without strict admin checks in some configurations.

2) **Contracts and validations (Pydantic)**
   - `models/schemas.py` used only in memory and tasks; others define local DTOs.
   - Free/sensitive inputs without clear limits:
     - `/llm/invoke`, `/chat/message`: no max_length (cost/abuse risk).
     - `/sandbox/execute`: arbitrary code/expression (requires hard gate).
     - `/documents/upload`: limited size but no MIME whitelist.
   - Positive: Autonomy validates plan steps.

3) **HTTP Performance and middlewares**
   - Global middlewares: SecurityHeaders, Correlation, RateLimit, CORS, msgpack negotiation, Prometheus.
   - RateLimit: Redis token-bucket, fail-open; bypass for health/metrics.
   - Msgpack negotiation adds cost for large responses.
   - `/system/overview` makes sequential calls; could be parallelized.

4) **Governance and versioning**
   - Routes outside `/api/v1`: `/`, `/health`, `/metrics`, etc.
   - Endpoints with code but unregistered: `admin_graph`, `meta`, `resources`.
   - Naming inconsistencies: `/rag/user-chat` vs `/rag/user_chat`.

5) **API Security (Keys and Headers)**
   - `X-API-Key` optional; if missing, API fully exposed.
   - `actor_user_id` accepts `X-User-Id` without verification (impersonation risk).
   - Critical endpoints without auth/admin checks identified.

6) **LLM Cost Checklist**
   - Core LLM has budgets, but identity resolution needs hardening.
   - `RateLimitMiddleware` is by IP/Key, not cost/tenant.

#### Tasks

* [ ] Remove route duplicates (`/optimization/*` and `/productivity/*`)
* [ ] Decide fate of unexposed routes (`admin_graph`/`meta`/`resources`)
* [ ] Standardize route naming (`/rag/user-chat` → `/rag/user_chat`)
* [ ] Define size limits for free inputs per endpoint
* [ ] Validate URL/headers in `/tools` and impose limits
* [ ] Hard gate critical endpoints with JWT/role (admin)
* [ ] Make `X-API-Key` mandatory when no JWT present
* [ ] Restrict administrative cost/cache endpoints
* [ ] Add MIME allowlist and scanning in `/documents/upload`
* [ ] Parallelize calls in `/system/overview`
* [ ] Propagate budget enforcement to HTTP gateway

### Batch 3 - Services (LLM, Chat, RAG, Observability, Autonomy) (IN PROGRESS)

**Objective**: map service layer and explicit critical pending items in Janus core flow.

#### Tasks

* [ ] Impose size limits in `LLMService` (prompt + output)
* [ ] Impose size limits in `ChatService` (message + attachments)
* [ ] Standardize cost registration/estimation in Chat → LLM path
* [ ] Validate conversation ownership in service and SQL repo
* [ ] Make `user_id`/`project_id` mandatory and server-side before RAG/LLM
* [ ] Persist `ChatEventPublisher` events (avoid silent `db_logger=None`)
* [ ] Expose degradation telemetry in RAG and summarization
* [ ] Implement backoff, limits, and cancellation in `AutonomyLoop`
* [ ] Unify repository interfaces used by `ChatService` and `RAGService`
* [ ] Centralize identity resolution before calling LLM/RAG/Autonomy

### Batch 4 - Repositories and persistence (IN PROGRESS)

**Objective**: map repositories, data sources, and persistence contracts, highlighting inconsistencies.

#### Tasks

* [ ] Standardize Postgres session (100% async or dedicated sync engine)
* [ ] Fix calls to `db.get_session_direct` (non-existent method) in repos
* [ ] Align `ChatRepositorySQL` with db infra (avoid incompatible sync Session)
* [ ] Rewrite `PromptRepository` for coherent flow (async)
* [ ] Persist collaboration/tool/optimization repositories (avoid restart loss)
* [ ] Persist learning stats/experiments
* [ ] Remove or archive file-based `chat_repository` if unused
* [ ] Define consistency strategy between SQL, Qdrant, and Neo4j
* [ ] Add retries/timeouts and confirmation in cross-store deletions
* [ ] Type returns of Memory/Knowledge repos
* [ ] Finalize Alembic and ensure migrations for new models
* [ ] Remove `db.create_tables` from boot in production

### Batch 5 - Agents, Tools and Sandbox (IN PROGRESS)

**Objective**: map agent orchestration, tool-calls, and sandbox.

#### Tasks

* [ ] Apply PolicyEngine, rate limit, and confirmation in all tool-calls
* [ ] Ensure `action_registry.record_call` in tool-calls flow
* [ ] Fix `ChatAgentLoop` fallback (execute_tool_calls doesn't accept strict)
* [ ] Add timeout and concurrency limit per tool in `ToolExecutorService`
* [ ] Fix missing awaits in `core/autonomy/planner.py`
* [ ] Cover planner/autonomy with regression test
* [ ] Unify sandbox and integrate Docker executor to services flow
* [ ] Align `SandboxService.get_capabilities` with real enforcement
* [ ] Persist rate limit and stats per user/tenant

### Structural Infra — Processes & Resilience (new)
  * [ ] **Separate plans**: move workers (Parliament, meta-agent, consolidator, auto-healer, autonomy) to own processes/containers; flags per environment.
  * [ ] **Robust messaging**: ensure DLX/DLQ effective and publish fail-fast (retry/backoff) instead of silent drop.
  * [ ] **Lightweight startup**: remove heavy auto-index/warm-up from HTTP boot; make opt-in via scheduled job.
  * [ ] **Security by profile**: production mode with restricted CORS, mandatory API-Key/Bearer, and DANGEROUS tools block.
  * [ ] **Worker supervision**: add monitor/restart/backoff for tasks created via `asyncio.create_task`.
  * [ ] **Resilient Broker**: complete DLX/DLQ config and replace silent drop with retry.
  * [ ] **Neo4j reconnect**: implement reconnect/health gating.
  * [ ] **Duplicate metrics**: fix duplicate counters in `productivity.py`.
  * [ ] **Dangerous tools**: enforce strict policy for `execute_shell`/`write_file .py`.
  * [ ] **Secure endpoints**: create "prod" profile with restricted CORS and mandatory auth.
  * [ ] **Scheduled Warm-up/index**: move LLM warm-up and auto-indexing to async jobs (scheduler).
