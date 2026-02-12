# Development Guide - Backend (`janus`)

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
cd janus
# instalar deps
# iniciar API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Estrutura de Codigo

- Endpoints: `janus/app/api/v1/endpoints`
- Servicos: `janus/app/services`
- Repositorios: `janus/app/repositories`
- Core runtime: `janus/app/core`
- Modelos: `janus/app/models`

## Testes

```bash
cd janus
pytest
```

Suites adicionais no repositorio:

- `tests/` (raiz)
- `janus/tests/` (unit, integration, e2e, smoke)

## Operacao e Health

- `GET /healthz`
- `GET /health`
- `GET /api/v1/system/status`
- `GET /api/v1/workers/status`

## Observacoes

- Worker orchestration pode iniciar automaticamente (`START_ORCHESTRATOR_WORKERS_ON_STARTUP`).
- Configuracoes de custo/LLM estao em `janus/app/config.py`.

---

_Gerado pelo workflow BMAD `document-project`_
