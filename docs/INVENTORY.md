# System Inventory & Surveys

This document contains detailed surveys of the system components, APIs, and current status of various modules, originally conducted to map the state of the Janus V1 architecture.

## 📎 Detailed Surveys

### ✅ Batch 1 — Boot & Kernel (CLOSED)

**Scope Covered**: Application lifecycle (lifespan), Kernel initialization, critical infrastructure, manual DI, warm-up, auto-indexing, workers, and shutdown.

**Completed Deliverables**:

1.  **Startup Flow Map (Textual Pipeline & Criticality)**
    *   FastAPI Lifespan initializes the Kernel and maps services in `app.state` with backward compatibility.
    *   Kernel executes: Infrastructure → MAS Agents → DI → OS Tools → Workers → Auto-index → Warm-up → Senses.
    *   Critical steps (failures interrupt boot): Infrastructure and MAS Agents.
    *   Best-effort steps: Workers, warm-up, voice.

2.  **Infrastructure Inventory & Operational Impact**
    *   Parallel initialization: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
    *   Firebase is optional and does not block boot (non-critical failure).

3.  **Coupling Analysis (Manual DI)**
    *   Kernel concentrates repository and service creation, increasing coupling and hindering isolated testing.
    *   Injection flow is "eager" rather than lazy, increasing startup cost.

4.  **Workers & Scheduler**
    *   Workers start globally (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
    *   No global flags to disable per environment, increasing dev/CI costs.

5.  **Warm-up & Auto-indexing**
    *   `AUTO_INDEX_ON_STARTUP=True` can cause high costs on large databases.
    *   LLM warm-up in background is asynchronous but still consumes resources at boot.

**Technical Recommendations (Focus on Cost & Performance)**

*   [ ] Parallelize prompt loading (reduce cold start latency).
*   [ ] Incremental indexing based on hash/commit (avoid unnecessary O(N)).
*   [ ] Create feature flags for workers per environment (reduce operational cost).
*   [ ] Introduce lightweight DI container (reduce coupling and improve testability).

---

### 🔍 Batch 2 — API & Endpoints (CLOSED)

**Objective**: Map contracts, endpoints, validations, and performance impacts of the HTTP layer (FastAPI), including route governance and security.

#### Results (Heartbeat Rigor)

1.  **Full V1 Route Inventory**
    *   Total (Full API): 212 unique routes; 65 with Pydantic request models; 2 with File/Form upload.
    *   Routes defined but not exposed in v1 router: `admin_graph`, `meta`, `resources`.
    *   Real duplications (same method/path): `/optimization/*` and `/productivity/*` (detailed below).
    *   `PUBLIC_API_MINIMAL` mode exposed: `/chat`, `/users`, `/profiles`, `/autonomy`, `/assistant`, `/autonomy/history`, `/consents`, `/pending_actions`, `/evaluation`, `/deployment`, `/auth`, `/auto-analysis`, `/feedback`.

#### Full Route Inventory (Full API)
*Note: Listed paths already include the `/api/v1` prefix.*

*(Refer to the original documentation or code for the full 200+ route table if needed. Key findings summarized below.)*

**Key Route Groups:**
*   `/admin`: Configuration updates.
*   `/agent`, `/assistant`: Execution endpoints.
*   `/auth`: Supabase exchange, token issuance.
*   `/autonomy`: Goals, plans, history, status.
*   `/chat`: Conversations, messages, streams, history.
*   `/collaboration`: Agents, tasks, workspace artifacts.
*   `/consents`: Consent management.
*   `/context`: Context retrieval, web search.
*   `/deployment`: Publish, rollback, stage.
*   `/documents`: Link URL, upload, search, status.
*   `/evaluation`: AB experiments.
*   `/feedback`: User feedback, satisfaction reports.
*   `/knowledge`: Graph queries, consolidation, reindexing.
*   `/learning`: Models, training, harvesting.
*   `/llm`: Invocation, cache, circuit breakers, pricing.
*   `/memory`: Generative memories, timeline.
*   `/meta-agent`: Analysis, heartbeat.
*   `/observability`: Health checks, metrics, poison pills.
*   `/optimization`: System analysis (Duplicated).
*   `/pending_actions`: Approval/rejection.
*   `/productivity`: Calendar, mail, notes (Duplicated).
*   `/profiles`: User profiles.
*   `/rag`: Hybrid search, user chat search.
*   `/reflexion`: Reflexion config and execution.
*   `/sandbox`: Code execution, expression evaluation.
*   `/system`: DB migration, health, overview.
*   `/tasks`: Queues, consolidation tasks.
*   `/tools`: Tool management, creation from API/Function.
*   `/users`: User management, roles.
*   `/workers`: Start/stop workers.

2.  **Contracts & Validations (Pydantic)**
    *   `models/schemas.py` used only in memory and tasks; others define local DTOs.
    *   Free/sensitive inputs without clear limits:
        *   `/llm/invoke`, `/chat/message`, `/assistant/execute`: No `max_length` on prompt/message (cost/abuse risk).
        *   `/tools/create/from-function`: Code without limit/syntax validation.
        *   `/sandbox/execute`: Arbitrary code (requires hard gate).
        *   `/documents/upload`: Limited size, but no MIME/extension whitelist or scan.
        *   `/rag/*`: Free query; lacks sanitization and per-user limits.
    *   Positive: Autonomy validates plan steps and `AgentExecutionRequest` has `max_length`.

3.  **HTTP Performance & Middlewares**
    *   Global Middlewares: `SecurityHeadersMiddleware`, `CorrelationMiddleware`, `RateLimitMiddleware`, CORS, msgpack negotiation, Prometheus instrumentator.
    *   RateLimit: Token-bucket in Redis, fail-open if Redis down; bypass for `/metrics`, `/healthz`.
    *   Msgpack negotiation does JSON decode/encode when `Accept=application/msgpack`; extra cost on large responses.
    *   `/system/overview` makes sequential calls; could be parallelized.

4.  **Governance & Versioning**
    *   Routes outside `/api/v1`: `/`, `/health`, `/healthz`, `/metrics`, `/static`.
    *   Endpoints with code but unregistered: `admin_graph`, `meta`, `resources`.
    *   Duplication of `include_router` in `/optimization` and `/productivity`.
    *   Inconsistent naming: `/rag/user-chat` vs `/rag/user_chat`.

5.  **API Security (Keys & Headers)**
    *   `X-API-Key` is optional; API exposed if absent.
    *   `actor_user_id` accepts `X-User-Id` without verification (impersonation risk).
    *   Critical endpoints without auth/admin: `/system/db/*`, `/workers/*`, `/sandbox/execute`, etc.
    *   Recommendation: Separate admin routes, require JWT/role, remove `X-User-Id` fallback.

6.  **LLM Endpoint Cost Checklist**
    *   Core LLM has budgets, but `user_id` comes from payload; needs identity authentication.
    *   RateLimit is by IP/Key, not cost/tenant.

#### Tasks (Inventory Derived)
*See Roadmap for actionable items derived from this inventory.*

---

### Batch 3 — Services (LLM, Chat, RAG, Observability, Autonomy) (IN PROGRESS)

**Objective**: Map the service layer and explicit critical pending items in the Janus core flow.

#### Tasks
*   [ ] Enforce size limits in `LLMService` (prompt + output).
*   [ ] Enforce size limits in `ChatService` (message + attachments).
*   [ ] Standardize cost tracking/estimation in Chat → LLM path.
*   [ ] Validate conversation ownership in service and SQL repository.
*   [ ] Make `user_id`/`project_id` mandatory and server-side before RAG/LLM.
*   [ ] Persist `ChatEventPublisher` events (avoid silent `db_logger=None`).
*   [ ] Expose degradation telemetry in RAG and summarization (explicit failure).
*   [ ] Implement backoff, limits, and cancellation in `AutonomyLoop`.
*   [ ] Unify repository interfaces used by `ChatService` and `RAGService`.
*   [ ] Centralize identity resolution before calling LLM/RAG/Autonomy.

---

### Batch 4 — Repositories & Persistence (IN PROGRESS)

**Objective**: Map repositories, data sources, and persistence contracts, highlighting inconsistencies and technical debt.

#### Tasks
*   [ ] Standardize Postgres session (100% async or dedicated sync engine).
*   [ ] Fix `db.get_session_direct` calls (non-existent method) in repositories.
*   [ ] Align `ChatRepositorySQL` with DB infra (avoid incompatible sync Session).
*   [ ] Rewrite `PromptRepository` for coherent flow (async) or separate sync/async.
*   [ ] Persist collaboration/tool/optimization/context/sandbox repositories (avoid data loss on restart).
*   [ ] Persist learning stats/experiments.
*   [ ] Remove or archive file-based `chat_repository` if unused.
*   [ ] Define consistency strategy between SQL, Qdrant, and Neo4j (no UoW).
*   [ ] Add retries/timeouts and confirmation for cross-store deletions.
*   [ ] Type returns of Memory/Knowledge repos and standardize errors.
*   [ ] Finalize Alembic and ensure migrations for new models.
*   [ ] Remove `db.create_tables` from boot in production.

---

### Batch 5 — Agents, Tools & Sandbox (IN PROGRESS)

**Objective**: Map agent orchestration, tool-calls, and sandbox, highlighting policy, execution, and isolation failures.

#### Tasks
*   [ ] Apply PolicyEngine, rate limit, and confirmation on all chat tool-calls.
*   [ ] Ensure `action_registry.record_call` in tool-calls flow (full telemetry).
*   [ ] Fix `ChatAgentLoop` fallback (`execute_tool_calls` does not accept strict).
*   [ ] Add timeout and concurrency limit per tool in `ToolExecutorService`.
*   [ ] Fix missing awaits in `core/autonomy/planner.py` (draft/critique/refine/replan/verify).
*   [ ] Cover planner/autonomy with regression tests.
*   [ ] Unify sandbox and integrate Docker executor into service flow.
*   [ ] Align `SandboxService.get_capabilities` with real enforcement.
*   [ ] Persist rate limit and stats per user/tenant.

### Next Steps
- Batch 6: TBD (Define scope).
