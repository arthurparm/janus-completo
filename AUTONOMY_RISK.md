# Autonomy & Risk Analysis

**Last Updated:** 2026-08-14

## 0. Operating Boundary

Janus's operating charter authorizes it to formulate, pursue, and revise its own objectives, in addition to serving direct requests. The canonical specification is defined in [documentation/janus-project-philosophy.md](documentation/janus-project-philosophy.md).

For risk analysis, "autonomy" means observable, policy-bound agency; it does not mean unrestricted execution. "Continuity" means persistence of identity, memory, learning, goals and commitments; it does not assert biological life, consciousness or legal personhood.

The central safety distinction is:

```text
reflect -> propose goal -> persist goal -> plan -> authorize effects -> execute -> verify -> learn
```

Each transition is a separate contract. Permission to reflect or create a goal must never be interpreted as permission to execute external effects. Reviews must treat invisible initiative, unbounded goals, missing provenance, non-reversible actions and transport-specific policy gaps as architectural defects.

The primary philosophical failure modes are:

| Failure mode | Impact | Required control |
|---|---|---|
| Canned identity without real continuity | Misleading product behavior | Prove memory, goals and state in the current runtime |
| Prompt-only goals | Goals disappear or evade governance | Persist typed lifecycle, origin, rationale and evidence |
| Goal creation conflated with execution | Unauthorized side effects | Apply policy, risk, confirmation and budget after planning |
| Reflection without a decision | Cost and anthropomorphic theater | Require a goal change, learning or explicit no-action result |
| Provider or transport identity drift | Janus contradicts its mission | Apply the constitution before mutable prompts across every path |
| Hidden autonomous initiative | Loss of trust and control | Expose rationale, cost, risk, progress, pause and cancellation |

## 1-4. Self-Study Loop, EvolutionManager, ReflectorAgent, SafeEvolutionManager + JanusLab (REMOVED)

Commit `67564805` ("refactor: overhaul auth system and harden security posture") **permanently blocked autonomous code evolution, tool creation, and sandbox access** as a deliberate security decision. `SelfStudyManager`, `EvolutionManager`, `SafeEvolutionManager`, `evolution_sandbox.py`, and the original `ReflectorAgent` (superseded by [log_aware_reflector.py](file:///h:/repos/janus-completo/backend/app/core/memory/log_aware_reflector.py)) were deleted from the codebase; `app/core/evolution/__init__.py` now exports nothing and documents the removal in its module docstring. The self-study cycle, backlog queue, tool-generation pipeline (`TOOL_SPECIFICATION_PROMPT`/`TOOL_GENERATION_PROMPT`), and Lab-validated production promotion described in earlier revisions of this document no longer exist in any form — Janus cannot generate, validate, or register new tools for itself.

**What remains**: `JanusLabManager` ([janus_lab.py](file:///h:/repos/janus-completo/backend/app/core/evolution/janus_lab.py)) is kept solely because [backend/tests/unit/test_sg018_secret_defaults_removed.py](file:///h:/repos/janus-completo/backend/tests/unit/test_sg018_secret_defaults_removed.py) still regression-tests that its Docker lab-env builder never falls back to an insecure default `NEO4J_PASSWORD`. It is not imported or reachable from any runtime path (no worker, endpoint, or scheduled task constructs it) — it exists purely as a secret-hygiene guard, not an active capability.

If autonomous tool creation is reinstated in the future, treat it as a new feature requiring its own risk review — do not assume any of the mitigations described in earlier revisions of this document (Docker isolation, SHA-256 signing, canary promotion) still apply, since the code that implemented them is gone.

## 5. Risk Assessment Matrix

**Kernel (HIGH)**: Single point of composition failure. If `_build_dependency_graph()` fails (e.g., missing attribute, import error, or configuration issue), the entire application fails to start. Mitigation: comprehensive startup tests, flag-controlled phases, graceful degradation in `_init_infrastructure()`. Residual risk: a subtle wiring bug could pass tests but fail in production with a specific configuration combination. Mitigation by testing with production-like configuration.

**LLM Router (MEDIUM)**: Budget guardrail misconfiguration could degrade all traffic to LOCAL_ONLY if `is_total_budget_threshold_exceeded()` returns a false positive. The epsilon-greedy exploration (10% of requests) could select an untested model with unexpected behavior. Circuit breaker state is per-process and not shared, so a rolling restart resets all breakers. Residual risk: provider API key rotation could silently disable a provider mid-operation without the fallback being tested.

**Multi-Agent System (HIGH)**: Agents can execute arbitrary tool calls defined in the `action_registry`. Prompt injection in project descriptions or task descriptions could cause an agent to execute unintended actions. Agents run via LangGraph's `create_agent` with native tool calling (no ReAct text parsing) and only non-SYSADMIN roles get `PermissionLevel.DANGEROUS` tools filtered out of their toolset at construction time; SYSADMIN retains full tool access. Mitigation: restricted tool permissions (PermissionLevel.SAFE/DANGEROUS), PolicyEngine validation before execution. Residual risk: a carefully crafted task description could bypass content safety heuristics.

**Tool Executor (MEDIUM)**: The JSON envelope extraction (`_validate_tool_args()`) is heuristic-based and may accept malformed input in edge cases. The PolicyEngine content safety patterns are static lists that may not catch novel injection techniques. Mitigation: argument validation via Pydantic schemas, audit logging of all executions. Residual risk: a tool with overly permissive argument types could accept unexpected input.

**Sandbox (HIGH)**: The Python sandbox (`PythonSandbox`) uses restricted `exec()` with __builtins__ limitation. The process-mode sandbox was removed in `chat-critical-audit` and Docker is now mandatory for untrusted code execution. If the Docker sandbox is unavailable (Docker daemon down, image not found), the system falls back to the in-process sandbox which has weaker isolation. Residual risk: a vulnerability in the Python interpreter could allow sandbox escape.

**Evolution/Lab (REMOVED, not mitigated-and-live)**: Autonomous tool generation and Lab-validated promotion to production were permanently deleted (see Section 1-4). There is no residual risk from this vector today because the capability does not exist, not because it is mitigated — do not cite F1.1/F1.3/F3.2/F5.2/F6.2 as active controls for this row.

**Knowledge Graph (MEDIUM)**: LLM hallucination in the consolidation pipeline could introduce incorrect entities and relationships into the Neo4j graph. The quarantine mechanism (`Quarantine` node label) provides a safety net, but quarantined data is still stored and could be queried. The `GraphGuardian` normalizes entity names, but hallucinated entities with plausible names could pass validation. Residual risk: an LLM-hallucinated entity that matches a real concept but has incorrect relationships could degrade retrieval quality. Mitigated by: F3.3 (automatic quarantine with `no_code_evidence` label), F6.4 (provenance tracking).

**Observability (LOW)**: SLO classification is heuristic-based (`_classify_event_domain()` uses path prefix matching). A misclassified operation could generate false SLO alerts or miss real breaches. Predictive anomaly detection uses statistical baselines that may not adapt quickly to legitimate traffic pattern changes. Residual risk: minimal operational impact; worst case is noisy alerts or missed anomalies.

## 6. Addressed Security Boundaries

**Prompt Injection in Agent Project Decomposition** → Mitigated by F6.1 (SafetyPlanValidator validates LLM-generated plans against safety policy) + F6.2 (PromptSanitizer removes system instructions, injection delimiters, trust markers and Unicode escape sequences from user input before LLM decomposition). The SafetyPlanValidator blocks subtasks that call permanently vetoed tools, reference system paths, contain blocked shell operators or modify security configuration files.

**LLM Hallucinated Entities in Neo4j** → Mitigated by F3.3 (quarantine automatique: entities extracted by LLM without code-source AST corroboration receive `Quarantine` label + `quarantine_reason="no_code_evidence"` and are excluded from search results). Manual review endpoint `POST /autonomy/admin/knowledge/quarantine/review` available. Automatic purge after 30 days without review.

**Dependency Confusion in Tool Execution** → Was mitigated by F1.2/F1.3/F6.4 (namespace isolation, SHA-256 signing, provenance tracking for evolution-generated tools) while autonomous tool evolution existed. That capability was permanently removed (see Section 1-4), so this attack surface no longer applies; the mitigations are not active controls today.

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
