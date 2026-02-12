# Integration Architecture - `front` <-> `janus`

## Topologia

```text
Browser (Angular)
  -> HTTP/SSE via /api/v1
Janus API (FastAPI)
  -> Services/Repositories
  -> RabbitMQ workers
  -> Redis / Postgres / Neo4j / Qdrant
```

## Pontos de Integracao

### 1. API REST

- Front chama `JanusApiService` para dominios: chat, autonomia, llm, observabilidade, tools, docs, knowledge.
- Base URL configuravel via `API_BASE_URL` e ambientes.

### 2. Streaming SSE

- Endpoint: `GET /api/v1/chat/stream/{conversation_id}`
- Eventos: `start`, `ack`, `partial`/`token`, `done`, `error`, `heartbeat`
- Cliente aplica reconexao com backoff.

### 3. Auth e Contexto

- Header `Authorization` via interceptor.
- Headers de correlacao/contexto (`X-Request-ID`, `X-User-Id`, etc.) em fluxos sensiveis.

### 4. Operacao e Observabilidade

- Front consulta status consolidado do backend e workers.
- Backend exporta metricas/health para observabilidade operacional.

## Contratos de Confianca

- Prefixo de API estabilizado em `/api/v1`.
- Uso de DTOs tipados no frontend reduz drift de contrato.
- Health endpoints servem como gate de readiness no front e no compose.

## Riscos de Integracao

- Alto numero de endpoints no backend aumenta risco de breaking changes sem contract tests.
- Dependencia de SSE exige observabilidade de conexao e fallback em redes restritivas.

---

_Gerado pelo workflow BMAD `document-project`_
