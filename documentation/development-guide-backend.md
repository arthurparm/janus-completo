# Development Guide - Backend (`backend`)

## Pre-requisitos

- Python 3.11+ (CI em Python 3.12)
- Docker + Docker Compose

## Setup Recomendado (PC1 + PC2)

Na raiz do repositorio:

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

Servicos principais:

- API: `http://localhost:8000`
- Neo4j (PC2): `bolt://<pc2-tailscale-ip>:7687`
- Qdrant (PC2): `http://<pc2-tailscale-ip>:6333`
- Ollama (PC2): `http://<pc2-tailscale-ip>:11434`

## Setup Local API (alternativo)

```bash
cd backend
pip install -r requirements.txt
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

## Operacao e Health

- `GET /healthz`
- `GET /health`
- `GET /api/v1/system/status`
- `GET /api/v1/workers/status`
