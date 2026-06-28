# Kernel Startup

## Startup States

The Kernel defines three operational states that determine the application's availability at startup.

### `healthy`

All critical and non-critical dependencies initialized successfully. The application operates at full capacity with all features enabled.

Criteria:

- All infrastructure services (PostgreSQL, Neo4j, Qdrant, RabbitMQ) initialized without errors
- Redis initialized or gracefully skipped (respects `REDIS_ENABLED` flag)
- LLM router registered and circuit breakers closed
- Dependency graph built without exceptions
- Background workers, monitoring, and scheduler started

### `degraded`

Some non-critical or recoverable-critical dependencies failed during initialization. The application starts but operates with reduced functionality. The Kernel records each failed dependency in `degraded_dependencies` and continues startup.

Criteria:

- At least one dependency recorded in `degraded_dependencies`
- No `KernelError` raised — the startup sequence completed
- The `_state` property returns `"degraded"`

### `critical`

A critical dependency failure prevented the application from starting. The Kernel raises `KernelError` and the application process exits or enters a crash-loop.

Criteria:

- `_init_infrastructure` raises an unhandled exception
- `_build_dependency_graph` fails (repositories or services cannot be constructed)
- `_init_mas_actors` raises `KernelError`
- The `_state` property returns `"critical"`

---

## Dependency Table

| Dependency | Type | Criticality | Fallback Behavior | Health Check | Recovery |
|---|---|---|---|---|---|
| PostgreSQL | `db` | critical | No fallback. If the database is unavailable the application cannot start. Table creation and schema migration are attempted before declaring failure. | `check_postgres()` — runs `SELECT 1` against the async engine | Restore the PostgreSQL container with `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d postgres`. Verify connection credentials in `.env.pc2`. |
| Neo4j | `graph_db` | critical | Offline mode. The KnowledgeRepository cannot operate without Neo4j. Services that depend on graph queries (knowledge, agents, collaboration) will fail at injection time. | `check_neo4j()` — runs `RETURN 1 AS ok` via session | Restore the Neo4j container with `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d neo4j`. Check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in environment. |
| Qdrant | `memory_db` | critical | Degraded mode. EpisodicMemory reads return empty results and write operations are queued or skipped. Chat and tools continue to work but without memory context. The circuit breaker opens after repeated failures. | `check_qdrant_health()` — verifies collection existence via `MemoryCore` client, attempts `_try_revive_connection` on transient failures | Restore the Qdrant container with `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant`. Check `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY` in environment. |
| RabbitMQ | `broker` | critical | Workers disabled. Background task processing, message passing, and async consolidation are unavailable. The application API and chat features remain functional. | `check_message_broker_health()` — calls `broker.health_check()` | Restore the RabbitMQ container with `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d rabbitmq`. Verify `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASS` in environment. |
| Redis | `redis_manager` | non-critical | Caching disabled. Rate limiting falls back to in-memory implementation. The application operates at full functionality minus caching and distributed rate limiting. Respected the `REDIS_ENABLED` config flag — if set to `False`, Redis is never initialized. | `check_redis()` — calls `RedisManager.get_instance().ping()` | Check `REDIS_ENABLED=True` in config. Restore the Redis container with `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d redis`. Verify `REDIS_HOST`, `REDIS_PORT` in environment. |
| LLM Providers | `llm_router` | critical | Fallback models. The `LLMService` maintains a pool of providers with circuit breakers. If the primary provider is down the router selects the next available provider. If all circuit breakers are open the health check reports unhealthy and inference requests fail. | `check_llm_router_health()` — inspects circuit breaker snapshot and pool summary | Check API keys (OpenAI, Groq, Ollama) in environment. Verify `LLM_POOL_WARM_PROVIDERS` config. Monitor open circuit breakers. |

---

## Degraded Mode Operation

When the Kernel starts in degraded state, specific dependencies are unavailable. The following table describes what works and what does not for each failed dependency.

| Failed Dependency | What Works | What Does Not Work |
|---|---|---|
| PostgreSQL | Static file serving, LLM inference (if LLM providers are healthy), tool execution | No data persistence. Authentication, chat history, user management, observability logging, and all SQL-backed operations fail. The application cannot serve API requests reliably. |
| Neo4j | LLM inference, chat (conversation-only), tool execution, file serving | Knowledge graph queries, agent management, collaboration, code indexing, reflexion, and all graph-backed operations fail. Dependency injection of `KnowledgeRepository` raises, cascading to dependent services. |
| Qdrant | Chat, tools, LLM inference, authentication | Episodic memory reads return empty. Memory write operations are skipped. RAG service cannot perform vector similarity search. Knowledge consolidation and document ingestion workers fail. |
| RabbitMQ | API endpoints, chat, LLM inference, authentication, tool execution | Background workers (consolidation, document ingestion, neural training) do not start. Outbox event processing is disabled. Scheduled jobs do not run. System operates in a reduced asynchronous-processing mode. |
| Redis | All application features | Distributed caching is disabled. Rate limiter falls back to in-memory (per-process) implementation. No performance impact beyond increased database load for uncached queries. |
| LLM Providers | API responses that do not require inference, static content | All LLM-dependent features fail: chat completion, agent reasoning, knowledge summarization, code analysis, autonomous goal generation. The application is effectively non-functional for AI tasks. |

---

## Recovery Procedures

### PostgreSQL

```bash
# 1. Verify the container is running
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps postgres

# 2. Inspect container logs
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs postgres

# 3. Restart the service
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 restart postgres

# 4. If the container is missing, recreate it
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d postgres

# 5. Verify connectivity
python -c "from app.db.postgres_config import postgres_db; import asyncio; print(asyncio.run(postgres_db.check_connection()))"
```

### Neo4j

```bash
# 1. Verify the container is running
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps neo4j

# 2. Inspect container logs
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs neo4j

# 3. Check configuration variables
echo "NEO4J_URI=$NEO4J_URI"
echo "NEO4J_USER=$NEO4J_USER"

# 4. Restart the service
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 restart neo4j

# 5. Verify connectivity via Cypher
python -c "from app.db.graph import get_graph_db; import asyncio; db = asyncio.run(get_graph_db()); print('Connected' if db else 'Failed')"
```

### Qdrant

```bash
# 1. Verify the container is running
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps qdrant

# 2. Inspect container logs
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs qdrant

# 3. Check configuration
echo "QDRANT_HOST=$QDRANT_HOST"
echo "QDRANT_PORT=$QDRANT_PORT"

# 4. Restart the service
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 restart qdrant

# 5. Verify via health check
curl -sf http://localhost:6333/health
```

### RabbitMQ

```bash
# 1. Verify the container is running
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps rabbitmq

# 2. Inspect container logs
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs rabbitmq

# 3. Check configuration
echo "RABBITMQ_HOST=$RABBITMQ_HOST"
echo "RABBITMQ_USER=$RABBITMQ_USER"

# 4. Restart the service
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 restart rabbitmq

# 5. Verify via management API
curl -sf -u "$RABBITMQ_USER:$RABBITMQ_PASS" http://localhost:15672/api/health/checks/alarms
```

### Redis

```bash
# 1. Verify Redis is enabled in config
echo "REDIS_ENABLED=$REDIS_ENABLED"

# 2. If disabled, enable it
export REDIS_ENABLED=True

# 3. Verify the container is running
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps redis

# 4. Restart the service
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 restart redis

# 5. Verify connectivity
python -c "from app.core.infrastructure.redis_manager import RedisManager; import asyncio; m = RedisManager.get_instance(); print(asyncio.run(m.ping()))"
```

### LLM Providers

```bash
# 1. Check API key environment variables
echo "OPENAI_API_KEY set: $([ -n \"$OPENAI_API_KEY\" ] && echo 'yes' || echo 'no')"
echo "GROQ_API_KEY set: $([ -n \"$GROQ_API_KEY\" ] && echo 'yes' || echo 'no')"
echo "OLLAMA_BASE_URL=$OLLAMA_BASE_URL"

# 2. Inspect circuit breaker status via health endpoint
curl -sf http://localhost:8000/health | python -m json.tool

# 3. Verify a specific provider manually
curl -sf http://localhost:11434/api/tags  # Ollama

# 4. Restart the application container to reset circuit breakers
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 restart janus-api
```

---

## Health Check Endpoint Reference

### `GET /healthz`

Basic health check. Returns a static `200 OK` response as long as the application process is running. Does not verify dependency health.

```json
{
  "status": "ok"
}
```

### `GET /health`

Detailed health check with system metadata. Includes per-dependency pass/fail status, latency, build reference, and Tailscale configuration.

**Healthy response:**

```json
{
  "status": "ok",
  "service": "Janus API",
  "version": "1.x.x",
  "environment": "production",
  "tailscale": {
    "enabled": true,
    "host": "janus",
    "backend_url": "http://backend:8000",
    "frontend_url": "http://frontend:4300"
  },
  "build_ref": "v1.0.0-abc1234"
}
```

**Degraded response** (e.g., Qdrant is down):

```json
{
  "status": "ok",
  "service": "Janus API",
  "version": "1.x.x",
  "environment": "production",
  "tailscale": null
}
```

Note: The `GET /health` endpoint returns the application-level status. For per-component health details with latency, scores, and circuit breaker state, use the `HealthMonitor.get_system_health()` data which is exposed through the monitoring subsystem and reports status as `"healthy"`, `"degraded"`, or `"unhealthy"` with a composite score.

**HealthMonitor report structure (degraded example):**

```json
{
  "status": "degraded",
  "score": 75,
  "message": "5/7 componentes saudáveis",
  "components": {
    "postgres": {
      "component": "postgres",
      "status": "healthy",
      "message": "PostgreSQL connection is operational",
      "details": { "latency_seconds": 0.012 },
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.015,
      "error": null
    },
    "neo4j": {
      "component": "neo4j",
      "status": "healthy",
      "message": "Neo4j connection is operational",
      "details": { "latency_seconds": 0.008 },
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.010,
      "error": null
    },
    "episodic_memory_qdrant": {
      "component": "episodic_memory_qdrant",
      "status": "degraded",
      "message": "Qdrant offline (fallback memory-only ativo)",
      "details": {},
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 2.100,
      "error": "Connection refused"
    },
    "message_broker": {
      "component": "message_broker",
      "status": "healthy",
      "message": "Conexão com RabbitMQ está operacional",
      "details": {},
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.030,
      "error": null
    },
    "redis": {
      "component": "redis",
      "status": "healthy",
      "message": "Redis connection is operational",
      "details": { "latency_seconds": 0.005 },
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.007,
      "error": null
    },
    "llm_router": {
      "component": "llm_router",
      "status": "healthy",
      "message": "Todos os provedores operacionais",
      "details": { "open_circuits": 0, "pool_instances": 4 },
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.001,
      "error": null
    },
    "multi_agent_system": {
      "component": "multi_agent_system",
      "status": "healthy",
      "message": "3 agentes ativos",
      "details": { "active_agents": 3, "workspace_tasks": 12, "pm_active": true },
      "checked_at": "2026-06-23T12:00:00",
      "duration_seconds": 0.020,
      "error": null
    }
  },
  "last_check": "2026-06-23T12:00:00",
  "suggested_timeouts": {
    "llm": 60.0,
    "qdrant_search": 30.0,
    "neo4j_query": 30.0,
    "rabbitmq_management": 5.0
  }
}
```

The `status` field in the HealthMonitor report uses these rules:

- `"healthy"` if no critical component is unhealthy and the composite score is 80 or higher
- `"degraded"` if no critical component is unhealthy and the composite score is between 50 and 79
- `"unhealthy"` if any critical component is unhealthy, or the composite score is below 50
