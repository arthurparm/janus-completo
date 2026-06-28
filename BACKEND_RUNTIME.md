# Backend Runtime

## 1. Kernel Lifecycle

The Kernel ([kernel.py](file:///h:/repos/janus-completo/backend/app/core/kernel.py)) is the central dependency container and lifecycle manager. It initializes the entire system in 8 sequential phases, each controllable via boolean flags for testing and selective startup.

**Phase 1 - Infrastructure (Critical)**: Initializes Neo4j via `_init_infrastructure()`, which calls `initialize_graph_db()`, `initialize_memory_db()` (Qdrant), and `initialize_broker()` (RabbitMQ). Each component has offline fallback: if Neo4j is unreachable, `GraphDatabase._offline` is set to True and the system continues without the graph. The MessageBroker attempts the configured host first, then falls back to localhost, and finally proceeds in silent-drop mode if both fail.

**Phase 2 - MAS Actors (Critical)**: Initializes the Multi-Agent System via `_init_mas_actors()`. Creates 4 specialized agents by default: PROJECT_MANAGER, CODER, RESEARCHER, and SYSADMIN. Each agent is wrapped in an `AgentActor` that starts a RabbitMQ consumer for its dedicated queue. Controlled by `INIT_MAS_AGENTS_ON_STARTUP` setting (defaults to false in production due to resource overhead).

**Phase 3 - Dependency Graph (Critical)**: `_build_dependency_graph()` wires the entire object graph. Instantiates 15+ repositories (Knowledge, Memory, Agent, Task, Context, Sandbox, Reflexion, Tool, Collaboration, LLM, Chat, Optimization, Observability, Prompt, Outbox, DocumentManifest), then creates 15+ services (Agent, Memory, Knowledge, Task, Context, Sandbox, Reflexion, Tool, Collaboration, Document, Observability, LLM, Prompt, Optimization, Outbox, Autonomy, Chat). Optionally sets global facades (`set_global_facades=True`) for InferenceFacade and KnowledgeFacade.

**Phase 4 - OS Tools**: Registers operating system tools via `register_os_tools()` and UI tools via `register_ui_tools()`. Makes tools available in the global `action_registry`.

**Phase 5 - Workers and Scheduler**: Starts background workers: knowledge consolidator, data harvester, life cycle worker, outbox service. Initializes neural training worker and document ingestion worker as asyncio tasks. Starts the APScheduler with default jobs (retention, maintenance).

**Phase 6 - Auto-Index**: Creates an asyncio task for `_run_auto_index()` to perform self-healing index operations on the knowledge graph. Controlled by `AUTO_INDEX_ON_STARTUP`.

**Phase 7 - LLM Warm-up**: Creates an asyncio task for `_warm_up_llms_async()` to pre-warm configured LLM providers, reducing cold-start latency for user requests.

**Phase 8 - Senses**: Initializes `VoiceManager` for audio capabilities. Non-critical; failures are logged but do not block startup.

**Graceful Shutdown**: The `shutdown()` method stops workers in reverse order: stops all workers, cancels training/consolidation/ingestion tasks, stops monitoring, stops scheduler, shuts down SQLAlchemy engines, then closes Neo4j, Qdrant, and RabbitMQ connections concurrently via `asyncio.gather()`.

## 2. Hybrid Brain / LLM Router

The LLM Router ([router.py](file:///h:/repos/janus-completo/backend/app/core/llm/router.py), 830 lines) implements an adaptive model selection system supporting 5+ providers.

**Providers**: Ollama (local), OpenAI (GPT-4-mini), Google Gemini (Gemini Pro), DeepSeek (DeepSeek Chat), xAI (Grok). Each provider has enable/disable flags, API key validation, and health checks. The cloud catalog lists all available models with their pricing, latency stats, and enabled status.

**Selection Algorithm**: `ModelRanker.rank()` scores candidates using a weighted formula. For `FAST_AND_CHEAP` priority: score = w_cost * cost_norm + w_lat * lat_norm + w_fail * failure_penalty. Weights depend on `LLM_ECONOMY_POLICY` (strict: 0.75/0.20/0.05, quality: 0.45/0.35/0.20, balanced: 0.60/0.30/0.10). For `HIGH_QUALITY` priority: score = success_rate - 0.3 * lat_norm - alpha * cost_norm. Candidates are sorted ascending for FAST_AND_CHEAP (lowest score wins) and descending for HIGH_QUALITY (highest score wins).

**Epsilon-Greedy Exploration**: Configured via `LLM_EXPLORATION_PERCENT` (default 0.10). In 10% of requests, a random non-top candidate is selected instead of the top-ranked one. This provides continuous exploration of alternative models to gather performance data.

**Budget Guardrails**: `_apply_budget_guardrail()` checks `is_total_budget_threshold_exceeded()` before each selection. If the total budget threshold is exceeded, all non-LOCAL_ONLY requests are forcibly downgraded to LOCAL_ONLY regardless of priority. This prevents cost overruns.

**Circuit Breakers**: Each provider has a dedicated circuit breaker (`_circuit_closed()` check). Failure threshold = 3, recovery timeout = 30s, half-open max calls = 5, half-open success threshold = 3. When a provider circuit is OPEN, that provider is excluded from candidate selection.

**Rate Limiting**: The `ModelUsageTracker` ([rate_limiter.py](file:///h:/repos/janus-completo/backend/app/core/llm/rate_limiter.py)) tracks TPM (tokens per minute), RPM (requests per minute), TPD (tokens per day), and RPD (requests per day) per model. Supports Firebase sync for distributed rate limit state. Models at >80% usage are marked unavailable.

**Pricing**: `_expected_k_ema_by_role` uses EMA-smoothed token estimates per role (orchestrator: 2K, code_generator: 3K, knowledge_curator: 1.5K). Combined with `_model_penalty_factors` for provider-specific adjustments.

## 3. Multi-Agent System (MAS)

The MAS ([multi_agent_system.py](file:///h:/repos/janus-completo/backend/app/core/agents/multi_agent_system.py)) implements a Society of Minds pattern with 7 specialized agent roles defined in [structures.py](file:///h:/repos/janus-completo/backend/app/core/agents/structures.py).

**Agent Roles**: PROJECT_MANAGER (general coordinator), RESEARCHER (research and analysis), CODER (code generation), TESTER (testing and validation), DOCUMENTER (documentation), OPTIMIZER (optimization and refactoring), SYSADMIN (system administration with OS Agency).

**Actor Model**: Each agent is wrapped in an `AgentActor` ([agent_actor.py](file:///h:/repos/janus-completo/backend/app/core/agents/agent_actor.py)) that owns a dedicated RabbitMQ queue (`janus.agent.{role}`). Actors receive task messages from their queue, execute them via the agent's `execute_task()` method, and publish results to the shared results queue (`janus.agent.results`). Communication is fully asynchronous and message-passing based.

**Shared Workspace**: `SharedWorkspace` ([workspace.py](file:///h:/repos/janus-completo/backend/app/core/agents/workspace.py)) provides a shared context for all agents. Tasks have dependencies, status tracking (PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED), and priority (LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4).

**Dependency Graph Resolution**: The `resolve_dependencies()` method computes a topological ordering of tasks. Tasks with unmet dependencies are marked as BLOCKED. The scheduler dispatches tasks in dependency order, ensuring that prerequisites complete before dependent tasks begin.

**Agent Manager**: `AgentManager` ([agent_manager.py](file:///h:/repos/janus-completo/backend/app/core/agents/agent_manager.py)) maps infrastructure `AgentType` enums to MAS `AgentRole` enums and provides a unified interface for running agents via API requests. It creates agents on demand with fresh LLM instances for context isolation.

## 4. RAG / Knowledge System

The RAG system implements multi-source fusion across five knowledge stores: episodic memory (conversation history), preferences (user settings), procedural memory (system prompts and instructions), secrets (encrypted credentials), and documents (uploaded files).

**Route-Based RAG**: The `RAGService` ([rag_service.py](file:///h:/repos/janus-completo/backend/app/services/rag_service.py)) makes routing decisions based on query type. Code queries are routed to the Neo4j codebase AST index. Document queries go to Qdrant document collections. General knowledge queries use the full multi-source pipeline.

**Multi-Source Fusion**: Results from all active sources are combined with semantic reranking. Each source contributes a relevance score, and the final ranking uses a weighted combination of vector similarity, recency, and source authority.

**Codebase AST Indexing**: Python source files are parsed into AST nodes and stored in Neo4j as typed entities (classes, functions, imports, calls) with relationships (DEFINES, CALLS, IMPORTS, INHERITS_FROM). JavaScript/TypeScript files use regex-based extraction. Each entity has an embedding vector (1536-dim, cosine similarity) for hybrid search.

**Consolidation Pipeline**: The async consolidation worker ([async_consolidation_worker.py](file:///h:/repos/janus-completo/backend/app/core/workers/async_consolidation_worker.py)) consumes knowledge consolidation tasks from RabbitMQ. It processes batch and single-mode consolidations, extracting entities and relationships from experience content and persisting them to Neo4j with quarantine validation.

## 5. Neo4j Graph Database

The GraphDatabase ([graph.py](file:///h:/repos/janus-completo/backend/app/db/graph.py)) manages the Neo4j connection with singleton driver, offline degradation, and ontology initialization.

**Relationship Types**: 30+ types defined in `GraphRelationship` enum ([schemas.py](file:///h:/repos/janus-completo/backend/app/models/schemas.py)) including structural (CONTAINS, CALLS, IMPORTS, DEFINES, INHERITS_FROM, IMPLEMENTS), action-based (USES, CREATES, RETURNS), causal (CAUSES, SOLVES, CAUSED_BY, SOLVED_BY), semantic (IS_A, PART_OF, DEPENDS_ON, RELATES_TO, SIMILAR_TO), and agentic (HAS_GOAL, HAS_PREFERENCE, EXECUTES, TRUSTS, BLOCKED_BY, COMPLETED_BY, CREATED_BY, MODIFIED_BY).

**Indexes**: 20+ indexes including vector indexes (1536-dim cosine for Concept, Entity, and other labels), fulltext indexes (for Entity.name, Concept.name), and btree indexes (for entity_id, timestamp, source). Vector indexes use Neo4j 5.11+ `db.index.vector.queryNodes` syntax.

**Ontology**: The `GraphGuardian` ([graph_guardian.py](file:///h:/repos/janus-completo/backend/app/core/memory/graph_guardian.py)) normalizes entity types (classes, functions, errors, concepts) and relationship types before persistence. Prevents explosion of unknown relationship types. The `semantic_relation_matcher.py` dynamically matches relation types using both the enum and semantic similarity.

**Offline Degradation**: If Neo4j is unreachable during `connect()`, `_offline` is set to True. All subsequent graph operations check this flag and return empty results gracefully. The system remains fully functional for chat operations using Qdrant-only memory.

## 6. Message Broker + Workers

The MessageBroker ([message_broker.py](file:///h:/repos/janus-completo/backend/app/core/infrastructure/message_broker.py), 984 lines) wraps RabbitMQ with connection pooling, automatic reconnection, and offline fallback.

**DLX/DLQ**: System-wide dead letter exchange (`janus.dlx`, fanout) and dead letter queue (`janus.dlq`, durable) are declared idempotently on startup. Failed messages (processing errors) are NACKed with `requeue=False`, sending them to the DLX. This prevents poison pill infinite loops while preserving messages for debugging and replay.

**Serialization**: Uses msgpack by default for compact binary serialization. Falls back to JSON for compatibility. Message headers carry trace context (trace_id, user_id) for distributed tracing.

**Worker Infrastructure**: 25+ background workers including: agent_tasks_worker (per-agent task execution), async_consolidation_worker (knowledge graph consolidation), data_harvester (external data collection), document_ingestion_worker (file processing), life_cycle_worker (scheduled maintenance), neural_training_worker (model fine-tuning).

**Queue Policy Reconciliation**: `reconcile_queue_policy()` validates queue arguments against expected configuration. If mismatches are found and `force_delete=True`, the queue is deleted and recreated with correct arguments. This ensures consistent queue topology across restarts.

**Trace Context Propagation**: Each published message receives trace headers (trace_id, parent_span_id). Consumers extract and restore trace context before processing, ensuring end-to-end trace continuity across service boundaries.

## 7. Memory System

The MemoryCore ([memory_core.py](file:///h:/repos/janus-completo/backend/app/core/memory/memory_core.py), 764 lines) implements the Generative Agents memory model (Park et al. 2023).

**Recency/Importance/Relevance Scoring**: `GenerativeMemoryService` ([generative_memory.py](file:///h:/repos/janus-completo/backend/app/core/memory/generative_memory.py)) combines three weighted scores: recency (exponential decay with 0.995 decay factor per hour), importance (LLM-scored on a 1-10 scale), and relevance (cosine similarity to query). Default weights are alpha=1.0, beta=1.0, gamma=1.0.

**Qdrant Vector Store**: Primary storage for memory vectors (1536-dim). Uses `AsyncQdrantClient` with configurable timeouts (search: 30s, connection: 10s, read: 25s, write: 25s). Circuit breaker wraps all Qdrant operations with half-open recovery.

**PII Redaction**: `redact_pii()` ([security.py](file:///h:/repos/janus-completo/backend/app/core/memory/security.py)) identifies and redacts CPF, CNPJ, RG, phone numbers, email addresses, credit card numbers, and IP addresses using regex patterns. Redaction happens before embedding generation to prevent PII from appearing in vector indices.

**Encryption**: `encrypt_text()`/`decrypt_text()` uses Fernet symmetric encryption with a rotating keyring. Each encrypted payload carries metadata (encryption method, key ID). The `SecretKeyRotationService` supports gradual re-encryption without downtime.

**Quota Enforcement**: Per-origin quotas track items and bytes within sliding windows. Default: 200 items/5MB per origin per hour. Self-study origins have higher limits (5000 items/25MB). `SmartEviction` policies protect persistent/strong memories and prefer rolling_window retention. Protected items (retention=persistent, stability_score >= threshold, or strong_memory flag) are exempt from eviction.

## 8. Evolution / Lab

The Evolution module ([core/evolution/](file:///h:/repos/janus-completo/backend/app/core/evolution/)) provides autonomous self-improvement capabilities.

**SelfStudyManager**: Orchestrates the full self-study cycle: (1) Reflection via `ReflectorAgent` analyzing past experiences for failure patterns, (2) Prioritization ranking improvements by impact, (3) Evolution creating/improving tools via `EvolutionManager`, (4) Validation verifying improvements work. The cycle runs during idle time when system health score drops below 0.8. Limited to 3 evolutions per session by default.

**EvolutionManager**: Manages the evolution backlog as a JSON file (`data/evolution_backlog.json`). The `queue_request()` method adds improvement requests. `process_next_pending()` cycles through spec generation (via LLM `TOOL_SPECIFICATION_PROMPT`), tool code generation (via `TOOL_GENERATION_PROMPT`), AST validation, and tool registration in the `action_registry`.

**ReflectorAgent**: Analyzes past experiences from memory looking for failure keywords (error, failed, timeout, exception, tool not found), user dissatisfaction signals (wrong, incorrect, try again), and missing capabilities. Produces a `ReflectionReport` with `health_score` (0-1), detected `FailurePattern` instances, and suggested improvements.

**SafeEvolutionManager + JanusLab**: The complete Dream Mode flow: (1) `LogAwareReflector` reads actual application logs, (2) identifies error patterns, (3) generates improvement code, (4) spawns a JanusLab Docker container with `janus-api:latest` image, restricted environment (`DISABLE_WORKERS=true`, `DISABLE_MEMORY_WRITES=true`, `ENVIRONMENT=lab`), no-network mode, (5) tests the code in the Lab, (6) if passes, applies to Prime, (7) auto-destroys Lab after 600s. Limited to 2 attempts per session.

## 9. Security Architecture

**Secret Validator** ([secret_validator.py](file:///h:/repos/janus-completo/backend/app/core/security/secret_validator.py)): Defines `INSECURE_DEFAULTS` mapping for Neo4j_PASSWORD, POSTGRES_PASSWORD, RABBITMQ_PASSWORD, and AUTH_JWT_SECRET. Runs during `lifespan` startup in production mode. Blocks boot with `InsecureConfigurationError` if any secret equals an insecure default. Uses Pydantic `SecretStr` to prevent value leakage in logs.

**Egress Policy** ([egress_policy.py](file:///h:/repos/janus-completo/backend/app/core/security/egress_policy.py)): `enforce_tool_http_egress()` implements deny-by-default for tool HTTP requests. `enforce_worker_http_egress()` applies an allowlist for worker-initiated connections. `resolve_safe_http_target()` ([url_safety.py](file:///h:/repos/janus-completo/backend/app/core/security/url_safety.py)) performs DNS resolution, IP classification (blocks private/loopback/link-local), and SSRF mitigation. For HTTP, the fetch URL uses the resolved IP to prevent DNS rebinding. For HTTPS, the hostname is preserved for TLS/SNI but the resolved IP is logged.

**Request Guards** ([request_guard.py](file:///h:/repos/janus-completo/backend/app/core/security/request_guard.py)): `require_authenticated_actor_id()` ensures a valid session. `require_admin_actor()` restricts to admin users. `require_same_user()` enforces resource ownership. All guards extract actor info from JWT claims.

**Rate Limiting**: Auth rate limiting ([auth_rate_limiter.py](file:///h:/repos/janus-completo/backend/app/core/security/auth_rate_limiter.py)) uses in-memory sliding windows per IP+identifier. Defaults: 10 req/60s login, 5 req/60s reset. LLM rate limiting ([rate_limiter.py](file:///h:/repos/janus-completo/backend/app/core/llm/rate_limiter.py)) uses multi-window tracking (TPM/RPM/TPD/RPD) with optional Firebase sync for distributed state. Both return 429 with Retry-After headers.

**Command Sandbox** ([command_sandbox.py](file:///h:/repos/janus-completo/backend/app/core/tools/command_sandbox.py)): Validates shell commands against an allowlist (allowed executables: echo, pwd, ls, cat, head, tail, wc, grep, find, python, pytest, git, date, whoami) and argv prefix patterns (e.g., git only allowed with specific subcommands like status, diff, log). Blocks shell operators (&&, ||, ;, |, >, <, `, $(), multiline commands, max 600 chars).

## 10. Observability

**SLO Per Domain**: `ObservabilityService.get_domain_slo_report()` ([observability_service.py](file:///h:/repos/janus-completo/backend/app/services/observability_service.py)) computes SLOs for 4 domains: chat (max 5% error rate, max 3.5s p95 latency), rag (5%, 4.5s), tools (3%, 2.5s), workers (3%, 4.0s). Each domain report includes error rate, availability %, p95 latency, and breach status with active alerts.

**Health Checks**: Per-component health checks registered in `HealthMonitor`: Neo4j, Qdrant, RabbitMQ, Postgres, Redis, LLM Router, Multi-Agent System. Each returns status (healthy/unhealthy/degraded) with details. Critical checks (background_workers) can degrade the overall system health status.

**Predictive Anomaly Detection**: `PredictiveAnomalyDetectionService` monitors metric trends and predicts potential SLO breaches before they occur. Uses statistical baseline comparison with configurable sensitivity.

**Prometheus Metrics**: Comprehensive metrics exported via `/metrics` endpoint: `LLM_ROUTER_COUNTER` (model selections per role/provider), `LLM_SELECTION_SCORE` (adaptive selection score), `LLM_EXPECTED_COST_USD` (estimated cost per request), `memory_operations_total`, `memory_quota_rejections_total`, `rate_limit_fallback_total`, and operation-level success/error/duration instruments.

**OpenTelemetry Tracing**: `_tracer` is initialized from `opentelemetry.trace` when available. Each observability service operation starts an OTEL span with attributes (operation name, window parameters, latency). Spans propagate to configured OTEL collectors.

**Immutable Audit Ledger**: `ObservabilityRepository` writes immutable audit events for all tool executions, auth operations, LLM calls, and system actions. Events include timestamp, actor_id, operation, status, and metadata. Retention policies purge events older than configurable days.

## 11. Tool Executor & Sandbox

The ToolExecutorService ([tool_executor_service.py](file:///h:/repos/janus-completo/backend/app/services/tool_executor_service.py), 671 lines) handles tool lifecycle from request to execution.

**JSON Envelope Protocol**: Tool calls arrive as structured JSON with tool name, arguments, and metadata. The executor validates the envelope, resolves the tool from `action_registry`, validates arguments against schema, and returns structured results.

**PolicyEngine ([policy_engine.py](file:///h:/repos/janus-completo/backend/app/core/autonomy/policy_engine.py))**: Multi-layer validation: (1) Content safety check for injection patterns (jailbreak, ignore instructions, unsafe mode), (2) Destructive operation detection with simulation confirmation, (3) Quota enforcement (max actions per cycle=20, max seconds=60), (4) Command allowlist/blocklist for restricted tools with argv prefix matching, (5) Risk profile selection (conservative/balanced/aggressive) controlling auto-confirm behavior.

**Docker Sandbox** ([sandbox_executor.py](file:///h:/repos/janus-completo/backend/app/core/tools/sandbox_executor.py)): Executes Python code in isolated Docker containers with configurable resource limits (memory: configurable, CPU: 1.0 cores). Uses `execute_python_code` tool registered as SAFE permission level. The sandbox restricts imports (no os, subprocess, sys) and blocks filesystem/network access.

**Command Sandbox** ([command_sandbox.py](file:///h:/repos/janus-completo/backend/app/core/tools/command_sandbox.py)): For OS-level commands, validates against a strict allowlist of executables and argv prefixes. Shell operators (&&, ||, ;, pipe, redirect) are blocked. Max command length is 600 characters. Multiline commands are rejected.
