# 📋 Inventory & Surveys
>
> *Detailed analysis of the current system state, tasks, and API inventory.*

## 🧱 Surveys (Tasks)

* [x] **Batch 1 — Boot & Kernel** (survey closed)
* [x] **Batch 2 — API & Endpoints** (survey closed)
* [ ] **Batch 3 — Services (LLM, Chat, RAG, Observability, Autonomy)** (survey + fixes)
* [ ] **Batch 4 — Repositories and Persistence** (survey + fixes)
* [ ] **Batch 5 — Agents, Tools, and Sandbox** (survey + fixes)
* [ ] **Batch 6 — TBD** (define scope)
* [ ] **Structural Infra — Processes & Resilience** (new)
  * [ ] **Separate planes**: move workers (Parliament, meta-agent, consolidator, auto-healer, autonomy) to their own processes/containers; flags per environment to disable in dev/CI.
  * [ ] **Robust messaging**: ensure effective DLX/DLQ and publish fail-fast (retry/backoff + alert) instead of silent drop when RabbitMQ is offline; health gating on dependent routes.
  * [ ] **Lightweight startup**: remove heavy auto-index/warm-up from HTTP boot; make it opt-in via scheduled job and healthy readiness before serving traffic.
  * [ ] **Security per profile**: production mode with restricted CORS, mandatory API-Key/Bearer, and blocking of DANGEROUS tools outside allowlist; document dev vs prod profile.
  * [ ] **Worker supervision**: add monitor/restart/backoff for tasks created via `asyncio.create_task` (MAS actors, autonomy/lifecycle loops), avoiding silent failures.
  * [ ] **Resilient Broker**: complete DLX/DLQ configuration (fanout bindings) and replace silent drop with retry + alert when `_connection` is None; add dead-letter for all critical queues.
  * [ ] **Neo4j reconnect**: implement reconnect/health gating when the driver goes offline, avoiding being stuck until restart.
  * [ ] **Duplicate metrics**: fix duplicate counters in `productivity.py` (repeated declaration of `_PROD_REQUESTS_TOTAL`/noop), ensuring unique names and consistent exports.
  * [ ] **Dangerous Tools**: reinforce policy for `execute_shell`/`write_file .py` (require explicit allowlist per environment and log/audit) to avoid inadvertent use in production.
  * [ ] **Secure Endpoints**: create "prod" profile with restricted CORS and mandatory authentication (API-Key/Bearer) and consistent sanitization of free payloads (prompts/URLs/markdown) before processing.
  * [ ] **Scheduled Warm-up/Index**: move LLM warm-up and auto-indexing to opt-in asynchronous jobs (scheduler), maintaining healthy readiness in HTTP.

---

## 📎 Appendices — Detailed Surveys

### ✅ Batch 1 — Boot & Kernel (CLOSED)

**Covered Scope**: application lifecycle (lifespan), Kernel initialization, critical infrastructure, manual DI, warm-up, auto-indexing, workers, and shutdown.

**Completed Deliverables**:

1) **Startup flow map (textual pipeline and criticality)**
   - FastAPI Lifespan initializes the Kernel and maps services in `app.state` with compatibility for old routes.
   - The Kernel executes: infrastructure → MAS agents → DI → OS tools → workers → auto-index → warm-up → senses.
   - Critical steps (failures interrupt): infrastructure and MAS agents; "best-effort" steps: workers, warm-up, voice.

2) **Infra inventory and operational impact**
   - Infra initialized in parallel: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
   - Firebase is optional and does not block boot (non-critical failure).

3) **Coupling analysis (Manual DI)**
   - Kernel concentrates the creation of repositories and services, increasing coupling and hindering isolated tests.
   - The injection flow is "eager" and not lazy, increasing startup cost.

4) **Workers and scheduler**
   - Workers start globally (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
   - There are no global flags to disable per environment, raising cost in dev/CI.

5) **Warm-up and auto-indexing**
   - `AUTO_INDEX_ON_STARTUP=True` can cause high cost in large bases.
   - LLM warm-up in background is asynchronous, but still consumes resources at boot.

**Technical Recommendations (focusing on cost and performance)**

- [ ] Parallelize prompt loading (reduces cold start latency).
- [ ] Incremental indexing based on hash/commit (avoids unnecessary O(N)).
- [ ] Create feature flags for workers per environment (reduces operational cost).
- [ ] Introduce lightweight DI container (reduces coupling and improves testability).

---

### 🔍 Batch 2 — API & Endpoints (CLOSED)

**Objective**: map contracts, endpoints, validations, and performance impacts of the HTTP layer (FastAPI), including route governance and security.

#### Results (Rigor of the "Heart")

1) **Complete V1 Route Inventory**
   - Total (Full API): 212 unique routes; 65 with Pydantic request model; 2 with File/Form upload.
   - Defined routes, but not exposed in v1 router: admin_graph, meta, resources.
   - Real duplicates (same method/path): /optimization/* and /productivity/* (detail in inventory).
   - PUBLIC_API_MINIMAL mode exposed: /chat, /users, /profiles, /autonomy, /assistant, /autonomy/history, /consents, /pending_actions, /evaluation, /deployment, /auth, /auto-analysis, /feedback.

#### Complete Route Inventory (Full API)
Note: listed paths already include the `/api/v1` prefix.

*(Refer to Swagger/OpenAPI documentation or source code for the full table)*

2) **Contracts and Validations (Pydantic)**
   - models/schemas.py used only in memory (Experience, ScoredExperience) and tasks (QueueName); the rest defines local DTOs.
   - Free/sensitive inputs without clear limits:
     - /llm/invoke, /chat/message, /assistant/execute: prompt/message without max_length (cost/abuse risk).
     - /tools/create/from-function: code without limit/syntax validation; /tools/create/from-api without URL/headers validation.
     - /sandbox/execute and /sandbox/evaluate: arbitrary code/expression (requires hard gate and limits).
     - /documents/upload: limited size, but without MIME/extension whitelist and without scan.
     - /tasks/consolidation: free metadata (dict) without strict schema.
     - /rag/* and /knowledge/*: free query; lacks sanitization and limits per user.
   - Positive point: Autonomy validates plan steps and AgentExecutionRequest has max_length.

3) **HTTP Performance and Middlewares**
   - Global Middlewares: SecurityHeadersMiddleware, CorrelationMiddleware, RateLimitMiddleware, CORS, msgpack negotiation, Prometheus instrumentator.
   - RateLimit: token-bucket in Redis, fail-open if Redis fails; bypass only for /metrics, /healthz, /livez, /readyz.
   - msgpack negotiation does JSON decode/encode when Accept=application/msgpack; extra cost on large responses.
   - /system/overview and /system/health/services make sequential calls; can parallelize to reduce latency.
   - SSE (/chat/stream, /chat/{id}/events) does not go through msgpack, OK.

4) **Governance and Versioning**
   - Routes outside /api/v1: /, /health, /healthz, /metrics, /static.
   - Endpoints with code, but not registered: admin_graph, meta, resources.
   - `include_router` duplication in /optimization and /productivity (duplicates routes and OpenAPI).
   - Inconsistent naming: /rag/user-chat vs /rag/user_chat; /pending_actions; /auto-analysis.

5) **API Security (Keys and Headers)**
   - X-API-Key is optional; when absent, entire API is exposed.
   - actor_user_id accepts X-User-Id without verification; allows impersonation if API key is shared.
   - Critical endpoints without auth/admin:
     /system/db/migrate, /system/db/validate, /workers/start-all, /workers/stop-all,
     /collaboration/system/shutdown, /sandbox/execute, /tools/create/*, /knowledge/clear,
     /knowledge/index, /observability/poison-pills/*, /optimization/analyze/run-cycle,
     /llm/ab/set-experiment, /llm/cache/*, /llm/response-cache/*, /tasks/queue/*/policy/reconcile.
   - Recommendation: separate admin routes, require JWT/role, remove X-User-Id fallback, apply allowlist per method.

6) **Cost Checklist for LLM Endpoints**
   - Core LLM has budgets, but user_id/project_id comes from payload; without authenticating identity, limits can be bypassed.
   - RateLimitMiddleware is by IP/API key, not by cost/tenant.
   - Chat/Assistant/Agent use LLM path; need to inherit authenticated identity for real cost.
   - /llm/budget/summary and /llm/pricing/providers exposed; ideal to restrict to admin.

#### Tasks

* [ ] Remove route duplications (/optimization/* and /productivity/*)
* [ ] Decide destination of routes not exposed in v1 router (admin_graph/meta/resources)
* [ ] Standardize route naming and stabilize compatibility (e.g., /rag/user-chat → /rag/user_chat)
* [ ] Define size limits for free inputs (prompt/message/code/query) per endpoint
* [ ] Validate URL/headers in /tools/create/from-api and impose limits in /tools/create/from-function
* [ ] Hard gate critical endpoints with JWT/role (admin) and remove X-User-Id fallback
* [ ] Make X-API-Key mandatory when there is no JWT (remove exposed by default mode)
* [ ] Restrict administrative cost and cache endpoints (/llm/budget/summary, /llm/pricing/providers, /llm/*cache*)
* [ ] Add MIME/extension allowlist and scanning in /documents/upload
* [ ] Parallelize calls in /system/overview and /system/health/services
* [ ] Propagate budget enforcement (USD) to HTTP gateway per user/tenant

### Batch 3 - Services (LLM, Chat, RAG, Observability, Autonomy) (IN PROGRESS)

**Objective**: map the service layer and explicit critical pending items in the Janus heart flow.

#### Tasks

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

### Batch 4 - Repositories and Persistence (IN PROGRESS)

**Objective**: map repositories, data sources, and persistence contracts, highlighting inconsistencies and technical debt.

#### Tasks

* [ ] Standardize Postgres session (100% async or dedicated sync engine)
* [ ] Fix calls to db.get_session_direct (non-existent method) in repositories
* [ ] Align ChatRepositorySQL with DB infra (avoid incompatible sync Session)
* [ ] Rewrite PromptRepository for coherent flow (async) or separate sync/async
* [ ] Persist collaboration/tool/optimization/context/sandbox repositories (avoid loss on restart)
* [ ] Persist learning stats/experiments (avoid partial loss)
* [ ] Remove or archive chat_repository file-based if not used
* [ ] Define consistency strategy between SQL, Qdrant, and Neo4j (without UoW)
* [ ] Add retries/timeouts and confirmation in cross-store deletions
* [ ] Type return of Memory/Knowledge repos and standardize errors at repo level
* [ ] Finalize Alembic and ensure migrations for new models (e.g., ModelDeployment)
* [ ] Remove db.create_tables from boot in production

### Batch 5 - Agents, Tools, and Sandbox (IN PROGRESS)

**Objective**: map agent orchestration, tool-calls, and sandbox, highlighting policy, execution, and isolation failures.

#### Tasks

* [ ] Apply PolicyEngine, rate limit, and confirmation in all chat tool-calls
* [ ] Ensure action_registry.record_call in tool-calls flow (complete telemetry)
* [ ] Fix ChatAgentLoop fallback (execute_tool_calls does not accept strict)
* [ ] Add timeout and concurrency limit per tool in ToolExecutorService
* [ ] Fix missing awaits in core/autonomy/planner.py (draft/critique/refine/replan/verify)
* [ ] Cover planner/autonomy with regression test (coroutine/await)
* [ ] Unify sandbox and integrate Docker executor into services flow
* [ ] Align SandboxService.get_capabilities with real enforcement (timeout/CPU/mem/output)
* [ ] Persist rate limit and stats per user/tenant (Redis/DB) and standardize HITL flow

### Next step after Batch 5
- Batch 6: TBD (define scope).
