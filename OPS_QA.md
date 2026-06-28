# Operations & QA

## 1. PC1/PC2 Split Deployment

The Janus application uses a two-machine deployment architecture for performance isolation and resource optimization.

**PC2 - Stateful Services**: Runs on dedicated hardware (i9-13900F, 64GB DDR5, RTX 4060 Ti 16GB). Contains Neo4j (22GB memory, 10 CPU cores), Qdrant (12GB memory, 6 CPU cores, SSD-optimized), and Ollama (20GB memory, 8 CPU cores, 16GB VRAM via CUDA). These services need consistent high-performance access to disk and GPU. Neo4j uses 20GB heap + 12GB pagecache. Qdrant uses HNSW with memmap disabled for performance. Ollama loads up to 2 models simultaneously within the 16GB VRAM budget. The boot order on PC2 is `docker compose -f docker-compose.pc2.yml up -d`.

**PC1 - Stateless Services**: Runs the application and supporting infrastructure. Contains janus-api (4GB memory, 4 CPUs, FastAPI on port 8000), janus-frontend (1.5GB memory, 2 CPUs, Angular on port 4300), PostgreSQL 16 with pgvector (1.5GB memory, 2 CPUs), Redis 7 (384MB memory, 1 CPU), and RabbitMQ 3.13 (768MB memory, 1.5 CPUs). PC1 depends on PC2 for Neo4j, Qdrant, and Ollama connections. Boot order: start PC2 first, then PC1.

**Tailscale Interconnect**: PC1 and PC2 communicate via Tailscale VPN. The PC1 docker-compose uses environment variables pointing to PC2's Tailscale IP for `NEO4J_URI`, `QDRANT_HOST`, and `OLLAMA_HOST`. This eliminates the need for exposed public ports while maintaining low-latency connectivity.

**Boot Command**: `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d` then `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d`. The `tooling/dev.py up` command automates this sequence.

## 2. Test Structure

**Pytest Configuration**: Pytest is configured via [pyproject.toml](file:///h:/repos/janus-completo/backend/pyproject.toml) with asyncio mode (auto), strict markers, and coverage reporting.

**Unit Tests** (`backend/tests/unit/`): Test individual components in isolation with mocked dependencies. Cover kernel bootstrap contracts, LLM router refactoring, memory core DI, memory smart eviction, scheduler retention jobs, auth rate limiting, observability instrumentation, chat streaming, and security validations.

**Integration Tests** (`backend/tests/integration/`): Test component interactions with real or containerized dependencies. Cover OS tools, MetaAgent proactive remediation, Memory Core operations, Message Broker pub/sub, LLM fallback logic, Circuit Breaker resilience, Agent role-based tool filtering, and the comprehensive test_janus_comprehensive.py (1265 lines) and test_janus_subsystems.py suites.

**Contract Tests** (`qa/` directory): 9 critical test files testing API visibility, tool executor policy guards, chat agent loop content safety, memory quota enforcement, generative memory LLM role priority, chat endpoint contract, observability request dashboard, DB migration service contract, and knowledge code query contract. These are the canonical quality gates for backend changes.

**Load Tests**: `locustfile.py` for performance and load testing with configurable user counts and request patterns.

**Security Tests**: `tests/unit/test_security_asvs_lite_regression.py` covers OWASP ASVS-inspired checks including SSRF prevention, egress policy enforcement, and command injection protection.

## 3. QA Tooling

**dev.py Orchestrator**: The primary QA entry point ([tooling/dev.py](file:///h:/repos/janus-completo/tooling/dev.py)) supports commands: `up` (full stack deployment), `down` (teardown), `qa` (run all quality gates), `doctor` (diagnostics), `setup` (initial configuration), `checklist` (generate compliance checklist).

**API Inventory** (`tooling/extract_api_inventory.py`): Scans all endpoint files to build a complete inventory of API routes, methods, and parameters.

**API Matrix** (`tooling/generate_api_matrix.py`): Generates a coverage matrix comparing discovered endpoints against expected endpoints.

**Coverage Report** (`tooling/generate_api_coverage_report.py`): Validates 229 expected endpoints against actual implementations. Generates JSON and Markdown reports. Uses Docker evidence collection (log tails) for runtime validation. Fails if coverage targets are not met.

**Async Ops Validation** (`tooling/async_ops_validation.py`): Tests system behavior under concurrent load (8 users, 45s timeout, 90s chaos timeout). Validates that async operations complete within acceptable timeframes under stress.

## 4. Offline Eval Gate

**eval_technical_qa.py** ([backend/scripts/](file:///h:/repos/janus-completo/backend/scripts/eval_technical_qa.py)): The offline evaluation gate for technical QA quality.

**Offline-Codebase Mode**: Runs evaluations against the local codebase without requiring LLM API calls. Uses pre-computed embeddings and cached responses for fast iteration.

**Baseline Comparison**: Compares current run results against stored baselines in `backend/evals/technical-qa/baselines/`. Detects regressions in pass rate, citation coverage, and latency.

**Regression Gates**: Three gates with strict thresholds:
- Max pass rate drop: 2% (absolute)
- Max citation coverage drop: 2% (absolute)
- Max p95 latency increase: 250ms

**Command**: `python backend/scripts/eval_technical_qa.py --mode offline-codebase --repo-root . --dataset backend/evals/technical-qa/datasets/technical-qa.v1.json --runs-root outputs/qa/technical-qa/runs --baselines-root backend/evals/technical-qa/baselines --compare-baseline --gate-on-regression --require-baseline --max-pass-rate-drop 0.02 --max-citation-coverage-drop 0.02 --max-p95-latency-increase-ms 250`

## 5. Docker Compose Architecture

**PC1 Resource Limits** ([docker-compose.pc1.yml](file:///h:/repos/janus-completo/docker-compose.pc1.yml)):
- janus-api: mem_limit=4g, cpus=4.0, healthcheck on :8000/health
- janus-frontend: mem_limit=1536m, cpus=2.0, healthcheck on :4300/
- postgres (pgvector/pg16): mem_limit=1536m, cpus=2.0, pg_isready healthcheck
- redis (7-alpine): mem_limit=384m, cpus=1.0, AOF persistence, redis-cli ping healthcheck
- rabbitmq (3.13-management-alpine): mem_limit=768m, cpus=1.5, rabbitmq-diagnostics healthcheck

All PC1 services share the `janus-pc1-net` bridge network (172.20.0.0/16). API has read-only volume mounts for app code and scripts. Persistent volumes for postgres, redis, rabbitmq, app data, and workspace.

**PC2 Resource Limits** ([docker-compose.pc2.yml](file:///h:/repos/janus-completo/docker-compose.pc2.yml)):
- neo4j (5.19-community): mem_limit=22g, cpus=10.0 (cpuset=0-9), heap=20G, pagecache=12G, APOC plugin
- qdrant (v1.16.2): mem_limit=12g, cpus=6.0 (cpuset=10-15), HNSW without memmap, API key auth
- ollama (latest): mem_limit=20g, cpus=8.0 (cpuset=16-23), GPU passthrough for RTX 4060 Ti 16GB, CUDA v12

PC2 services share `janus-pc2-net` bridge network (172.21.0.0/16). Ollama has a companion `ollama-model-init` container that auto-pulls configured models on first boot.

## 6. Secret Validator

The secret validator ([secret_validator.py](file:///h:/repos/janus-completo/backend/app/core/security/secret_validator.py)) enforces production security by checking for known insecure default values.

**INSECURE_DEFAULTS Dictionary**:
- `NEO4J_PASSWORD`: blocked values include "password", "change_me_neo4j_password", "__required__"
- `POSTGRES_PASSWORD`: blocked values include "janus_pass", "change_me_postgres_password", "__required__"
- `RABBITMQ_PASSWORD`: blocked values include "janus_pass", "change_me_rabbitmq_password", "__required__"
- `AUTH_JWT_SECRET`: blocked values include "", "none", "null", "changeme", "change_me", "dev_secret_change_me", "janus_dev_secret"

**Behavior**: In non-production environments, validation is skipped with an info log. In production, discovery of any insecure default raises `InsecureConfigurationError` with a detailed message listing all offending settings. This prevents boot in production with weak or default credentials.

**Pydantic SecretStr**: Settings use `SecretStr` type for passwords, preventing accidental exposure in logs, error messages, or serialized output. The validator calls `get_secret_value()` to access the plaintext for comparison.

## 7. URL Safety & Egress Policy

The URL safety system ([url_safety.py](file:///h:/repos/janus-completo/backend/app/core/security/url_safety.py)) and egress policy ([egress_policy.py](file:///h:/repos/janus-completo/backend/app/core/security/egress_policy.py)) implement defense-in-depth against SSRF and unauthorized network access.

**resolve_safe_http_target**: Performs DNS resolution and classifies the resolved IP address. Blocks requests to private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), loopback (127.0.0.0/8), link-local (169.254.0.0/16), and multicast (224.0.0.0/4). For HTTP URLs, the fetch URL uses the resolved IP directly to prevent DNS rebinding attacks. For HTTPS URLs, the hostname is preserved for TLS SNI but the resolved IP is logged for audit.

**enforce_tool_http_egress**: Implements deny-by-default for tool-originated HTTP requests. Only URLs matching `TOOL_EGRESS_ALLOW_HOSTS` are permitted. Unauthorized requests are blocked with an audit trail. Returns the safe URL or raises an `EgressPolicyError`.

**enforce_worker_http_egress**: Similar deny-by-default policy for worker-originated requests, using `WORKER_EGRESS_ALLOW_HOSTS`. Additionally, auto-allows internal infrastructure hosts (RabbitMQ management API, internal Docker hosts) for operational needs. Used by the MessageBroker for queue policy reconciliation.

## 8. Rate Limiting

**Auth Rate Limiting** ([auth_rate_limiter.py](file:///h:/repos/janus-completo/backend/app/core/security/auth_rate_limiter.py)): In-memory sliding window implementation using `collections.deque` per (endpoint_key + IP + identifier) tuple. Default limits from `AUTH_RATE_LIMITS` settings: 20 req/60s for token endpoint, 10 req/60s for login, 5 req/60s for request-reset, 10 req/60s for reset. The `enforce_auth_rate_limit()` function is called as a dependency in auth endpoints. Returns HTTP 429 with `Retry-After` header. The rate limit store can be reset programmatically via `reset_auth_rate_limit_store()` for testing.

**LLM Rate Limiting** ([rate_limiter.py](file:///h:/repos/janus-completo/backend/app/core/llm/rate_limiter.py)): Multi-window tracking per (provider:model) key supporting TPM (tokens per minute), RPM (requests per minute), TPD (tokens per day), and RPD (requests per day). The `ModelUsageTracker` class uses thread-safe locks for concurrent access. Each window auto-resets on expiry. Limits can be configured via settings (`LLM_RATE_LIMITS`) and dynamically updated via `update_model_limits()` or from API response headers.

**80% Alert Threshold**: Models are considered "unavailable" when usage reaches 80% of any limit. This provides headroom to prevent hard 429 errors. The threshold is configurable via `LLM_RATE_LIMIT_THRESHOLD` (default 0.80).

**Redis Token Bucket Middleware** ([rate_limit_middleware.py](file:///h:/repos/janus-completo/backend/app/core/infrastructure/rate_limit_middleware.py)): Optional Redis-backed rate limiting using a Lua token bucket script. Provides IP-based rate limiting with configurable rate and burst capacity. Falls back to a fail-closed strategy (returning 503) or fail-open (allowing the request) based on configuration.
