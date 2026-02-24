# API Contracts - Backend (`backend`)

## Visao Geral

- Framework: FastAPI
- Prefixo principal: `/api/v1`
- Modulos de endpoint: **39** arquivos em `app/api/v1/endpoints`
- Operacoes HTTP mapeadas por decorators: **229**

## Prefixos Principais por Dominio

- `chat`, `autonomy`, `assistant`, `agent`
- `knowledge`, `documents`, `rag`, `memory`, `context`
- `llm`, `observability`, `optimization`, `deployment`
- `users`, `profiles`, `auth`, `consents`, `pending_actions`
- `workers`, `tasks`, `tools`, `resources`, `productivity`

## Endpoints Criticos (amostra representativa)

### Chat

- `POST /api/v1/chat/start`
- `POST /api/v1/chat/message`
- `GET /api/v1/chat/{conversation_id}/history`
- `GET /api/v1/chat/stream/{conversation_id}` (SSE)

### Autonomy

- `POST /api/v1/autonomy/start`
- `POST /api/v1/autonomy/stop`
- `GET /api/v1/autonomy/status`
- `GET/PUT /api/v1/autonomy/plan`
- CRUD de metas em `/api/v1/autonomy/goals`

### Documents/RAG/Knowledge

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/list`
- `GET /api/v1/documents/search`
- `GET /api/v1/rag/*`
- `POST /api/v1/knowledge/index`
- `GET /api/v1/knowledge/stats`

### Operacao e Observabilidade

- `GET /api/v1/system/status`
- `GET /api/v1/system/overview`
- `GET /api/v1/workers/status`
- `POST /api/v1/workers/start-all`
- `GET /api/v1/observability/health/system`
- `GET /api/v1/observability/metrics/summary`

## Contratos de Streaming

- SSE em `/api/v1/chat/stream/{conversation_id}`
- Eventos esperados no cliente: `start`, `ack`, `partial/token`, `done`, `error`, `heartbeat`

## Seguranca e Controle

- Modo opcional com API key global (`PUBLIC_API_KEY`)
- JWT/local auth em endpoints de autenticacao
- trilha de auditoria e consentimento em rotas dedicadas

## Notas

- O roteador suporta modo `PUBLIC_API_MINIMAL` para exposicao reduzida de endpoints.
- Existem rotas legadas e novas convivendo; importante manter contract tests para evitar regressao.

---

_Gerado pelo workflow BMAD `document-project`_
