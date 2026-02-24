# Development Guide - Backend (`backend`)

## Pre-requisitos

- Python 3.11
- Poetry/uv (dependendo do fluxo local)
- Docker + Docker Compose (recomendado)

## Setup Recomendado (Stack Completa)

Na raiz do repositorio:

```bash
docker compose up -d
```

Servicos principais expostos:

- API: `http://localhost:8000`
- Front (container): `http://localhost:4300`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`

## Setup Local API (alternativo)

```bash
cd backend
# instalar deps
# iniciar API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Estrutura de Codigo

- Endpoints: `backend/app/api/v1/endpoints`
- Servicos: `backend/app/services`
- Repositorios: `backend/app/repositories`
- Core runtime: `backend/app/core`
- Modelos: `backend/app/models`

## Testes

```bash
cd backend
pytest
```

Suites adicionais no repositorio:

- `qa/` (raiz)
- `backend/tests/` (unit, integration, e2e, smoke)

## Operacao e Health

- `GET /healthz`
- `GET /health`
- `GET /api/v1/system/status`
- `GET /api/v1/workers/status`

## Observacoes

- Worker orchestration pode iniciar automaticamente (`START_ORCHESTRATOR_WORKERS_ON_STARTUP`).
- Configuracoes de custo/LLM estao em `backend/app/config.py`.

---

_Gerado pelo workflow BMAD `document-project`_
