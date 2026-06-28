# Autonomy & Risk Analysis

**Last Updated:** 2026-06-23

## 1. Self-Study Loop

The SelfStudyManager ([self_study_manager.py](file:///h:/repos/janus-completo/backend/app/core/evolution/self_study_manager.py)) orchestrates the autonomous self-improvement cycle that runs during idle time.

**Offline Static Analysis**: Code analysis uses two strategies: AST parsing for Python files (via `ast` module) and regex-based extraction for JavaScript/TypeScript files. The analysis identifies function definitions, class declarations, imports, and call patterns without executing the code. This enables safe, offline analysis of the entire codebase without runtime risk.

**Incremental vs Full Modes**: In incremental mode, only files changed since the last analysis (via `git diff`) are scanned. This is the default for routine self-study cycles, typically running every 15-30 minutes. Full mode scans the entire codebase and is triggered manually or on deployment. Full mode can process up to 1200 files per run.

**SHA-256 Fingerprint Dedup**: Each analyzed code fragment is fingerprinted using SHA-256. This prevents duplicate analysis of unchanged code across cycles and reduces storage overhead. The fingerprint is used as a deterministic ID in Qdrant memory storage.

**Limits and Safeguards**: Files larger than 512KB are skipped. Maximum 1200 files per analysis run. Only local-only LLM (Ollama) is used for sprint classification to avoid API costs and ensure air-gapped operation. These limits prevent resource exhaustion.

**Cycle Flow**: (1) ReflectorAgent analyzes past experiences from memory, (2) if health_score >= 0.8, system is considered healthy and no evolution is triggered, (3) if health_score < 0.8, failed patterns are prioritized, (4) tool_missing patterns with suggested_improvements are selected as evolution candidates, (5) EvolutionManager generates and registers new tools up to MAX_EVOLUTIONS_PER_SESSION (3).

## 2. EvolutionManager

The EvolutionManager ([evolution_manager.py](file:///h:/repos/janus-completo/backend/app/core/evolution/evolution_manager.py), 329 lines) manages the tool creation lifecycle.

**Backlog Queue** (`data/evolution_backlog.json`): Persisted JSON array of evolution requests. Each item has: `request` (human description), `status` (pending/in_progress/done/failed), `created_at`, `spec` (structured tool specification), `result` (generated code), and `validation` (AST check results). The backlog provides durability across restarts.

**Request to Tool Pipeline**: `queue_request()` adds a description. `process_next_pending()` runs the full pipeline: (1) Generate structured specification via LLM using `TOOL_SPECIFICATION_PROMPT` (returns JSON with tool_name, description, arguments schema, dependencies, return_type, safety_level, edge_cases, performance_notes, usage_example), (2) Generate tool code via LLM using `TOOL_GENERATION_PROMPT`, (3) Validate generated code with `ast.parse()` for Python syntax correctness, (4) Register the tool in `action_registry` via `ToolService`.

**Dependencies**: Depends on `LLMService` for code generation (uses ModelRole.CODE_GENERATOR with LOCAL_ONLY priority for safety) and `ToolService` for tool registration and validation. The generated tool code is stored in the tools database for future execution.

## 3. ReflectorAgent

The ReflectorAgent ([reflector_agent.py](file:///h:/repos/janus-completo/backend/app/core/evolution/reflector_agent.py), 324 lines) provides the self-awareness component of the self-study loop.

**Memory Analysis**: Reads from MemoryCore to analyze past experiences. It searches for failure keywords: "error", "failed", "não consegui", "não foi possível", "timeout", "exception", "falha", "problema", "tool not found", "comando não encontrado". It also detects user dissatisfaction signals: "errado", "incorreto", "wrong", "não era isso", "tente novamente", "try again", "não funcionou".

**Failure Pattern Detection**: Groups related failures into `FailurePattern` instances with fields: `pattern_type` (error_type, timeout, tool_missing, user_dissatisfaction), `count` (occurrence frequency), `examples` (sample experiences), `severity` (1-10), `suggested_improvement` (actionable recommendation), and `first_seen`/`last_seen` timestamps.

**Health Score**: Computes an `overall_health_score` (0.0-1.0) based on the ratio of successful to failed experiences, weighted by recency. More recent failures have higher impact. A score below 0.8 triggers self-study evolution.

**ReflectionReport**: Produces a structured report with `health_score`, `failure_patterns` list, `summary` (natural language), `observation_count` (total experiences analyzed), and `time_period` (analysis window). The report feeds directly into the SelfStudyManager's decision process.

## 4. SafeEvolutionManager + JanusLab

The SafeEvolutionManager ([safe_evolution_manager.py](file:///h:/repos/janus-completo/backend/app/core/evolution/safe_evolution_manager.py), 359 lines) combines self-reflection with JanusLab for validated autonomous evolution.

**Lab Container**: JanusLab ([janus_lab.py](file:///h:/repos/janus-completo/backend/app/core/evolution/janus_lab.py), 366 lines) spawns Docker containers using the `janus-completo-janus-api:latest` image. Containers are named with the `janus_lab_` prefix. Lab containers connect to the `janus-completo_janus-net` network for isolation.

**Restricted Environment**: Lab containers run with `DISABLE_WORKERS=true` (no background processing), `DISABLE_MEMORY_WRITES=true` (read-only memory), and `ENVIRONMENT=lab` (non-production settings). This prevents the lab instance from modifying production data or starting long-running processes.

**No-Network Mode**: Lab containers operate in an isolated Docker network without external internet access. This prevents accidental data exfiltration or external service calls during testing.

**Auto-Destroy**: Lab containers self-destroy after 600 seconds (LAB_TEST_TIMEOUT). If the lab test completes early, the container is destroyed immediately. This prevents resource leaks from abandoned lab instances.

**Validation Pipeline**: The `_attempt_safe_evolution()` method: (1) Generates tool code via EvolutionManager, (2) Spawns Lab container, (3) Applies the code change to the Lab, (4) Runs validation tests inside Lab, (5) If tests pass, applies the change to the Prime (production) instance, (6) Destroys Lab container. Limited to 2 attempts per session (`MAX_ATTEMPTS_PER_SESSION=2`).

**LogAwareReflector**: The enhanced reflector ([log_aware_reflector.py](file:///h:/repos/janus-completo/backend/app/core/memory/log_aware_reflector.py), 453 lines) reads actual application log files (janus.log, Docker container logs) in addition to Qdrant memory. This catches real runtime errors that would not appear in memory experiences, such as import errors, configuration issues, and system-level failures.

## 5. Risk Assessment Matrix

**Kernel (HIGH)**: Single point of composition failure. If `_build_dependency_graph()` fails (e.g., missing attribute, import error, or configuration issue), the entire application fails to start. Mitigation: comprehensive startup tests, flag-controlled phases, graceful degradation in `_init_infrastructure()`. Residual risk: a subtle wiring bug could pass tests but fail in production with a specific configuration combination. Mitigation by testing with production-like configuration.

**LLM Router (MEDIUM)**: Budget guardrail misconfiguration could degrade all traffic to LOCAL_ONLY if `is_total_budget_threshold_exceeded()` returns a false positive. The epsilon-greedy exploration (10% of requests) could select an untested model with unexpected behavior. Circuit breaker state is per-process and not shared, so a rolling restart resets all breakers. Residual risk: provider API key rotation could silently disable a provider mid-operation without the fallback being tested.

**Multi-Agent System (HIGH)**: Agents can execute arbitrary tool calls defined in the `action_registry`. Prompt injection in project descriptions or task descriptions could cause an agent to execute unintended actions. The LangChain ReAct agent format provides instruction boundaries, but prompt injection is an active threat. Mitigation: restricted tool permissions (PermissionLevel.SAFE/DANGEROUS), PolicyEngine validation before execution. Residual risk: a carefully crafted task description could bypass content safety heuristics.

**Tool Executor (MEDIUM)**: The JSON envelope extraction (`_validate_tool_args()`) is heuristic-based and may accept malformed input in edge cases. The PolicyEngine content safety patterns are static lists that may not catch novel injection techniques. Mitigation: argument validation via Pydantic schemas, audit logging of all executions. Residual risk: a tool with overly permissive argument types could accept unexpected input.

**Sandbox (HIGH)**: The Python sandbox (`PythonSandbox`) uses restricted `exec()` with __builtins__ limitation. The process-mode sandbox was removed in `chat-critical-audit` and Docker is now mandatory for untrusted code execution. If the Docker sandbox is unavailable (Docker daemon down, image not found), the system falls back to the in-process sandbox which has weaker isolation. Residual risk: a vulnerability in the Python interpreter could allow sandbox escape.

**Evolution/Lab (HIGH)**: Auto-evolution with potential impact on production stability. The evolution manager generates and registers tools automatically. A poorly generated tool could introduce bugs, performance issues, or security vulnerabilities. Mitigation: Docker isolation in JanusLab, restricted environment, auto-destroy. Residual risk: the validation tests in Lab may not catch all edge cases, and a tool that passes Lab validation could still fail in production with real data. Mitigated by: F1.1 (EvolutionSandbox Docker isolation), F1.3 (SHA-256 signing), F3.2 (automatic rollback), F5.2 (canary deployment), F6.2 (PromptSanitizer).

**Knowledge Graph (MEDIUM)**: LLM hallucination in the consolidation pipeline could introduce incorrect entities and relationships into the Neo4j graph. The quarantine mechanism (`Quarantine` node label) provides a safety net, but quarantined data is still stored and could be queried. The `GraphGuardian` normalizes entity names, but hallucinated entities with plausible names could pass validation. Residual risk: an LLM-hallucinated entity that matches a real concept but has incorrect relationships could degrade retrieval quality. Mitigated by: F3.3 (automatic quarantine with `no_code_evidence` label), F6.4 (provenance tracking).

**Observability (LOW)**: SLO classification is heuristic-based (`_classify_event_domain()` uses path prefix matching). A misclassified operation could generate false SLO alerts or miss real breaches. Predictive anomaly detection uses statistical baselines that may not adapt quickly to legitimate traffic pattern changes. Residual risk: minimal operational impact; worst case is noisy alerts or missed anomalies.

## 6. Addressed Security Boundaries

**Prompt Injection in Agent Project Decomposition** → Mitigated by F6.1 (SafetyPlanValidator validates LLM-generated plans against safety policy) + F6.2 (PromptSanitizer removes system instructions, injection delimiters, trust markers and Unicode escape sequences from user input before LLM decomposition). The SafetyPlanValidator blocks subtasks that call permanently vetoed tools, reference system paths, contain blocked shell operators or modify security configuration files.

**LLM Hallucinated Entities in Neo4j** → Mitigated by F3.3 (quarantine automatique: entities extracted by LLM without code-source AST corroboration receive `Quarantine` label + `quarantine_reason="no_code_evidence"` and are excluded from search results). Manual review endpoint `POST /autonomy/admin/knowledge/quarantine/review` available. Automatic purge after 30 days without review.

**Dependency Confusion in Tool Execution** → Mitigated by F1.2 (namespace isolation: core/evolution/user with hierarchical resolution — evolution cannot shadow core), F1.3 (SHA-256 code signing verified before every evolution tool execution), and F6.4 (provenance tracking recording creator, timestamp, LLM model and evolution_attempt_id for every evolution tool).

## 7. Residual Monitoring Gaps

The following require continuous monitoring but do not justify new implementation phases:

| Gap | Monitoring Strategy |
|---|---|
| Sandbox escape via Python interpreter vulnerability | Monitor Docker security updates. EvolutionSandbox runs with `network_mode=none`, `read_only=True`, `tmpfs /tmp`. AST validation blocks imports of `subprocess`, `os`, `socket`, `requests`. |
| LLM routing degradation | Existing LLM Router budget guardrail and model-specific circuit breakers monitor this. |
| Knowledge graph quality drift | Monitored via `autonomy_quarantined_entities_count`. Periodic review via admin endpoint. |
| Canary promotion latency | `_canary_promote()` requires external scheduler invocation. Monitor `autonomy_canary_traffic_split` to ensure promotion completes. |
| Federated entity propagation | `KnowledgeFederation` validates SHA-256 + source before accepting. Monitor `AUTONOMY_FEDERATION_ENABLED` flag. |

## 8. Architecture Evolution

| Phase | Scope | Spec |
|---|---|---|
| 1-5 | Foundation, Governance, Resilience, Observability, Scale | `autonomy-build-plan` |
| 6-8 | Hardening, Tests, Documentation | `autonomy-next-phases` |
| 9-11 | Intelligence, Cost Governance, Maintenance | `autonomy-final-phases` |
