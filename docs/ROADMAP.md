# 🗺️ Janus Roadmap & Technical Debt

> *Originally extracted from V1 Launch plan. Last consolidated update: 2026.*

This document defines the critical path for the **Janus V1** launch and beyond, prioritizing robustness, scientific grounding, and production readiness.

## 📌 Index

- [Backlog by Difficulty](#-backlog-by-difficulty-throughput--medium--hard)
- [Scientific Frontier (Post-V1 Evolution)](#-scientific-frontier-post-v1-evolution)
- [Infrastructure Strategy (Phase 3)](#-infrastructure-strategy-phase-3)
- [V1 Critical Path (Launch Blockers)](#-v1-critical-path-launch-blockers)
- [Conclusion History (Archived)](#-conclusion-history-archived)

---

## 🧱 Backlog by Difficulty (Throughput / Medium / Hard)

Practical criteria:
- **Throughput**: Well-defined, mechanical changes, low risk (Good for "Mini" models).
- **Medium**: Requires system context and some design, but manageable scope.
- **Hard**: High risk, cross-dependencies, structural refactoring, concurrency, or security.

### 🟢 Throughput

- Adjust CSP for production (reduce `unsafe-inline`/`unsafe-eval`) in *Security Headers Middleware*.
- Standardize success/error/warn toasts in critical flows in *UX Improvements*.
- Sweep and centralization of hardcoded settings/URLs in `environment.ts` in *Hardcoded Settings*.
- Sanitize `eslint-report.json` and lock regressions in CI in *Linter Bankruptcy*.

### 🟡 Medium

- Complete *UI Coverage* (missing screens, empty/error/loading states).
- Resolve *Autonomy 500 Error* (reproduce, fix, test).
- Implement *Input Sanitization* (policy per endpoint + extra validation for free payloads).
- Evolve *Smart Model Routing* with complexity classification (heuristic/embedding).

### 🔴 Hard

- Fix *Broken Thought Stream* (RabbitMQ → SSE → UI) with E2E test.
- Eliminate *State Desync* (define single source of truth and migrate).
- Replace *Ad-hoc State Management* with robust store (SignalStore/Elf/NgRx).
- Unify Design System (*Design System Conflict*: remove Material gradually).
- Implement *Immutable Audit Log* (append-only + tamper-evident + access control).
- Finalize *Database Migration Pipeline* (Alembic + CI/deploy).
- Implement *Graceful Degradation* (degradation matrix + health/alerts).
- Scientific Foundation/Frontier: Pending research/implementation items (LATS/ToT/Self-RAG/RAPTOR/etc).

---

## 🧪 Scientific Frontier (Post-V1 Evolution)

*Avant-garde concepts (2025/2026) to transform Janus into an embryonic AGI.*

### 🧩 Self-Evolving Toolset (Agent-0 Style)

* **Concept**: The agent not only uses tools but **creates** its own tools.
* **Implementation**: `ToolSynthesizerAgent`. When Janus identifies a repetitive task without a tool, it writes a Python script, validates it in the Sandbox, and if it works, saves it to the DB as a new permanent `Tool`.

### 🐝 Swarm Intelligence (Decentralization)

* **Concept**: Abandon centralized orchestration for a swarm model.
* **Implementation**: **Dynamic Handoffs**. Agents can transfer execution directly to other specialists (`transfer_to_agent`) without passing through the Supervisor, reducing latency and bottlenecks.

### 💾 Active Memory Management (OS-Level)

* **Concept**: The LLM actively manages its context window like an Operating System manages RAM.
  * **Implementation**: Control token `<memory_warning>`. When context fills up, the agent is forced to decide what to "forget" (delete) or "archive" (save to Neo4j) before continuing.

### 🧬 Code Generation & Rigor

1. **Flow Engineering / AlphaCodium** - *CodiumAI, 2024*
    * **Concept**: Replace "zero-shot coding" with a rigid iterative flow: *Yaml Analysis -> Plan -> Tests -> Code -> Fix*.
    * **In Janus**: Refactoring `CoderAgent` to follow this rigid StateFlow (increases accuracy from ~19% to ~44%).
2. **Hippocampal Memory Replay** - *DeepMind/Stanford*
    * **Concept**: Offline consolidation. The agent "dreams" (simulates tasks) during idle time to reinforce connections in the Graph.
    * **In Janus**: Upgrade in `SelfStudyManager` to run replays of past experiences.

### ⏱️ Latency & UX

1. **Skeleton-of-Thought** - *Ning et al., 2023*
    * **Concept**: Generate the skeleton (topics) of the answer first, then fill in the content in parallel.
    * **In Janus**: Optimization for long chat responses, reducing perceived latency.

---

## 🏛️ Infrastructure Strategy (Phase 3)

### 🧠 Model Routing Strategy (The "Brains")

* **DeepSeek V3/R1** (The Workhorse):
  * *Usage*: Heavy coding, refactoring, generation.
  * *Why*: Best cost-benefit for code (beats GPT-4 in dev benchmarks).
  * *Cost*: ~$0.14/1M input | ~$0.28/1M output.

* **Qwen 2.5 72B** (The Architect):
  * *Usage*: Critical review, System Design, Logic validation.
  * *Why*: SOTA coding performance (similar to Claude/GPT-4), but extremely accessible.
  * *Cost*: ~$0.12/1M input | ~$0.39/1M output.
  * *Comparison*: **GPT-5.2 Mini** costs **$2.00/1M output** (5x more expensive) and offers no real free quota.

* **Llama-3-Local / Flash** (The Speedster):
* *Usage*: Fast chat, Classification, Routing.

### 💰 Budget & Rate Limiting Strategy (Dual-Wallet)

* **Wallet A (DeepSeek API - $9.50)**:
  * **Usage**: 100% dedicated to **Workhorse (DeepSeek V3)**.
  * **Advantage**: Lower latency (direct source) and does not consume OpenRouter balance.

* **Wallet B (OpenRouter - $10.00)**:
  * **Primary Usage**: **Architect (Qwen 2.5 72B)** (Reviews and Decisions).
  * **Perk**: Having >$0 credit unlocks **1000 requests/day** on Free/Trial models.
  * **Secondary Usage**: Speedster (Llama 3 Free) via daily free quota.

* **Suggested Daily Distribution**:
    1. **Workhorse (Via Direct API)**: ~700 requests (Consumes balance A).
    2. **Architect (Via OpenRouter)**: ~200 requests (Consumes balance B).
    3. **Speedster (Via OpenRouter Free)**: ~100 requests (Consumes daily quota, zero cost).

### ☢️ The Privacy Dilemma (Option C)

* **OpenAI Data Sharing (Complimentary Tokens)**:
  * **What it is**: OpenAI offers free tokens (e.g., 250k/day) if you allow them to train on your data.
  * **The "Nightmare" Risk**: All Janus code, prompts, and strategies become OpenAI training property. If Janus creates something innovative, OpenAI learns it.
  * **Verdict**: **Enable ONLY if the project has no critical trade secrets/IP.** Otherwise, the cost of violated privacy >>> $10 savings.

### 🛡️ The Free-Tier Army (Option D - Risk Free)

The best *real* free quotas of 2026 (No privacy cost):

1. **Google Gemini (Free Tier)**:
    * **Quota**: ~1500 requests/day (Flash 2.5).
    * **Usage**: Long text summaries, multimodal processing (images/video).
2. **Groq (Free Tier)**:
    * **Quota**: ~14.4k requests/day (Llama 3.1 8B) or ~1k/day (larger models).
    * **Usage**: Ultra-fast routing, simple chat.
3. **Cohere (Trial)**: ~1000 calls/month (Limited, good only for sporadic Reranking).

### 📜 Protocol: Strict Structured Outputs

* **Decision**: Abandon generic "JSON Mode".
* **New Standard**: **Native Structured Outputs** (OpenAI `response_format` / Anthropic `tool_use` with `strict: true`).
* **DeepSeek Specifics**: DeepSeek V3 supports *Strict Mode* (Function Calling) via `beta` endpoint or advanced prompt engineering. We will use the OpenAI-compatible standard from DeepSeek.
* **Reason**: Guarantees 100% Schema adherence (zero parse errors), eliminating retry loops and manual validators.

---

## 🚨 V1 Critical Path (Launch Blockers)

*Mandatory items for version 1.0 launch.*

### 🛡️ Security & Enterprise Ready

* [x] **Security Headers Middleware**: Implement CSP, HSTS, X-Frame-Options, and X-Content-Type-Options.
  - [x] Middleware created (`SecurityHeadersMiddleware`).
  - [x] Registered in FastAPI (`app.add_middleware(SecurityHeadersMiddleware)`).
  - [x] Headers applied in response (CSP, HSTS, XFO, X-CTO, Referrer/Permissions).
  - [ ] Adjust CSP for production (reduce/avoid `unsafe-inline` and `unsafe-eval` when possible).

* [ ] **Input Sanitization**: Validate and sanitize all API inputs (injection prevention).
  - [ ] Define sanitization policy per endpoint (query/body/path).
  - [ ] Apply extra validation for free payloads (e.g., prompts, URLs, markdown).
  - [ ] Standardize validation errors (Problem+JSON) and metrics.
* [ ] **Rate Limiting (Cost-Based)**: Limit users by **dollar spend**, not just requests.
  - [x] Daily budget per user/project applied in LLM calls (`max_tokens` cut by USD).
  - [x] Spend tracking per tenant/provider in Redis (spend USD).
  - [ ] Propagate enforcement to HTTP gateway (block by budget per endpoint/user).
* [ ] **Immutable Audit Log**: Ensure critical action logs cannot be altered.
  - [ ] Define event format (append-only) and critical action categories.
  - [ ] Persist events with chained hash (tamper-evident).
  - [ ] Expose audit/query with access control.

### 🖥️ Frontend V1 (Refactor & Finish)

* [ ] **UI Overhaul (Clean/Professional)**: Migrate from "Magicpunk" to professional/minimalist SaaS aesthetic (Shadcn/UI + Tailwind).
  - [ ] Consolidate tokens (colors/spacing/typography) and remove legacy styles.
  - [ ] Replace main components with equivalents in the new design system.
  - [ ] Define consistent base layout (header/sidebar/cards/tables).
* [ ] **Complete UI Coverage**: Implement missing screens (80%+) following new Design System (Tools, Workers, RAG).
  - [ ] Map missing pages/screens and prioritize by usage.
  - [ ] Implement routes and empty states (empty/error/loading).
  - [ ] Ensure visual and interaction consistency (buttons, tables, dialogs).

* [ ] **UX Improvements**:
  * Real-time Feedback (Global Toasts).
  * Onboarding Flow (Setup Wizard).
  * Friendly error handling.
  - [x] Global Toast infra available (UiToastService/UiToasterComponent).
  - [ ] Standardize toasts for success/error/warn in critical flows.
  - [ ] Create onboarding wizard (first access / setup).
  - [ ] Normalize error messages from API (Problem+JSON) to UI.

#### 🐛 Critical Bugs & Failures (High Priority)

* [ ] **Broken Thought Stream**: Agent thought stream (SSE) not receiving events from RabbitMQ (Chat Screen).
  - [ ] Confirm event consumption (RabbitMQ) in backend and fanout to SSE.
  - [ ] Validate event contract (types/payload) and ordering.
  - [ ] E2E Test: publish event -> UI receives and renders.
* [ ] **Autonomy 500 Error**: Internal Server Error (500) prevents creation of Strategic Goals.
  - [ ] Reproduce error and capture stacktrace.
  - [ ] Fix validation/DI/repos and add test.
  - [ ] Ensure Problem+JSON return for controlled error.
* [ ] **State Desync**: Lack of reactivity between Backend (Redis) and Frontend (NgRx/Signals).
  - [ ] Identify duplicate sources of truth (store/local state/cache).
  - [ ] Define single state strategy (SignalStore/Elf/NgRx) and migration.
  - [ ] Add reactivity tests (component/store).

#### 🏚️ Technical Debt & Clean Code

* [ ] **Linter Bankruptcy**: Giant `eslint-report.json` (>400KB). Massive correction and stricter rules needed.
  - [ ] Reduce critical violations first (security/bug-prone rules).
  - [ ] Ensure lint in CI and block regressions.
  - [ ] Remove/generate `eslint-report.json` only on demand.
* [ ] **Hardcoded Settings**: Remove hardcoded keys and URLs; move to `environment.ts`.
  - [ ] Sweep for fixed URLs/keys in frontend.
  - [ ] Centralize in `environment.ts` + `api.config.ts`.
  - [ ] Ensure fallback by environment (dev/prod/tailscale).
* [ ] **Test Coverage Zero**: No unit or e2e tests running on frontend currently.
  - [ ] Ensure minimal suite running in CI (unit).
  - [ ] Add smoke e2e (login + chat).
  - [ ] Define coverage goal (per critical module).
* [x] **Legacy Testing Stack**: Update from Karma/Jasmine to Vitest/Jest + Testing Library (2026 Standard).
  - [x] Vitest configured in frontend (`vitest.config.ts` / script `npm test`).
  - [x] Testing Library present (`@testing-library/angular`).
* [ ] **Ad-hoc State Management**: Replace `GlobalStateStore` (Manual signals with high cognitive load) with robust lib (NgRx SignalStore or Elf) to avoid "State Desync".
  - [ ] Define target (NgRx SignalStore vs Elf) and guideline.
  - [ ] Migrate critical modules (Chat, Goals, Autonomy) first.
  - [ ] Remove redundant manual patterns after migration.
* [ ] **Design System Conflict**: Remove Angular Material gradually and unify on Shadcn/UI (Tailwind) to reduce bundle size and visual inconsistencies.
  - [ ] Map Angular Material usage points and prioritize replacements.
  - [ ] Remove dependencies/styles when migration reaches critical mass.

### ⚙️ Stability & Ops

* [ ] **Database Migration Pipeline**: Finalize transition to Alembic (abandon manual scripts).
  - [ ] Introduce Alembic (config + env) and first migration.
  - [ ] Integrate migrations in deploy/CI.
  - [ ] Document operational upgrade/downgrade flow.

* [ ] **Smart Model Routing**: Router that chooses between Local/API based on task complexity (Economy).
  - [x] Routing by role/priority available (Local vs Cloud).
  - [x] Budget guardrails and cost fallback in LLM pipeline.
  - [ ] Automatically classify complexity (heuristic/embedding) and adjust priority.
* [ ] **Graceful Degradation**: Clear fallbacks when services (e.g., Redis, Neo4j) go down.
  - [ ] Define degradation matrix by dependency (Redis/Neo4j/Qdrant/RabbitMQ).
  - [ ] Ensure fail-open/fail-closed behavior per endpoint according to criticality.
  - [ ] Expose status and alerts (health checks + metrics) for each degraded mode.

---

## ✅ Conclusion History (Archived)

### Foundation & Architecture

* [x] **Hybrid Agent Architecture** (LangGraph + PydanticAI).
* [x] **Native GraphRAG** (neo4j-graphrag).
* [x] **Centralized HITL** (Human-in-the-loop via Postgres Checkpoints).
* [x] **Graph Versioning** (Schema Migration & Purge).
* [x] **Observability** (LangSmith Tracing & Setup).
* [x] **Async Database Pool** (asyncpg + SQLAlchemy).
* [x] **Secure Sandbox** (Docker-based execution).
* [x] **MySQL → PostgreSQL Migration** (pgvector).
* [x] **Redis State Backend**.
