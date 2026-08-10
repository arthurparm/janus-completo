# Chat turn baseline classification

Baseline: `codex/chat-turn-baseline-aff4681` at `aff4681741d77f09b1254d6eda0781d6aca0dc12`.

The 15 ADR scenarios are captured for REST and SSE. `conversation_access_denied` is the additional approval prerequisite, so the directory contains 16 scenario pairs (32 golden JSON files). `CLASSIFICATION.json` is the machine-readable, JSON-path-level acceptance contract. Unlisted differences are regressions until classified.

| Scenario | REST | SSE | Decision boundary |
|---|---|---|---|
| light_chat | Correct | Correct | Preserve answer/provider/model and one LLM call; correct REST `user_id=null`, history depth, final state and write/patch asymmetry. |
| operational_non_light | Correct | Correct | Preserve the operational answer contract; converge REST agent loop versus SSE direct LLM through the shared planner/executor. |
| discovery | Correct | Correct | Preserve static text/model; correct final state, persistence and post-response-effect divergence. |
| docs | Correct | Correct | Correct REST pending-study versus SSE completed-static split and inconsistent citation handling. |
| capabilities | Correct | Correct | Preserve static text/model; correct final state, persistence and effects. |
| blocked_tool_creation | Preserve | Correct | Preserve REST fail-closed response/security alert; make SSE obey the same policy. |
| indexed_document | Correct | Correct | Preserve answer, citations, citation status and current two deterministic grounding LLM calls; correct finalization/persistence/effects. |
| knowledge_space_pending | Correct | Correct | Preserve the pending semantic state; converge text, delivery/failure classification and final state. |
| missing_required_with_knowledge_space | Correct | Correct | Correct REST early return that drops confirmation/agent state; converge delivery/failure metadata without losing SSE confirmation. |
| missing_required_without_knowledge_space | Correct | Correct | Preserve transport-specific polling/stream UX only; replace REST in-memory job and SSE blocking/buffered study with one durable state machine. |
| secret_recall | Correct | Correct | Preserve authorized secret response and citation contract; correct SSE metadata/effects and shared finalization. |
| high_risk | Correct | Correct | Preserve confirmation payload/text; move the gate before agent-loop/LLM execution and persist once. |
| provider_error | Preserve | Preserve | Preserve REST 500 versus SSE `event:error`, error codes, one user write and no assistant write. |
| citation_timeout | Correct | Correct | Preserve the answer and transport terminal; create a shared deadline and classify timeout separately from no evidence. |
| sse_disconnect_resume | Preserve | Correct | REST is not applicable. Preserve SSE done/replay contract, but correct duplicate direct-service LLM execution and writes by retaining the ledger adapter. |
| conversation_access_denied | Correct | Preserve | Preserve 403/no-writes/no-model-execution; correct REST knowledge-space resolution occurring before conversation authorization. |

"Correct" means the snapshot intentionally reproduces at least one known bug. It is not permission to change every field: only the `correct_paths` in `CLASSIFICATION.json` may differ intentionally; every `preserve_path`, and every unlisted path, remains protected.

## Approved refactor acceptance

The Item 1 comparator now accepts only the explicit `approved_refactor_paths`, the scenario-specific `approved_scenario_paths`, and the original per-transport `correct_paths`. All unlisted changes remain regressions. The approved cross-cutting corrections are the shared finalizer metadata, the atomic assistant write, the typed planner/executor request shape, and diagnostic trace movement caused by the shared core.

After Items 2-13, the normalized REST and SSE domain result is equal in every scenario except `sse_disconnect_resume`. That remaining write-count difference is transport-specific: the direct `StreamingService` harness cannot exercise the endpoint's durable SSE ledger, while the ledger replay contract is covered independently by the stream idempotency tests. It is not treated as domain parity evidence.
