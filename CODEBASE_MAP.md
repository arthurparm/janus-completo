# Codebase Map

## Directory Structure Overview

```
h:\repos\janus-completo\
├── backend/                    # FastAPI + Python 3.11+
│   ├── app/
│   │   ├── main.py            # FastAPI app entry, lifespan events
│   │   ├── config.py          # Pydantic Settings (978 lines, all env config)
│   │   ├── api/v1/            # Router + endpoints (chat, auth, knowledge, tools, admin, observability)
│   │   ├── core/              # Kernel, LLM, agents, memory, tools, security, evolution, workers, monitoring
│   │   ├── services/          # Business logic layer (orchestration)
│   │   ├── repositories/      # Data access layer (SQL, Neo4j, Qdrant, broker)
│   │   ├── models/            # Pydantic/SQLAlchemy models + schemas
│   │   ├── db/                # Database engines (graph.py, vector_store.py, db.py)
│   │   ├── prompts/           # LangChain prompt templates (agent roles, cypher, evolution)
│   │   └── planes/            # Domain planes (inference, knowledge)
│   ├── tests/                 # Unit, integration, e2e
│   ├── docker/Dockerfile      # Multi-stage build (final + test target)
│   └── scripts/               # Utility scripts (eval, sanitize, maintenance)
│
├── frontend/                  # Angular 20 standalone
│   ├── src/app/
│   │   ├── core/              # Auth, guards, interceptors, layout, notifications, services
│   │   ├── features/          # Conversations, observability, tools, admin, home, auth
│   │   ├── services/          # API integration (chat-stream, backend-api, domain services)
│   │   ├── shared/            # Reusable components (ui, loading, skeleton, icons)
│   │   └── models/            # TypeScript interfaces matching backend DTOs
│   ├── angular.json           # esbuild builder, @angular/build:application
│   └── package.json           # Angular 20, RxJS 7, TailwindCSS 3, Cytoscape, Chart.js
│
├── qa/                        # Pytest contract tests (58+ tests covering critical paths)
│   ├── test_api_visibility_endpoints.py
│   ├── test_tool_executor_policy_guards.py
│   ├── test_chat_agent_loop_content_safety.py
│   ├── test_memory_quota_enforcement.py
│   ├── test_generative_memory_llm_role_priority.py
│   ├── test_chat_endpoint_contract.py
│   ├── test_observability_request_dashboard.py
│   ├── test_db_migration_service_contract.py
│   └── test_knowledge_code_query_contract.py
│
├── tooling/                   # Python and PowerShell canonical workflows
│   ├── dev.py                 # Main orchestrator (up/down/qa/doctor/setup)
│   ├── extract_api_inventory.py
│   ├── generate_api_matrix.py
│   ├── generate_api_coverage_report.py
│   ├── async_ops_validation.py
│   └── *.ps1                  # Windows PowerShell helpers
│
├── documentation/             # Architecture, deployment, QA, development guides
├── docker-compose.pc1.yml     # Stateless services (API, frontend, postgres, redis, rabbitmq)
├── docker-compose.pc2.yml     # Stateful services (neo4j, qdrant, ollama)
└── outputs/qa/                # Generated QA reports (do not remove, consumed by diagnostics)
```

## Data Flow Diagrams

### Request Flow (Backend)

```
HTTP Request
    │
    ▼
FastAPI Router (api/v1/router.py)
    │
    ▼
Endpoint (api/v1/endpoints/*.py)
    │
    ▼
Service Layer (services/*.py)         ← Business logic orchestration
    │
    ├──► Repository Layer (repositories/*.py)    ← Data access
    │       ├──► Neo4j (db/graph.py)             ← Knowledge graph
    │       ├──► Qdrant (core/memory/)            ← Vector store
    │       ├──► PostgreSQL (db/db.py)             ← Relational
    │       └──► RabbitMQ (core/infrastructure/)  ← Message broker
    │
    ├──► Core (core/*.py)                        ← Domain logic
    │       ├──► LLM Router (core/llm/router.py)  ← Model selection
    │       ├──► Memory Core (core/memory/)        ← Memory operations
    │       ├──► Tools (core/tools/)               ← Tool execution
    │       └──► Agents (core/agents/)             ← Multi-agent system
    │
    └──► Response ←─── HTTP Response
```

### SSE Chat Streaming Flow

```
Client (Angular)
    │  fetch() POST /v1/chat/stream/{conversation_id}
    ▼
ChatService (services/chat_service.py)
    │
    ▼
LLM Router → Model Selection → LLM Provider
    │
    ▼
SSE Events: start → cognitive_status → tool_status → token/partial → done/error
    │
    ▼
Client (Angular ChatStreamService)
    ├── status$ (connecting → open → streaming → done/error)
    ├── typing$ (boolean)
    ├── partials$ ({text: string})
    ├── done$ (conversation_id, provider, citations, understanding)
    ├── errors$ (error, code, retryable, attempt)
    ├── cognitive$ (state, confidence_band)
    └── toolStatus$ (tool events)
```

## Design Patterns

| Pattern | Location | Implementation |
|---|---|---|
| Singleton | [kernel.py](file:///h:/repos/janus-completo/backend/app/core/kernel.py) | `Kernel._instance` class variable, `get_instance()`/`reset_instance()` class methods. Also used in MessageBroker (broker connection), GraphDatabase (driver singleton). |
| Strategy | [llm/router.py](file:///h:/repos/janus-completo/backend/app/core/llm/router.py) | `ModelRanker.rank()` applies different scoring strategies based on `ModelPriority` (FAST_AND_CHEAP vs HIGH_QUALITY) and `LLM_ECONOMY_POLICY` (strict/balanced/quality). |
| Actor Model | [core/agents/multi_agent_system.py](file:///h:/repos/janus-completo/backend/app/core/agents/multi_agent_system.py) | Each `SpecializedAgent` is wrapped in an `AgentActor` that owns a RabbitMQ queue (`janus.agent.{role}`). Actors communicate via messages through the broker. 7 agent roles defined. |
| Circuit Breaker | [core/infrastructure/resilience.py](file:///h:/repos/janus-completo/backend/app/core/infrastructure/resilience.py) | Per-provider circuit breakers in LLM Router (failure_threshold=3, recovery_timeout=30s). Qdrant circuit breaker with half-open state (half_open_max_calls=5, half_open_success_threshold=3). |
| Factory | [core/llm/factory.py](file:///h:/repos/janus-completo/backend/app/core/llm/factory.py) | `LLMFactory` creates LLM instances per provider (Ollama, OpenAI, Gemini, DeepSeek, xAI) with pooling and caching. |
| Observer | [core/infrastructure/](file:///h:/repos/janus-completo/backend/app/core/infrastructure/) | Event system via RabbitMQ exchanges (`janus.events`). ChatEventPublisher publishes agent events. SSE streaming delivers events to Angular client. |
| Dependency Injection | [core/kernel.py](file:///h:/repos/janus-completo/backend/app/core/kernel.py) | `Kernel._build_dependency_graph()` wires all repositories and services together. `bootstrap_dependencies()` maps kernel attributes to `app.state` for FastAPI Depends injection. |
| Repository | [repositories/*.py](file:///h:/repos/janus-completo/backend/app/repositories/) | Each data source has a dedicated repository (KnowledgeRepository, MemoryRepository, TaskRepository, ToolRepository, etc.) encapsulating query logic. |
| Facade | [planes/*.py](file:///h:/repos/janus-completo/backend/app/planes/) | `InferenceFacade` and `KnowledgeFacade` provide simplified interfaces over multiple services. |

## Backend Navigation Map

| Domain | Entry Points | Key Files |
|---|---|---|
| Kernel/Startup | `main.py`, `core/kernel.py`, `core/bootstrap.py` | 8-phase startup, dependency graph, graceful shutdown |
| API Routing | `api/v1/router.py`, `api/v1/endpoints/*` | 229+ endpoints, PUBLIC_API_MINIMAL gate |
| LLM/Inference | `services/llm_service.py`, `core/llm/router.py`, `core/llm/factory.py` | 5+ providers, cost/latency ranking, circuit breakers |
| Multi-Agent | `core/agents/multi_agent_system.py`, `core/agents/agent_manager.py` | 7 roles, Actor Model, RabbitMQ queues |
| Knowledge/RAG | `services/knowledge*`, `services/rag_service.py`, `planes/knowledge/*` | Route-based RAG, multi-source fusion |
| Memory | `services/memory_service.py`, `core/memory/memory_core.py` | Generative Agents model, Qdrant, quotas, encryption |
| Autonomy | `services/autonomy*`, `core/evolution/*` | Self-study, evolution, lab testing |
| Tools/Sandbox | `services/tool_executor_service.py`, `core/tools/*` | PolicyEngine, Docker sandbox, command sandbox |
| Workers/Events | `core/workers/*`, `core/infrastructure/message_broker.py` | 25+ workers, DLX/DLQ, msgpack |
| Security | `core/security/*` | Secret validation, egress policy, rate limiting, auth |
| Observability | `services/observability_service.py`, `core/monitoring/*` | SLO per domain, Prometheus, OpenTelemetry, audit |

## Frontend Navigation Map

| Domain | Path | Key Files |
|---|---|---|
| Core | `core/auth/`, `core/guards/`, `core/interceptors/`, `core/layout/` | AuthService, 5 guards, interceptor chain, header |
| Features | `features/conversations/`, `features/observability/`, `features/tools/`, `features/admin/`, `features/home/` | Product screens |
| Services | `services/` | ChatStreamService (SSE), BackendApiService, domain services |
| Shared | `shared/components/` | UI components, skeleton, loading, icons |
| Models | `models/` | TypeScript interfaces aligned with backend API |

## Key Architectural Principles

1. **Layered Architecture**: endpoint -> service -> repository -> core/model. Endpoints must not accumulate business logic. Services orchestrate use cases. Repositories encapsulate persistence. Core contains runtime infrastructure and cross-cutting mechanisms.

2. **Offline Degradation**: Every external dependency (Neo4j, Qdrant, RabbitMQ, LLM providers) has a graceful degradation path. If a dependency is unavailable, the system logs warnings and proceeds with reduced functionality rather than crashing. Neo4j has `_offline` flag. RabbitMQ has silent-drop mode. LLM Router falls back to LOCAL_ONLY.

3. **Deny-by-Default Security**: Egress policy blocks all HTTP targets by default. Only explicitly allowlisted hosts are permitted. Tool execution has a PolicyEngine with content safety checks, destructive operation simulation, and command allowlist/blocklist. The secret validator prevents boot in production with insecure defaults.

4. **Observability as a First-Class Citizen**: Every service operation records metrics (Prometheus counters/histograms), traces (OpenTelemetry spans), and audit events. SLO thresholds are defined per domain (chat/rag/tools/workers) with automated breach detection and alerting.

5. **Idempotent and Recoverable**: Message broker consumers use poison pill protection (DLX/DLQ). Queue policies are reconciled on startup. Memory operations support key rotation and retention policies. Workers can restart without data loss.
