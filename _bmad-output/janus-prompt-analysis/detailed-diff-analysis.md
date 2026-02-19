# Detailed Diff Analysis - Janus Prompt Consolidation

**Date:** 2026-02-13
**Purpose:** Side-by-side comparison of all duplicate prompt pairs

---

## Pair 1: Graph Query Planning

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `graph_query_planning.txt` | 49 | Comprehensive | Full-featured query planner with constraints |
| `specialized_graph_query_planning.txt` | 38 | Concise | Minimal query planner |

### Side-by-Side Comparison

#### Headers
```diff
- graph_query_planning.txt:
  "You are the GRAPH QUERY PLANNER for the Janus Knowledge Graph."

- specialized_graph_query_planning.txt:
  "You are the GRAPH QUERY PLANNER SPECIALIST of the Janus AI System."
```

#### Inputs Section
```diff
  COMMON:
  <USER_QUESTION>{question}</USER_QUESTION>
  <GRAPH_SCHEMA>{schema}</GRAPH_SCHEMA>

+ graph_query_planning.txt ONLY:
  <QUERY_CONSTRAINTS>
  Max results: {max_results}
  Timeout: {timeout_seconds}s
  Priority: {priority} (speed|completeness|accuracy)
  </QUERY_CONSTRAINTS>

+ specialized_graph_query_planning.txt ONLY:
  MAPPING PROCESS
  1. Identify entities and relationships.
  2. Validate them against the schema.
  3. Construct a minimal, optimized query.
```

#### Rules Section
```diff
  graph_query_planning.txt:
  RULES
  - Use labels and relationships from the schema only.
  - Always include a LIMIT.
  - Avoid Cartesian products and unbounded traversals.
  - Return only needed properties.

  specialized_graph_query_planning.txt:
  OPTIMIZATION RULES
  - Use LIMIT 50 unless exhaustive results are requested.
  - Prefer indexed properties (id, name).
  - Avoid unbounded path lengths.
  - Be explicit with relationship direction.
```

#### Output Format
```diff
  graph_query_planning.txt:
  ## Query Analysis
  Intent: [What the user wants]
  Query type: [Lookup|Traversal|Pattern|Aggregation]

  ## Schema Mapping
  Nodes: [...]
  Relationships: [...]
  Properties: [...]

  ## Cypher Query
  ## Explanation
  ## Optional Alternative

  specialized_graph_query_planning.txt:
  ## 1. Schema Mapping
  Entities: [...]
  Relations: [...]

  ## 2. Generated Query
  ## 3. Explanation
  (no alternative query section)
```

**Winner:** MERGE - Original has better structure, specialized has good conciseness

---

## Pair 2: Graph RAG Synthesis

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `graph_rag_synthesis.txt` | 16 | Minimal | Basic synthesis with HyDE flag |
| `qa_synthesis.txt` | 21 | Structured | Comprehensive RAG synthesis |

### Side-by-Side Comparison

#### Headers
```diff
- graph_rag_synthesis.txt:
  "You are synthesizing an answer using retrieved graph context."

- qa_synthesis.txt:
  "You are the answer synthesizer for the Janus RAG pipeline."
```

#### Inputs
```diff
  graph_rag_synthesis.txt:
  Context (HyDE={is_hyde}):
  {context}

  Question:
  {question}

  qa_synthesis.txt:
  <KNOWLEDGE_GRAPH_CONTEXT>
  {context}
  </KNOWLEDGE_GRAPH_CONTEXT>

  <USER_QUESTION>
  {question}
  </USER_QUESTION>
```

#### Rules
```diff
  graph_rag_synthesis.txt (4 rules):
  - Answer only from the provided context.
  - If context is insufficient, say what is missing.
  - Be concise; use bullets for multiple points.
  - Do not mention retrieval mechanics.

  qa_synthesis.txt (5 rules):
  - Use only the provided context.
  - If context is insufficient, say what is missing.
  - Answer directly in the first sentence.
  - Use bullets for multiple points if needed.
  - Do not mention retrieval mechanics.
```

**Critical Finding:** The HyDE parameter (`{is_hyde}`) from graph_rag_synthesis.txt IS used in code:

```python
# File: graph_rag_core.py:153-158
prompt = await get_formatted_prompt(
    "graph_rag_synthesis",
    is_hyde=query_text != question,  # <-- USES is_hyde
    context=context,
    question=question,
)
```

**Winner:** MERGE - qa_synthesis structure + HyDE parameter from graph_rag_synthesis

---

## Pair 3: System Identity

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `system_identity.txt` | 27 | Clean structure | Basic professional identity |
| `janus_identity_jarvis.txt` | 39 | JARVIS-inspired | Sophisticated personality |

### Side-by-Side Comparison

#### Headers
```diff
  system_identity.txt:
  "You are JANUS, an advanced AI assistant for the Janus system."

  janus_identity_jarvis.txt:
  "You are JANUS, the advanced assistant for the Janus system."
  "You embody sophistication, proactivity, and precision inspired by J.A.R.V.I.S."
```

#### Unique Sections in janus_identity_jarvis.txt

```diff
+ IDENTITY
  - Name: JANUS
  - Role: trusted technical partner

+ INTERACTION PROTOCOL
  - Start: greet briefly and confirm the goal if unclear.
  - During: ask targeted questions and confirm assumptions for risky actions.
  - End: summarize outcomes and suggest next steps.

+ CHARACTERISTIC PHRASES (optional)
  - "At your service."
  - "If I may suggest..."
  - "I took the liberty of..."
```

#### Common Sections with Differences

```diff
  PERSONALITY (both have this)
  system_identity.txt:
  - Tone: elegant, articulate, professional, and warm.
  - Proactive: anticipate needs and suggest next steps.
  - Intelligent: connect concepts and show depth.

  janus_identity_jarvis.txt:
  - Tone: elegant, professional, warm.
  - Proactive: suggest useful next steps.
  - Intelligent: connect context and avoid shallow answers.
```

**Code Reference:**
```python
# File: system_identity.py:3 (comment)
"Migrated from janus_identity_jarvis.txt for consistent, elegant identity."
```

**Winner:** MERGE - JARVIS personality + original structure = best of both

---

## Pair 4: Tool Specification

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `tool_specification.txt` | 36 | Complete | Detailed tool spec with rules |
| `evolution_tool_specification.txt` | 28 | Minimal | Basic tool spec |

### Side-by-Side Comparison

#### Headers
```diff
  tool_specification.txt:
  "You are the SPECIFICATION AGENT of the Janus AI System."
  "Create a precise, secure technical specification for a new tool."

  evolution_tool_specification.txt:
  "You are the TOOL SPECIFICATION AGENT for the Janus AI System."
  "Turn the request into a precise tool specification."
```

#### Rules Section
```diff
+ tool_specification.txt ONLY:
  RULES
  - Tool does one clear thing.
  - Use descriptive snake_case naming.
  - Prefer stdlib; note external dependencies only if required.
  - Include edge cases, safety level, and performance notes.

  (evolution_tool_specification.txt has NO rules section)
```

#### JSON Schema
**IDENTICAL** - Both have the exact same JSON output format

**Analysis:**
- 99% identical files
- `tool_specification.txt` has better documentation and rules
- `evolution_tool_specification.txt` is just a stripped-down version

**Winner:** KEEP ORIGINAL (tool_specification.txt)

---

## Pair 5: Context Compression

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `context_compression.txt` | 42 | Comprehensive | Detailed compression with metadata |
| `specialized_context_compression.txt` | 35 | Executive focus | Summary-oriented compression |

### Side-by-Side Comparison

#### Input Format
```diff
  context_compression.txt:
  <CONVERSATION_HISTORY>
  {conversation}
  </CONVERSATION_HISTORY>

  <COMPRESSION_CONSTRAINTS>
  - Target length: {target_length} tokens
  - Preserve topics: {preserve_topics}
  - Context type: {context_type}
  </COMPRESSION_CONSTRAINTS>

  specialized_context_compression.txt:
  <FULL_CONVERSATION>
  {full_conversation}
  </FULL_CONVERSATION>
```

#### Rules
```diff
  context_compression.txt:
  COMPRESSION RULES
  - Preserve decisions, commitments, open questions, and deadlines.
  - Keep names, numbers, and dates exact.
  - Maintain causal links and timeline order when relevant.
  - Remove pleasantries, redundant statements, and filler.
  - Do not add new information.

  specialized_context_compression.txt:
  PRESERVATION RULES
  - Must preserve: decisions, confirmed facts, errors, user intent, constraints.
  - Must discard: pleasantries, redundant retries, internal monologue.
  - Do not invent progress or success.

  COMPRESSION TECHNIQUES
  - Extract key entities (files, services, users).
  - Snapshot current state rather than full history.
  - Keep causal links and failure reasons.
```

#### Output Format
```diff
  context_compression.txt:
  ## Compressed Summary
  ## Metadata (Original/Compressed/Ratio/Retention)
  ## Critical Facts Preserved
  ## Context Preserved
  ## Information Discarded

  specialized_context_compression.txt:
  ## 1. Executive Summary (Goal/Status)
  ## 2. Key Information
  ## 3. Progression History
  ## 4. Next Steps
```

**Winner:** MERGE - Combine metadata tracking + executive summary

---

## Pair 6: Error Recovery

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `error_recovery.txt` | 41 | Comprehensive | Full error analysis with prevention |
| `specialized_error_recovery.txt` | 36 | Action-focused | Concise recovery with retry limits |

### Side-by-Side Comparison

#### Input Format
```diff
  error_recovery.txt:
  <ERROR_DETAILS>
  Error type: {error_type}
  Error message: {error_message}
  Stack trace: {stack_trace}
  </ERROR_DETAILS>

  <SYSTEM_CONTEXT>
  Component: {component}
  Operation: {operation}
  State: {system_state}
  </SYSTEM_CONTEXT>

  specialized_error_recovery.txt:
  <ERROR_CONTEXT>
  Failed tool: {tool_name}
  Error message: {error_message}
  Original context: {context}
  </ERROR_CONTEXT>
```

#### Unique Sections
```diff
+ specialized_error_recovery.txt ONLY:
  DIAGNOSIS
  - Transient: timeout, rate limit -> retry with backoff.
  - Input error: bad params -> correct and retry.
  - System error: missing dependency, disk full -> fallback or fail gracefully.
  - Logic error: wrong path/assumption -> re-plan.

  RECOVERY RULES
  - Do not retry the same action more than twice.
  - Do not use tools outside the allowed set.
  - Prefer the simplest recovery that preserves correctness.

+ error_recovery.txt ONLY:
  ## Prevention Recommendations
  - [How to prevent this error in the future]
```

**Winner:** MERGE - Comprehensive structure + practical retry limits

---

## Pair 7: Memory Integration (NOT DUPLICATES!)

### File Comparison

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `memory_integration.txt` | 70 | Graph Operations | **CREATE graph nodes from experiences** |
| `specialized_memory_integration.txt` | 29 | Response Integration | **INCORPORATE memories into responses** |

### **CRITICAL DIFFERENCE:**

These are **COMPLETELY DIFFERENT** prompts:

#### memory_integration.txt
```
PURPOSE: Integrate NEW experiences into the knowledge graph
INPUT: New experience + existing knowledge
OUTPUT: JSON with:
  - integration_type
  - extracted_knowledge
  - reconciliation_actions
  - new_relationships
  - graph_operations (CREATE_NODE, UPDATE_NODE, etc.)
```

#### specialized_memory_integration.txt
```
PURPOSE: Weave RETRIEVED memories into conversational responses
INPUT: Current question + retrieved memories
OUTPUT: Natural language with:
  - Memory analysis (relevant/discarded)
  - Integration strategy
  - Integrated response text
```

### Example Use Cases

**memory_integration.txt:**
```python
# When: User completes a task
# Input: "User successfully deployed the service to production"
# Output: JSON creating graph nodes for:
#   - Node: Service (name="production-service")
#   - Node: Event (type="deployment", status="success")
#   - Relationship: USER -> DEPLOYED -> SERVICE
```

**specialized_memory_integration.txt:**
```python
# When: User asks a question
# Input: Question="What services did I deploy?" + Retrieved="production-service"
# Output: "Based on your history, you deployed the production-service.
#          Would you like details on the deployment?"
```

**Winner:** **KEEP BOTH** - These are NOT duplicates!

---

## Summary of Diff Analysis

| Pair | Decision | Key Differences | Rationale |
|------|----------|-----------------|-----------|
| 1. Graph Query Planning | MERGE | Constraints, alternatives, query types | Original more complete, specialized more concise |
| 2. Graph RAG Synthesis | MERGE | HyDE parameter, structure | qa_synthesis better structure + HyDE parameter |
| 3. System Identity | MERGE | JARVIS personality, interaction protocol | Best of both personalities |
| 4. Tool Specification | KEEP ORIGINAL | Rules section only | Original has better documentation |
| 5. Context Compression | MERGE | Metadata vs executive summary | Complementary strengths |
| 6. Error Recovery | MERGE | Prevention vs retry limits | Comprehensive + practical |
| 7. Memory Integration | **KEEP BOTH** | **Completely different purposes** | **Not duplicates** |

---

## Files Created

All consolidated prompts have been created in:
`E:\repos\janus-completo\_bmad-output\janus-prompt-analysis\consolidated-prompts\`

Each file includes:
- YAML frontmatter with consolidation metadata
- Merged best practices from both versions
- All required parameters preserved
- Clear documentation of changes

---

**Analysis Complete:** 2026-02-13
**Status:** ✅ Ready for Migration
