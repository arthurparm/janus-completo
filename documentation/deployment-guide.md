# Deployment Guide

## Visao Geral

A entrega local/servidor e baseada em `docker-compose.yml` com servicos de API, frontend e infraestrutura de dados/observabilidade.

## Servicos Provisionados

- `janus-api` (FastAPI)
- `frontend` (Angular dev server containerizado)
- `redis`, `postgres`, `rabbitmq`, `neo4j`, `qdrant`, `ollama`
- `prometheus`, `grafana`, `otel-collector`

## Comandos

### Subir stack

```bash
docker compose up -d
```

### Ver status

```bash
docker compose ps
```

### Logs

```bash
docker compose logs -f janus-api
docker compose logs -f frontend
```

### Health checks

- API: `http://localhost:8000/health`
- Front (container): `http://localhost:4300`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Variaveis e Segredos

- Arquivo `backend/app/.env` e usado por multiplos servicos.
- Chaves de API/credenciais nao devem ser hardcoded em ambientes versionados.

## Pipeline e Boas Praticas

- Executar testes automatizados antes do deploy.
- Versionar imagens em ambiente de CI/CD (evitar `latest` em producao).
- Separar compose de desenvolvimento e compose de producao.

---

_Gerado pelo workflow BMAD `document-project`_
