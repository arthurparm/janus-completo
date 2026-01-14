# Implement Reflexion & Self-Correction Mechanism (Shinn et al., 2023)

This plan details the implementation of a structured error analysis and self-correction loop within the Janus Meta-Agent execution graph.

## 1. Schema Updates (`janus/app/core/agents/meta_agent_module/schemas.py`)
### Extend `AgentState`
Add fields to capture execution errors and the subsequent structured analysis.
- `execution_error`: To store the raw error message or object from the execution phase.
- `error_analysis`: To store the structured output of the Reflexion process (Root Cause, Classification, Insights).

## 2. Meta-Agent Logic (`janus/app/core/agents/meta_agent.py`)
### Modify `execution_node_logic`
- Wrap task dispatch/execution in a `try-except` block.
- On failure:
  - Capture the exception.
  - Update state with `execution_error`.
  - Return status `"execution_failed"` instead of propagating the exception immediately.

### Implement `error_reflexion_node_logic`
Create a new method to handle the "Reflexion" process:
1.  **Retrieve Error**: Extract `execution_error` and `final_plan` from the state.
2.  **Analyze (LLM)**: Use the LLM to generate a structured analysis:
    -   **Root Cause**: Verbalization of why it failed.
    -   **Classification**: Categorize the error (e.g., LogicError, EnvironmentError, Timeout).
    -   **Actionable Insights**: Specific suggestions for the next attempt.
3.  **Memory Storage**: Save this analysis to `WorkingMemory` (Short-Term Memory) with type `"reflexion"` and relevant metadata.
4.  **Update State**:
    -   Store the analysis in `error_analysis`.
    -   Update `diagnosis` or `critique` to inform the subsequent `Plan` node.
    -   Increment `retry_count`.
5.  **Decision**: Return status `"retry"` (if retries < max) or `"give_up"`.

## 3. Graph Architecture (`janus/app/core/agents/meta_agent_module/graph_builder.py`)
### Add `error_reflexion` Node
- Register the new `error_reflexion` node in the `StateGraph`, wrapping the new `error_reflexion_node_logic`.

### Update Control Flow
- **Execute Node**: Add a conditional edge.
    -   `completed` → `END`
    -   `execution_failed` → `error_reflexion`
- **Error Reflexion Node**: Add conditional edges.
    -   `retry` → `plan` (Allows replanning with new insights).
    -   `give_up` → `dead_letter` (Final failure state).

## 4. Verification
- **Unit Test**: Create a test case where the `execute` node simulates a failure.
- **Verify Graph Flow**: Ensure the graph transitions `execute` -> `error_reflexion` -> `plan` -> `reflect` -> `execute`.
- **Verify Memory**: Check that `WorkingMemory` contains the "Reflexion" entry after a failure.
