# Janus Completo - Visao Geral do Projeto

**Data:** 2026-02-11
**Tipo:** Monorepo multi-part (web + backend)
**Arquitetura:** Frontend SPA Angular + Backend FastAPI orientado a servicos e workers

## Resumo Executivo

O repositorio `janus-completo` organiza um sistema agentico de IA com duas partes principais: `front` (Angular 20) e `janus` (API FastAPI com motor de agentes, memoria, observabilidade e automacao). O frontend consome a API via REST e SSE, enquanto o backend integra Redis, RabbitMQ, Neo4j, Qdrant e Postgres para processamento de conversa, memoria e operacao autonoma.

## Classificacao do Projeto

- **Tipo de repositorio:** monorepo
- **Partes detectadas:** 2 (`front`, `janus`)
- **Linguagens primarias:** TypeScript/HTML/SCSS (frontend), Python (backend)
- **Padrao arquitetural:** frontend componentizado + backend modular em camadas com workers orientados a fila

## Estrutura Multi-Parte

### Frontend (`front`)

- **Tipo:** web
- **Papel:** interface do usuario, fluxo de conversa, dashboards e operacao
- **Stack:** Angular 20, RxJS, TailwindCSS, Vitest, Firebase SDK

### Backend (`janus`)

- **Tipo:** backend
- **Papel:** API, roteamento de agentes, memoria, RAG, observabilidade e integracoes
- **Stack:** Python 3.11, FastAPI, SQLAlchemy, LangChain, Redis, RabbitMQ, Neo4j, Qdrant, PostgreSQL

### Integracao entre Partes

- Front usa `API_BASE_URL` com padrao `/api` e chamadas para `/api/v1/*`.
- Fluxo de streaming usa SSE em `GET /api/v1/chat/stream/{conversation_id}`.
- Backend publica health/status consumido pela UI (`/health`, `/api/v1/system/*`, `/api/v1/workers/status`).

## Stack Tecnologica (Resumo)

### Front

- Framework: Angular `^20.0.0`
- Linguagem: TypeScript `~5.9.2`
- Build: Angular CLI + `@angular/build` (Vite)
- UI: Angular Material, TailwindCSS
- Testes: Vitest + Testing Library

### Janus API

- Framework: FastAPI + Uvicorn
- Linguagem: Python `>=3.11,<3.13`
- Dados: SQLAlchemy (Postgres), Neo4j, Qdrant, Redis
- Fila/Eventos: RabbitMQ (`aio-pika`/`pika`)
- IA/LLM: LangChain ecosystem, OpenRouter, OpenAI, Gemini, Ollama, DeepSeek, xAI

## Funcionalidades-Chave

- Conversa assistida por agentes com streaming SSE.
- Memoria episodica + grafo de conhecimento + RAG hibrido.
- Operacao autonoma com planejamento e execucao por workers.
- Observabilidade com Prometheus, Grafana e OpenTelemetry.
- Controle de consentimento, pending actions e trilha de auditoria.

## Visao de Desenvolvimento

- **Frontend:** `cd front && npm install && npm start`
- **Backend (container):** `docker compose up -d`
- **Backend (local):** `cd janus && uvicorn app.main:app --reload`
- **Testes principais:** `cd front && npm run test` e `cd janus && pytest`

## Mapa de Documentacao

- `docs/index.md` - indice mestre
- `docs/architecture-front.md` - arquitetura do frontend
- `docs/architecture-janus.md` - arquitetura do backend
- `docs/integration-architecture.md` - contratos de integracao entre partes
- `docs/source-tree-analysis.md` - arvore comentada

---

_Gerado pelo workflow BMAD `document-project` (scan exhaustive)_
