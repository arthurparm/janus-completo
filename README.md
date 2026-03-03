# Janus Completo

**Type:** Monorepo with 2 parts (Frontend + Backend)
**Architecture:** Angular SPA + FastAPI modular backend with event-driven workers

## Overview

Sistema agentico dividido em frontend web e backend de IA, com suporte a memoria, RAG, observabilidade e operacao autonoma.

O repositorio `janus-completo` organiza um sistema agentico de IA com duas partes principais: `frontend` (Angular 20) e `backend` (API FastAPI com motor de agentes, memoria, observabilidade e automacao). O frontend consome a API via REST e SSE, enquanto o backend integra Redis, RabbitMQ, Neo4j, Qdrant e Postgres para processamento de conversa, memoria e operacao autonoma.

## Structure

### Frontend (`frontend/`)

- **Type:** Web Application
- **Stack:** Angular 20, TypeScript, RxJS, Tailwind, Vitest
- **Entry Point:** `frontend/src/main.ts`

### Backend (`backend/`)

- **Type:** Python Backend
- **Stack:** FastAPI, SQLAlchemy, RabbitMQ, Redis, Neo4j, Qdrant, Postgres
- **Entry Point:** `backend/app/main.py`

## Getting Started

### One-Command Local Bootstrap (Recommended)

```bash
python tooling/dev.py up
```

Optional lifecycle commands:

```bash
python tooling/dev.py setup
python tooling/dev.py qa
python tooling/dev.py down
```

### Prerequisites

- Node.js 20
- Python 3.11+
- Docker & Docker Compose (optional for full stack)

### Frontend (Local Development)

```bash
cd frontend
npm install
npm start
```
Access at: `http://localhost:4200`

### Backend (Local Development)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation at: `http://localhost:8000/docs`

### Full Stack (Docker)

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

Order is mandatory: start `PC2` first, then `PC1`.

## Documentation

Comprehensive documentation is available in the `documentation/` directory:

- [Project Overview](documentation/project-overview.md)
- [Architecture - Frontend](documentation/architecture-frontend.md)
- [Architecture - Backend](documentation/architecture-backend.md)
- [Integration Architecture](documentation/integration-architecture.md)
- [Deployment Guide](documentation/deployment-guide.md)
- [Deployment Split PC1/PC2](documentation/deployment-split-pc1-pc2.md)
- [API Endpoint Matrix (Live)](documentation/qa/api-endpoint-matrix.md)
- [API Test Playbook](documentation/qa/api-test-playbook.md)
- [Domain SLOs and Alerts](documentation/qa/domain-slo-alerts.md)

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

_Project documentation maintained in `documentation/` folder._
