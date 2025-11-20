## Visão Geral

* Integrar SSE para respostas do LLM em tempo real com reconexão resiliente.

* Padronizar contratos de API para chat (REST + SSE) e conversas (CRUD).

* Evoluir o `ChatComponent` para estados de UX claros (typing, streaming, error, reconnect) e fallback REST.

* Criar página `/conversations` para gestão de conversas (listagem, renomear, excluir, busca, paginação, ordenação).

* Instrumentar métricas de UX (TTFT, latência P95, taxas de erro) e envio para endpoint dedicado.

## Contratos de API

* SSE: `GET /api/v1/chat/stream/{conversation_id}?message=...&role=orchestrator&priority=fast_and_cheap&timeout_seconds=?` (janus/app/api/v1/endpoints/chat.py:188–212)

  * Eventos: `start`, `ack {conversation_id}`, `partial {text}`, `done {conversation_id, provider, model}`, `error {error}` (janus/app/services/chat\_service.py:593–737).

* REST:

  * `POST /api/v1/chat/start` (janus/app/api/v1/endpoints/chat.py:74–84)

  * `POST /api/v1/chat/message` (janus/app/api/v1/endpoints/chat.py:86–115)

  * `GET /api/v1/chat/{id}/history` (janus/app/api/v1/endpoints/chat.py:117–127)

  * `GET /api/v1/chat/conversations` (janus/app/api/v1/endpoints/chat.py:129–151)

  * `PUT /api/v1/chat/{id}/rename` (janus/app/api/v1/endpoints/chat.py:153–169)

  * `DELETE /api/v1/chat/{id}` (janus/app/api/v1/endpoints/chat.py:171–186)

## Serviço de Streaming (`chat-stream.service.ts`)

* Implementar cliente SSE usando `EventSource` com reconexão e backoff exponencial (jitter, limite 30s, reset em `open`).

* API pública:

  * `start(conversationId, text, role = 'orchestrator', priority = 'fast_and_cheap', timeoutSeconds?)`: inicia `EventSource` para a URL SSE; inicia cronômetros de métricas.

  * `stop()`: encerra conexão limpa e zera estados.

  * `status$`: `idle|connecting|open|streaming|retrying|closed|error`.

  * `typing$`: booleano para indicador de digitação progressiva (true durante `partial`).

  * `partials$`: Observable de chunks `{ text: string }`.

  * `done$`: evento final com `{ provider, model }`.

  * `errors$`: eventos de erro com causa e contagem de tentativas.

* Tratamento de eventos:

  * `open`: troca estado para `open`, mede TTFT a partir do primeiro `partial` subsequente.

  * `message` (default + nomeados): roteia para `ack|partial|done|error`.

  * `error`: troca estado para `error`, agenda reconexão (`retry`) respeitando backoff.

  * `retry`: evento interno para UI mostrar `reconnect`.

* Monitoramento: expor contadores de tentativas, tempo total de streaming e motivo de fechamento.

## Componente de Chat (`front/src/app/features/chat/chat/chat.ts`)

* Integração profunda com `chat-stream.service`.

* Alternância dinâmica SSE/REST via feature flag `VITE_FEATURE_SSE`.

* Estados visuais:

  * `typing`: ativo durante recepção de `partial`.

  * `streaming`: ativo após `open` até `done`/`error`.

  * `error`: exibe notificação com ação de retry.

  * `reconnect`: exibe estado durante backoff.

* UX do input:

  * `Enter`: envia; `Shift+Enter`: quebra linha.

  * Bloquear envio quando `streaming` ativo; habilitar `Cancelar` para `stop()`.

* Fluxo de envio:

  * Se `conversationId` ausente, chamar `startChat` (REST) primeiro.

  * Com SSE ativo: chamar `chat-stream.start(...)` e renderizar mensagens incrementais em `messages`.

  * Fallback REST: utilizar `JanusApiService.sendChatMessage` (front/src/app/services/janus-api.service.ts:425–427).

* Pontos de alteração existentes:

  * Método `sendMessage` (front/src/app/features/chat/chat/chat.ts:97–126) passa a delegar a SSE/REST conforme flag.

  * Preservar histórico via `getChatHistory` (front/src/app/features/chat/chat/chat.ts:81–95).

## Página de Gestão de Conversas (`/conversations`)

* Novo componente standalone `ConversationsComponent` em `front/src/app/features/chat/conversations/`.

* Rota: adicionar `path: 'conversations'` em `front/src/app/app.routes.ts` dentro de `MainLayout`.

* Funcionalidades:

  * Listagem com `JanusApiService.listConversations` (front/src/app/services/janus-api.service.ts:433–435).

  * Renomear: adicionar método `renameConversation(id, newTitle)` → `PUT /api/v1/chat/{id}/rename`.

  * Excluir: adicionar método `deleteConversation(id)` → `DELETE /api/v1/chat/{id}`.

  * Busca full‑text por título/conteúdo (client-side, simples `includes` sobre `title` e `last_message.text`).

  * Paginação client-side (page size configurável) e ordenação por `updated_at` (desc) com alternância.

  * Confirmação para ações destrutivas; feedback de sucesso/erro.

## Sistema de Métricas de UX

* Métricas coletadas:

  * TTFT: tempo do `start()` ao primeiro `partial`.

  * Latência total por requisição: `start()` ao `done`/`error`.

  * Taxas de erro por tipo (conexão SSE, HTTP 4xx/5xx, cancelamento).

  * P95/P50/P99 calculados localmente por janela deslizante (ex.: últimas 500 interações).

* Instrumentação:

  * Serviço `ux-metrics.service.ts` com buffer, agregação e exportação.

  * Emissão para endpoint dedicado `POST /api/v1/observability/metrics/ux` (proposta de contrato: `{ ttft_ms, latency_ms, outcome, provider?, model?, retries, timestamp }`).

  * Logs estruturados (console) com `trace_id` e metadados (`conversation_id`, tentativas, flags).

  * Amostragem configurável (ex.: 0.3) via `VITE_UX_METRICS_SAMPLING`.

* Dashboard:

  * Componente simples `UxDashboardComponent` lendo do `ux-metrics.service` para visualização (tabelas/indicadores sem libs adicionais).

## Feature Flags

* Ambientais via `import.meta.env`:

  * `VITE_FEATURE_SSE` (default `true`).

  * `VITE_UX_METRICS_SAMPLING` (default `0.3`).

  * `VITE_SSE_RETRY_MAX_SECONDS` (default `30`).

* Hook no bootstrap para ler flags e disponibilizar em `InjectionToken`.

## Integração e Testes

* Testes unitários:

  * `chat-stream.service`: reconexão, parsing de eventos, cálculo de TTFT/latência.

  * `ChatComponent`: alternância SSE/REST, bloqueios de UI, atalhos de teclado.

  * `ConversationsComponent`: paginação, ordenação, rename/delete com confirmação.

* Testes end‑to‑end (mínimo): fluxo completo de envio com SSE e fallback REST; gestão de conversas CRUD.

* Verificação manual com servidor em execução e `proxy.conf.json` em dev.

## Riscos e Considerações

* Compatibilidade `EventSource`: fallback automático a REST se indisponível.

* Reconexão: mensagens duplicadas evitadas pela lógica de merge de `partials` em um buffer por interação.

* Observabilidade backend: caso o endpoint de UX não exista, manter buffer local e logs até disponibilização.

* Segurança: não logar tokens/segredos; cabeçalhos contextuais já tratados em `JanusApiService.headersFor` (front/src/app/services/janus-api.service.ts:148–155).

## Próximos Passos

* Aprovar plano e contratos propostos.

* Implementar `chat-stream.service` e integrar no `ChatComponent`.

* Adicionar rota `/conversations` e CRUD no `JanusApiService`.

* Instrumentar métricas e construir dashboard básico.

