# Janus Completo

**Type:** Monorepo (Web + Backend)
**Primary Languages:** TypeScript (Frontend), Python (Backend)
**Architecture:** Angular SPA + FastAPI Modular Backend with Event-Driven Workers

## Project Overview

The `janus-completo` repository organizes an agentic AI system with two main parts: `front` (Angular 20) and `janus` (FastAPI API with agent engine, memory, observability, and automation). The frontend consumes the API via REST and SSE, while the backend integrates Redis, RabbitMQ, Neo4j, Qdrant, and Postgres for conversation processing, memory, and autonomous operation.

### Key Features
- Agent-assisted conversation with SSE streaming.
- Episodic memory + knowledge graph + hybrid RAG.
- Autonomous operation with planning and execution by workers.
- Observability with Prometheus, Grafana, and OpenTelemetry.
- Audit trail, pending actions, and consent control.

## Architecture

### Frontend (`front`)
- **Role:** User Interface, conversation flow, dashboards, and operations.
- **Stack:** Angular 20, RxJS, TailwindCSS, Vitest.
- **Access:** API via `/api/v1/*`.

### Backend (`janus`)
- **Role:** API, agent routing, memory, RAG, observability, and integrations.
- **Stack:** Python 3.11, FastAPI, SQLAlchemy, LangChain, Redis, RabbitMQ, Neo4j, Qdrant, PostgreSQL.

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Quickstart (Full Stack)

The recommended way to run the full stack is via Docker Compose:

```bash
docker compose up -d
```

### Local Development

#### Frontend (`front`)

```bash
cd front
npm install
npm start
```
Access at `http://localhost:4200`. Requests to `/api` are proxied to the backend.

#### Backend (`janus`)

```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Access API docs at `http://localhost:8000/docs`.

## Documentation

For detailed technical documentation, please refer to the `docs/` directory:

- [Frontend Architecture](docs/architecture-front.md)
- [Backend Architecture](docs/architecture-janus.md)
- [Integration Architecture](docs/integration-architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Contribution Guide](docs/contribution-guide.md)

Backend-specific technical notes can also be found in `janus/docs/`.

## Roadmap & Backlog

Below is the consolidated roadmap and backlog for the project (formerly `melhorias-possiveis.md`).

### 1) Code Intelligence

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| CI-001 | Fix code entity modeling in graph (File/Function/Class with consistent keys) | P0 | M | Done (2026-02-12) |
| CI-002 | Fix `CALLS` resolution to use qualified names and avoid broken links | P0 | M | Done (2026-02-12) |
| CI-003 | Incremental indexing by `git diff` (besides full reindex) | P1 | M | Idea |
| CI-004 | AST extraction of imports, decorators, signature, start/end lines | P1 | M | Idea |
| CI-005 | Support multiple languages (TS/JS/Python/SQL) in parser | P1 | L | Idea |
| CI-006 | Code question endpoint with citation (`file` + `line`) | P0 | M | Done (2026-02-12) |
| CI-007 | Hybrid search for code (lexical + vector + graph) | P1 | L | Idea |
| CI-008 | Impact map of changes (what breaks if X changes) | P1 | M | Idea |
| CI-009 | Complexity hotspots and debt automatically ranked | P2 | M | Idea |
| CI-010 | Dependency cycle detection and layer violations | P2 | M | Idea |
| CI-011 | Dead code identification and unused endpoints | P2 | M | Idea |
| CI-012 | Temporal graph of changes by commit and author | P2 | L | Idea |
| CI-013 | Explainability: why Janus answered this about code | P1 | M | Idea |
| CI-014 | "Pair reviewer" mode for PR with automatic checklist | P1 | M | Idea |
| CI-015 | Technical question evaluation dataset with versioned baseline | P0 | M | Done (2026-02-12) |

### 2) Memory, RAG, and Knowledge

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| MR-001 | Mandatory telemetry per step (`source`, `db`, `latency_ms`, `confidence`, `error_code`) | P0 | M | Done (2026-02-13) |
| MR-002 | Explicit routing policy between Postgres, vector, and graph | P0 | M | Partial |
| MR-003 | Confidence threshold with user confirmation flow | P0 | S | Done (2026-02-13) |
| MR-004 | Mandatory citations in document/code-based answers | P0 | M | Done (2026-02-13) |
| MR-005 | Semantic reranking with quality features by query type | P1 | M | Idea |
| MR-006 | Adaptive chunking by file type (code, doc, conversation) | P1 | M | Idea |
| MR-007 | Intelligent short-term memory eviction with policies by origin | P1 | S | Partial |
| MR-008 | Long-term memory with transactional consolidation in graph | P1 | M | Idea |
| MR-009 | Hierarchical summarization and compression of long conversations | P2 | M | Idea |
| MR-010 | Contradiction detection between old and new memories | P2 | M | Idea |
| MR-011 | PII protection in `pending confirmations` and tool logs | P0 | S | Done (2026-02-13) |
| MR-012 | Explainable retrieval (show why each context was included) | P1 | M | Idea |
| MR-013 | Recurrent offline evaluation (score.json + baseline comparison) | P0 | S | Partial |
| MR-014 | Semantic query cache with invalidation by source change | P2 | M | Idea |
| MR-015 | Multimodal RAG (image + text + PDF) | P3 | L | Idea |

### 3) Agents, Planning, and Execution

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| AG-001 | Hierarchical planning with goal decomposition into verifiable tasks | P1 | M | Idea |
| AG-002 | Tool policy by risk profile and scope | P0 | M | Partial |
| AG-003 | Simulation before executing destructive actions | P0 | S | Idea |
| AG-004 | Self-criticism per round with memory of recurring errors | P1 | M | Idea |
| AG-005 | Loop detection and automatic escape with alternative strategy | P1 | S | Idea |
| AG-006 | Multi-agent with fixed roles (executor, reviewer, auditor) | P2 | M | Idea |
| AG-007 | Exit checklist by task type (code, docs, deploy) | P1 | S | Idea |
| AG-008 | "Learn from human feedback" mode per approved/rejected action | P1 | M | Idea |
| AG-009 | Cost control per objective and abort by budget | P1 | S | Partial |
| AG-010 | Next best action recommender with expected score | P2 | M | Idea |

### 4) Tools, Security, and Governance

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| SG-001 | Replace fragile tool call parser with strict JSON envelope | P0 | M | Done (2026-02-13) |
| SG-002 | Argument validation by schema per tool (pydantic) | P0 | M | Done (2026-02-13) |
| SG-003 | Redaction of secrets/PII before persisting args and audit | P0 | S | Done (2026-02-13) |
| SG-004 | Sandboxing by capability and command allowlist | P0 | M | Done (2026-02-13) |
| SG-005 | Approvals with risk explanation and clear scope | P1 | S | Partial |
| SG-006 | Quotas by user/project/tool with sliding window | P1 | M | Partial |
| SG-007 | Retention policy and purge of sensitive data | P1 | M | Idea |
| SG-008 | Signed audit trail for critical actions | P2 | M | Idea |
| SG-009 | Policy simulator to validate changes before activation | P2 | M | Idea |
| SG-010 | Compliance mode (GDPR/LGPD) with pre-configured controls | P2 | M | Idea |

### 5) Observability, Quality, and Reliability

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| OQ-001 | Single dashboard per request_id (full pipeline) | P0 | M | Done (2026-02-13) |
| OQ-002 | SLOs per domain (chat, rag, tools, workers) with alerts | P0 | M | Partial |
| OQ-003 | End-to-end distributed tracing with front/back/worker correlation | P1 | M | Idea |
| OQ-004 | Standardized error taxonomy for support and product | P1 | S | Done (2026-02-13) |
| OQ-005 | Chaos tests for Redis, Neo4j, vector, and broker | P2 | M | Idea |
| OQ-006 | Contract tests for critical endpoints and SSE | P0 | M | Done (2026-02-13) |
| OQ-007 | Automatic answer quality scorecards | P1 | M | Idea |
| OQ-008 | Canary release for prompt/router changes | P2 | M | Idea |
| OQ-009 | Automatic semantic regression before deploy | P1 | M | Idea |
| OQ-010 | Postmortem template and incident playbook | P1 | S | Idea |
| OQ-011 | Automated coverage of 231 APIs with JSON report and Docker evidence | P0 | M | Planned |

### 6) Product and Experience (Front + API)

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| PX-001 | Answer explanation screen (sources, confidence, latency) | P1 | M | Idea |
| PX-002 | Clickable citation UI for code and documents | P0 | M | Done (2026-02-13) |
| PX-003 | Memory timeline per conversation and user | P1 | M | Partial |
| PX-004 | Pending approvals center with risk comparison | P1 | M | Done (2026-02-13) |
| PX-005 | Operator mode with real-time view of workers and queues | P1 | M | Partial |
| PX-006 | Global search in workspace (docs, code, conversations, tasks) | P1 | M | Idea |
| PX-007 | Quick routine actions (create task, reminder, summary) | P2 | M | Idea |
| PX-008 | Guided onboarding for new users | P2 | M | Idea |
| PX-009 | User profiles (dev, pm, qa) with behavioral defaults | P2 | S | Idea |
| PX-010 | Complete internationalization and terminological consistency | P3 | M | Idea |
| PX-011 | Simplify Chat UX for user mode (default simple mode + optional advanced panel) | P0 | S | In Progress (2026-02-13) |
| PX-012 | Clearer auth error messages (401/422) + guided reset flow | P1 | S | Planned |

### 7) Platform, Data, and Integrations

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| PL-001 | Definitive SQL schema alignment (avoid MySQL vs Postgres drift) | P0 | M | Done (2026-02-13) |
| PL-002 | Idempotent and audited migrations | P1 | M | Idea |
| PL-003 | Automated backup/restore of DB, graph, and vector | P0 | M | Idea |
| PL-004 | Multi-tenant with strong isolation per organization | P2 | L | Idea |
| PL-005 | Feature flags per environment and client | P1 | M | Idea |
| PL-006 | Declarative infrastructure provisioning (local and cloud) | P2 | M | Idea |
| PL-007 | Formal API versioning with deprecation policy | P1 | M | Idea |
| PL-008 | Native connectors (GitHub, Notion, Jira, Slack, GDrive) | P2 | L | Idea |
| PL-009 | Batch ingestion pipeline with dedupe and robust retry | P1 | M | Idea |
| PL-010 | Internal data catalog for knowledge sources | P2 | M | Idea |

### 8) DevEx and Delivery Flow

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| DX-001 | Single local setup command (devcontainer/cross-platform script) | P1 | S | Idea |
| DX-002 | Data seed and reproducible test scenarios | P1 | M | Done (2026-02-13) |
| DX-003 | Standardized lint/type/test gates in CI | P0 | S | Done (2026-02-13) |
| DX-004 | Risk-oriented PR templates with evidence | P1 | S | Idea |
| DX-005 | Load tests for chat and retrieval | P1 | M | Idea |
| DX-006 | Snapshot tests for critical prompts | P2 | M | Idea |
| DX-007 | Rapid diagnostic CLI (health + deps + config) | P1 | M | Idea |
| DX-008 | Bug reproducibility via minimal trace capture | P1 | M | Idea |
| DX-009 | Internal tool to generate evaluation datasets | P2 | M | Idea |
| DX-010 | Technical release notes bot by semantic commit | P3 | S | Idea |
| DX-011 | Live matrix of endpoints + API test execution playbook (local/CI) | P1 | S | Planned |

### 9) AI Applied to Product (Future)

| ID | Improvement | Priority | Effort | Status |
|---|---|---|---|---|
| AI-001 | Dynamic model routing by question type and cost | P1 | M | Partial |
| AI-002 | Distillation of validated answers to smaller models | P2 | L | Idea |
| AI-003 | Automatic factuality evaluator with external judge | P2 | M | Idea |
| AI-004 | Continuous learning with implicit feedback (real usage) | P2 | L | Idea |
| AI-005 | Action plan generation with automatic consistency verification | P1 | M | Idea |
| AI-006 | Architecture assistant comparing options and trade-offs | P2 | M | Idea |
| AI-007 | Episodic memory support with semantic time window | P2 | M | Idea |
| AI-008 | Hallucination detection with fallback to conservative mode | P1 | M | Idea |
| AI-009 | Supervised fine-tuning for Janus domain | P3 | L | Idea |
| AI-010 | Tutor mode to explain technical decisions step-by-step | P3 | M | Idea |
