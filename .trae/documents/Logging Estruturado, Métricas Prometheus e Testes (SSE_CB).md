## Objetivo
Padronizar logs estruturados completos, ampliar métricas Prometheus (TTFT/latência/CB), criar testes adicionais (CB antecipado, UTF‑8/heartbeats/carga) e atualizar documentação do protocolo SSE.

## Logging Estruturado
- Padrão de chaves: `trace_id`, `conversation_id`, `provider`, `model`, `ttft_ms`, `latency_ms`, `retries`, `code` (erro), `stage` (`start|ttft|done|error`).
- Pontos de log (structlog) em `janus/app/services/chat_service.py`:
  - `start`: imediatamente antes de `event: start` (próximo de 606–611), gerar `trace_id` (`uuid4`) e persistir em variáveis locais.
  - `ttft`: no primeiro `event: token` (refs: 615–623, 639–647, 663–676); medir `ttft_ms`.
  - `done`: após `event: done` (refs: 699–708), calcular `latency_ms`.
  - `error`: em todos os ramos de erro (timeouts, circuit open, invocation error) incluir `code` e `latency_ms`.
- Garantir logs em UTF‑8 e formato JSON (structlog já configurado em `app/main.py:69` via `setup_logging`).

## Métricas Prometheus
- Definições em `janus/app/core/monitoring/chat_metrics.py`:
  - `CHAT_TTFT_MS` (summary ou histogram) com labels `provider`, `model`.
  - `CHAT_LATENCY_MS` (summary/histogram) com labels `provider`, `model`, `outcome`.
  - `CHAT_CB_STATE_CHANGES` (counter) com labels `provider`, `state` (`open|closed|half_open`).
  - `CHAT_ERRORS_TOTAL` (counter) com labels `code`.
- Instrumentação em `chat_service.py`:
  - Observar TTFT no primeiro token.
  - Observar Latência no `done`/`error`.
  - Incrementar `CHAT_ERRORS_TOTAL` com `MessageTooLarge`, `TTFTTimeout`, `CircuitOpen`, `InvocationError`.
  - Registrar transições de CB em `_cb_on_error/_cb_on_success` (janus/app/services/chat_service.py:740–769).

## Testes Adicionais
- Unidade:
  - `janus/tests/unit/test_llm_select_and_cb.py`: mockar `LLMService.is_provider_open` para `True` e validar que `stream_message` retorna `event: error { code: CircuitOpen }` imediatamente.
  - `janus/tests/unit/test_chat_service_utf8_heartbeat.py`: usar caracteres especiais e `CHAT_HEARTBEAT_INTERVAL_SECONDS=1` para verificar que `event: heartbeat` e payloads UTF‑8 aparecem.
- Integração:
  - Ampliar `janus/tests/integration/test_chat_sse.py` para cobrir coração (`heartbeat`) e caracteres especiais (Português/emoji), além de CB aberto via estado compartilhado.
  - Carga (opcional no pipeline): script com 100+ conexões simultâneas usando `pytest-asyncio` (tasks) ou `locust`, medindo TTFT e Latência P95.

## Documentação
- Atualizar descrição do endpoint SSE em `janus/app/api/v1/endpoints/chat.py` (`summary`/docstring):
  - Versão do protocolo atual (ex.: `2025-11.v1`).
  - Estrutura dos eventos: `protocol`, `ack`, `token`, `partial` (compat), `heartbeat`, `done`, `error`.
  - Data prevista para descontinuação de `partial` (`CHAT_SSE_PARTIAL_DEPRECATE_AT`).
- Atualizar Swagger com exemplos de eventos e códigos de erro.

## Compatibilidade e Overhead
- Mantém `partial` simultâneo a `token` durante transição.
- Logs e métricas são leves; TTFT/latência medidos localmente.
- CB antecipado usa seleção de provider via `LLMService.select_provider` (sem invocação), evitando custo quando bloqueado.

## Passos de Implementação
1. Inserir logs `start/ttft/done/error` com chaves padronizadas em `chat_service.py` (refs: 606–611, 615–623, 639–647, 663–676, 699–708).
2. Adicionar e usar métricas em `chat_metrics.py` e instrumentar em `chat_service.py` (ttft/latência/erros/CB).
3. Criar testes unitários e integrar casos novos (CB antecipado, UTF‑8/heartbeat).
4. Atualizar documentação Swagger/OpenAPI no endpoint SSE com versão e cronograma de descontinuação.
5. (Opcional) Adicionar painel simples no front consumindo métricas agregadas.

## Entregáveis
- Código com logs uniformes e métricas expostas.
- Suite de testes expandida.
- Documentação atualizada do protocolo SSE.
- Esboço de dashboard e instruções de uso.