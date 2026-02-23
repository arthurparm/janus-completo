# API Contracts - Frontend (`frontend`)

## Base URL e Transporte

- Base principal: `API_BASE_URL` (default `/api`)
- Prefixo funcional: `/api/v1`
- Streaming: SSE em `/api/v1/chat/stream/{conversation_id}`

## Headers Relevantes

- `Authorization: Bearer <token>` via interceptor
- `X-Request-ID`, `X-User-Id`, `X-Project-Id`, `X-Session-Id` em chamadas contextualizadas

## Grupos de Endpoints Consumidos

### Chat

- `POST /api/v1/chat/start`
- `POST /api/v1/chat/message`
- `GET /api/v1/chat/{conversation_id}/history`
- `GET /api/v1/chat/stream/{conversation_id}` (SSE)

### Sistema e Operacao

- `GET /api/v1/system/status`
- `GET /api/v1/system/overview`
- `GET /api/v1/workers/status`
- `POST /api/v1/workers/start-all`
- `POST /api/v1/workers/stop-all`

### Autonomia

- `POST /api/v1/autonomy/start`
- `POST /api/v1/autonomy/stop`
- `GET /api/v1/autonomy/status`
- `GET/PUT /api/v1/autonomy/plan`
- `POST/GET/PATCH/DELETE /api/v1/autonomy/goals*`

### LLM/Observabilidade/Conhecimento

- `GET /api/v1/llm/providers`, `/health`, `/budget/summary`
- `GET /api/v1/observability/*`
- `GET /api/v1/knowledge/stats`
- `GET /api/v1/reflexion/summary/post_sprint`

### Documentos e RAG

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/list`
- `GET /api/v1/documents/search`
- `DELETE /api/v1/documents/{doc_id}`

## Erros e Resiliencia no Front

- `ChatStreamService` aplica retry exponencial com jitter em falhas SSE.
- Interceptors mapeiam erros HTTP para mensagens de UI.

## Observacoes

- `BackendApiService` concentra muitos dominios; recomendavel separar por bounded contexts para reduzir acoplamento.
- Alias de compatibilidade ativo: `JanusApiService` (deprecado) redireciona para `BackendApiService`; remocao planejada para o proximo ciclo.

---

_Gerado pelo workflow BMAD `document-project`_
