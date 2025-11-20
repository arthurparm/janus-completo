## Objetivo
Padronizar o SSE no backend com payloads UTF‑8 consistentes, heartbeats de keep‑alive, transição de eventos `partial`→`token` com compatibilidade, e testes cobrindo formatação, heartbeats e versões.

## Mudanças Técnicas
- Payloads JSON: usar `json.dumps(..., ensure_ascii=False)` em todos os pontos de emissão (token/done/error/ack), garantindo UTF‑8 e evitando escapes indevidos.
- Heartbeats: emitir `event: heartbeat` com `{ timestamp }` em intervalo configurável (`CHAT_HEARTBEAT_INTERVAL_SECONDS`, 15–30s) durante períodos sem tokens (enquanto o LLM processa e entre chunks longos).
- Versão e transição: adicionar `event: protocol` com `{ version, supports_partial: true, deprecate_partial_at }` após `start/ack`; manter emissão dupla (`token` + `partial`) durante migração.
- Generator assíncrono: converter `ChatService.stream_message` para async generator e executar `_llm.invoke_llm` via `asyncio.to_thread` para permitir heartbeats enquanto aguarda resultado.
- Endpoint SSE: manter `StreamingResponse` e headers já padronizados, sem quebra de contrato.

## Implementação Detalhada
1) Atualizar `janus/app/services/chat_service.py`:
- Trocar `def stream_message(...)` por `async def stream_message(...)` e adequar retornos.
- Inserir `ensure_ascii=False` em todos `json.dumps` nos trechos: 615–623, 639–647, 663–676 e demais.
- Adicionar emissão `protocol` e lógica de heartbeats (loop com `await asyncio.sleep(interval)`).
- Manter compatibilidade com `partial` por duplicação dos `token`.
2) Ajustar `janus/app/api/v1/endpoints/chat.py`: nenhum contrato de rota muda; o `StreamingResponse` aceita async generator; manter headers padronizados.
3) Front opcional: adicionar listener `heartbeat` no cliente SSE para futura UX (não obrigatório para backend padronizado).

## Testes
- Unidade (`janus/tests/unit/test_chat_service_stream.py`):
  - Verificar formatação UTF‑8 (`ensure_ascii=False`) via caracteres especiais.
  - Verificar emissão de `heartbeat`.
  - Compatibilidade de `partial` simultâneo a `token`.
- Integração (`janus/tests/integration/test_chat_sse.py`):
  - Fluxo start→protocol→ack→token(s)→done, presença de `heartbeat`.
  - Rejeição de mensagens >10KB.

## Logs e Monitoramento
- Adicionar logs estruturados com `conversation_id`, `ttft_ms`, `latency_ms`, `provider`, `model` e contadores de heartbeats para diagnóstico.

## Compatibilidade e Riscos
- Compatível com clientes atuais (mantemos `partial`), sem mudanças de endpoint.
- Conversão para async generator sem impacto para `StreamingResponse`.
- Se `pytest` não estiver instalado no ambiente, os testes criados não serão executados automaticamente; manter scripts prontos.

## Próximos Passos
- Aplicar alterações no `ChatService` e atualizar testes.
- Opcional: adicionar listener de `heartbeat` no frontend para UX.
