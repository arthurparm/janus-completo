## Objetivo
Padronizar logs estruturados com campos de desempenho, adicionar métricas Prometheus (TTFT/latência/CB/erros), criar testes adicionais (CB antecipado, UTF‑8/heartbeats) e atualizar a documentação do protocolo SSE.

## Logging Estruturado
- Campos padronizados: `trace_id`, `conversation_id`, `provider`, `model`, `ttft_ms`, `latency_ms`, `retries`, `code`, `stage`.
- Pontos de emissão (structlog) em `ChatService.stream_message`:
  - start: antes de `event: start` (janus/app/services/chat_service.py:606–611) → `stage: start`, `trace_id` gerado via `uuid4()`.
  - ttft: no primeiro `event: token` (refs 615–623, 639–647, 663–676) → `stage: ttft`, `ttft_ms`.
  - done: após `event: done` (refs 699–708) → `stage: done`, `latency_ms`.
  - error: em todos os erros (`MessageTooLarge`, `TTFTTimeout`, `CircuitOpen`, `InvocationError`) → `stage: error`, `code`, `latency_ms`.
- Provider/model e retries:
  - Obter `{provider, model}` via `LLMService.select_provider(...)` (janus/app/services/llm_service.py) e, após invocação, confirmar pelo `result`.
  - `retries`: contabilizar failover interno no `LLMRepository` (incremento quando `client_fb` é usado); propagar ao log.

## Métricas Prometheus
- Definições em `janus/app/core/monitoring/chat_metrics.py`:
  - `CHAT_TTFT_MS` (summary ou histogram) com labels `provider`, `model`.
  - `CHAT_LATENCY_MS` (summary/histogram) com labels `provider`, `model`, `outcome`.
  - `CHAT_CB_STATE_CHANGES` (counter) com labels `provider`, `state` (`open|closed|half_open`).
  - `CHAT_ERRORS_TOTAL` (counter) com labels `code`.
- Instrumentação em `chat_service.py`:
  - TTFT: observar no primeiro `token` (refs 615–623, 639–647, 663–676).
  - Latência: observar no `done` e em `error`.
  - Erros: incrementar `CHAT_ERRORS_TOTAL` por `MessageTooLarge`, `TTFTTimeout`, `CircuitOpen`, `InvocationError`.
  - CB: incrementar `CHAT_CB_STATE_CHANGES` em `_cb_on_error/_cb_on_success` (janus/app/services/chat_service.py:740–769).

## Circuit Breaker Antecipado
- `LLMService.select_provider(role, priority, user_id?, project_id?)` já implementado para obter `{provider, model}` sem custo.
- `LLMService.is_provider_open(provider)` consulta estado dos circuit breakers (janus/app/services/llm_service.py).
- Em `ChatService.stream_message`, bloquear antecipadamente e emitir `event: error { code: "CircuitOpen" }` com log `stage: error` antes da invocação.

## Testes
- Unidade:
  - `janus/tests/unit/test_llm_select_and_cb.py`: mockar `LLMService.is_provider_open`=True e validar erro imediato `CircuitOpen` sem invocação de LLM; verificar log contém `stage: error`, `code`, `trace_id`.
  - `janus/tests/unit/test_chat_service_utf8_heartbeat.py`: setar `CHAT_HEARTBEAT_INTERVAL_SECONDS=1` e usar conteúdo com acentos/emoji; validar presença de `event: heartbeat` e que `token` contém UTF‑8 (ensure_ascii=False).
- Integração:
  - Ampliar `janus/tests/integration/test_chat_sse.py`: confirmar `protocol`, `token`, `heartbeat`, `done`; simular CB `open` via estado dos circuitos e validar erro imediato.
  - Opcional: teste de carga simples com múltiplas conexões em paralelo (100+) medindo TTFT/latência P95.

## Documentação
- Atualizar docstring/summary do endpoint SSE em `janus/app/api/v1/endpoints/chat.py:188–214` com:
  - Versão do protocolo atual (ex.: `2025-11.v1`).
  - Estrutura completa dos eventos: `protocol`, `ack`, `token`, `partial` (compat), `heartbeat`, `done`, `error`.
  - Data de descontinuação de `partial` (`CHAT_SSE_PARTIAL_DEPRECATE_AT`).
- Incluir exemplos de payloads no Swagger/OpenAPI (UTF‑8, códigos de erro).

## Compatibilidade e Overhead
- Mantém emissão dupla `token`+`partial` durante a migração.
- Medições e logs com baixo overhead.
- CB antecipado evita custos quando o provider está indisponível.

## Entregáveis
- Logs estruturados com chaves padronizadas.
- Métricas Prometheus novas e instrumentadas.
- Testes unitários e de integração expandindo cobertura.
- Documentação de protocolo atualizada com versão e cronograma de migração.