# Janus Completo

**Type:** Monorepo with 2 parts (Frontend + Backend)
**Architecture:** Angular SPA + FastAPI modular backend with event-driven workers

## Overview

Sistema agentico dividido em frontend web e backend de IA, com suporte a memoria, RAG, observabilidade e operacao autonoma.

O repositorio `janus-completo` organiza um sistema agentico de IA com duas partes principais: `front` (Angular 20) e `janus` (API FastAPI com motor de agentes, memoria, observabilidade e automacao). O frontend consome a API via REST e SSE, enquanto o backend integra Redis, RabbitMQ, Neo4j, Qdrant e Postgres para processamento de conversa, memoria e operacao autonoma.

## Structure

### Frontend (`front/`)

- **Type:** Web Application
- **Stack:** Angular 20, TypeScript, RxJS, Tailwind, Vitest
- **Entry Point:** `front/src/main.ts`

### Backend (`janus/`)

- **Type:** Python Backend
- **Stack:** FastAPI, SQLAlchemy, RabbitMQ, Redis, Neo4j, Qdrant, Postgres
- **Entry Point:** `janus/app/main.py`

## Getting Started

### Prerequisites

- Node.js 20
- Python 3.11+
- Docker & Docker Compose (optional for full stack)

### Frontend (Local Development)

```bash
cd front
npm install
npm start
```
Access at: `http://localhost:4200`

### Backend (Local Development)

```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation at: `http://localhost:8000/docs`

### Full Stack (Docker)

```bash
docker compose up -d
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Project Overview](docs/project-overview.md)
- [Architecture - Frontend](docs/architecture-front.md)
- [Architecture - Backend](docs/architecture-janus.md)
- [Integration Architecture](docs/integration-architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [API Endpoint Matrix (Live)](docs/qa/api-endpoint-matrix.md)
- [API Test Playbook](docs/qa/api-test-playbook.md)

## Roadmap / Backlog

Consolidated from prior planning artifacts.

| ID | Prioridade | Task | Dono primário | Resultado esperado |
|---|---|---|---|---|
| JNS-001 | P0 | Sanitizar artefatos de épicos (canônico UTF-8 + shards limpos) | Tech Writer + SM | Base documental íntegra |
| JNS-002 | P0 | Rastreabilidade por story (FRs + NFRs) | PM + SM | Cobertura auditável por história |
| JNS-003 | P0 | ACs mensuráveis em todas as stories críticas | PM + QA | Critérios testáveis e objetivos |
| JNS-004 | P0 | Hardening de fluxos sensíveis (expiração, concorrência, idempotência, rollback) | Architect + QA | Governança operacional robusta |
| JNS-005 | P0 | Contract/Gate baseline (problem+json, REST/SSE contract tests, CI block) | Architect + Dev | Regressão bloqueada |
| JNS-006 | P0 | Cadência BMAD multi-agente (DoR/DoD + handoffs) | SM | Execução previsível |
| JNS-007 | P1 | Janus Orchestrator Kernel (roteamento por intenção/risco/confiança) | Architect + Dev | Orquestração multi-agente real |
| JNS-008 | P1 | Memory Service v1 (curto/médio/longo prazo por tenant/usuário/thread) | Dev | Contexto persistente útil |
| JNS-009 | P1 | Agent Runtime Contract v1 (IO, confidence, evidence, handoff) | Architect | Interoperabilidade entre agentes |
| JNS-010 | P1 | Console UX 3 painéis com timeline de evidência | UX + Dev | Loop operacional completo |
| JNS-011 | P1 | Quality Gates por risco (testes + política) | Test Architect | Segurança de execução |
| JNS-012 | P2 | Governança adaptativa + learning loop contínuo | PM + Architect | Evolução contínua do super agente |

---

_Project documentation maintained in `docs/` folder._
