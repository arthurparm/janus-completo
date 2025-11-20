## Objetivo
Elevar o backend de chat para padrões robustos de desempenho, resiliência e observabilidade, padronizando SSE, protegendo com circuit breakers e CORS, e entregando testes com critérios de aceitação claros.

## Contexto Atual
- SSE já exposto em `GET /api/v1/chat/stream/{conversation_id}`: `janus/app/api/v1/endpoints/chat.py:188–212`
- Geração de eventos em `ChatService.stream_message`: `janus/app/services/chat_service.py:582–739`
- Eventos hoje: `start`, `ack`, `partial`, `done`, `error`

## Implementações
### 1) Validação de Performance em `ChatService.stream_message`
- Limites configuráveis (via env/config): `MAX_MESSAGE_BYTES`, `DEFAULT_TIMEOUT_SECONDS`, `HEARTBEAT_INTERVAL_SECONDS`.
- Tamanho máximo (10KB): antes de `_repo.add_message`, validar `len(message.encode('utf-8')) <= MAX_MESSAGE_BYTES` e:
  - Se exceder: emitir `event: error` com `code: "MessageTooLarge"` e abortar.
- Monitoramento de timeouts:
  - Medir TTFT: marcar tempo ao gerar `start` e ao emitir primeiro `token`.
  - Se `timeout_seconds` ou `DEFAULT_TIMEOUT_SECONDS` for excedido antes do primeiro token: emitir `event: error` com `code: "TTFTTimeout"`.
  - Timeout total: do início ao `done`; se excedido, emitir `event: error` com `code: "TotalTimeout"`.
- Logging detalhado (structlog): registrar `trace_id`, `conversation_id`, `role`, `priority`, `ttft_ms`, `latency_ms`, `in_tokens`, `out_tokens`, `retries`, `provider`, `model`, `outcome`.
- Heartbeat/keep‑alive:
  - Agendar envio periódico `event: heartbeat` a cada `HEARTBEAT_INTERVAL_SECONDS` quando não há tokens em curso.
  - Alternativamente, comentar SSE (`:\n\n`) para compatibilidade com proxies.

### 2) Circuit Breakers
- Implementar CB por `provider` no `ChatService` (estado `closed/open/half_open`):
  - Parâmetros: `FAILURE_THRESHOLD`, `COOLDOWN_SECONDS`, `HALF_OPEN_TRIALS`.
  - Ao erro em `_llm.invoke_llm`, incrementar falhas; se `>= THRESHOLD`, abrir.
  - Em `open`, bloquear invocações e emitir `event: error` com `code: "CircuitOpen"`.
  - Após `COOLDOWN_SECONDS`, permitir `HALF_OPEN_TRIALS`; fechar se sucesso.
- Métricas: contabilizar transições e contagens (`CHAT_LATENCY_SECONDS`, `CHAT_TOKENS_TOTAL`, `CHAT_SPEND_USD_TOTAL`).

### 3) Padronização SSE
- Eventos obrigatórios:
  - `event: token` → payload `{ text, index?, timestamp }`
  - `event: done` → payload `{ conversation_id, provider, model, total_tokens? }`
  - `event: error` → payload `{ error, code, conversation_id?, timestamp }`
- Compatibilidade:
  - Transição suave: emitir `event: token` e, temporariamente, duplicar como `event: partial` para compatibilizar com clientes legados.
- Headers SSE e encoding:
  - `Content-Type: text/event-stream; charset=utf-8`
  - `Cache-Control: no-cache, no-transform`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no` (se atrás de Nginx)
- JSON consistente: sempre `JSON.stringify` com `ensure_ascii=False` e texto UTF‑8; escapar adequadamente quebras de linha.

### 4) CORS e Proxy `/stream/*`
- FastAPI CORS (global): `allow_origins` de env (`CORS_ALLOWED_ORIGINS`), `allow_methods=['GET','POST','PUT','DELETE']`, `allow_headers` incluindo `X-Request-ID`, `X-Conversation-Id`, `X-User-Id`.
- Validação de `Origin` por rota sensível:
  - Na SSE (`stream_message`), verificar `Origin` em `Request.headers`; se não permitido, retornar `403`.
- Cookies/segurança:
  - Se houver cookies, garantir `SameSite=strict|lax` conforme caso, `Secure` em prod, `HttpOnly` para tokens.
- Proxy dev (Angular): ajustar `proxy.conf.json` para rotear `/api` e `/api/v1/chat/stream/*` com `changeOrigin: true` e `secure: false` em dev; manter `headers` sem remover `Accept: text/event-stream`.

## Testes e Aceite
### Testes de Unidade
- `janus/tests/test_chat_service_stream.py`:
  - Tamanho máximo de mensagem: rejeita >10KB com `event: error`.
  - TTFT medição: primeiro `token` dentro do limite.
  - Heartbeat: emitido em inatividade prolongada.
  - Circuit breaker: abre após limiar, bloqueia e volta a `half_open`.
- Cobertura alvo ≥90% para `stream_message` e CB.

### Testes de Integração
- `janus/tests/test_sse_endpoint.py` com `httpx.AsyncClient`:
  - Fluxo SSE completo: `start` → `ack` → `token` → `done`.
  - Simulação de falhas (timeout, provider error) → `event: error` com `code` correto.
  - Fallback REST funcional (`/message`).
  - CRUD conversas (`/conversations`, `/{id}/rename`, `DELETE /{id}`) com dados reais.
- Carga: cenários com 100+ conexões simultâneas usando `pytest-asyncio` (tasks paralelas) ou `locust` (opcional) medindo TTFT e latência.

### Critérios de Aceitação
- TTFT < 1.5s em 99% dos casos (medido por logs e testes de carga).
- Latência P95 < 5s para mensagens completas.
- Reconexão automática com backoff (frontend já implementado) e heartbeats no backend.
- Gestão completa de histórico (já existente; validar via testes).
- Auditoria/observabilidade: logs estruturados com `trace_id` e métricas; exportáveis via endpoints existentes.

## Riscos e Mitigação
- Browsers sem SSE: manter fallback REST; detectar disponibilidade de `EventSource` no cliente.
- Timeouts longos: heartbeats a cada 30s e cancelamento do lado do cliente; `timeout_seconds` configurável.
- Contratos divergentes: validar DTOs em FastAPI/Pydantic (já presentes em `chat.py:15–71`), manter ambos eventos `token` e `partial` durante transição; documentar em Swagger/OpenAPI.
- Circuit breakers excessivamente agressivos: começar com thresholds conservadores e logar state changes para ajuste.

## Passos de Implementação
1. Introduzir config (env) e validar mensagem/timeout em `ChatService.stream_message` (refs: `janus/app/services/chat_service.py:582–739`).
2. Padronizar eventos SSE para `token/done/error`, mantendo compatibilidade com `partial` temporariamente.
3. Adicionar CB por provider no `ChatService` e integrar ao caminho de `_llm.invoke_llm`.
4. Configurar CORS global e validação de `Origin` na rota SSE `janus/app/api/v1/endpoints/chat.py:188–212`.
5. Ajustar headers SSE no `StreamingResponse` e garantir encoding UTF‑8.
6. Escrever testes unitários/integrados e um cenário de carga 100+ conexões.
7. Atualizar documentação Swagger com novos códigos e payloads.

## Observações de Compatibilidade
- Frontend atual consome `partial`; plano propõe dupla emissão `token`+`partial` inicialmente, e migração futura para `token` apenas, sem quebrar clientes existentes.
