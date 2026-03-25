---
tipo: dominio
dominio: frontend
camada: integracao
fonte-de-verdade: codigo
status: ativo
---

# Serviços de Integração

## Objetivo
Mapear como a UI de conversa consome o backend de chat na prática.

## Responsabilidades
- Explicar os serviços de fronteira.
- Destacar quem centraliza contratos e quem orquestra subfluxos de conversa.

## Entradas
- `frontend/src/app/services/*.ts`

## Saídas
- Mapa frontend -> backend.

## Dependências
- [[02 - Backend/API por Bounded Context]]
- [[03 - Frontend/Features e Experiência]]

## Serviços principais
- `backend-api.service`: client central com contratos extensos do backend.
- `chat-stream.service`: streaming SSE para conversa.
- `response-time-estimator.service`: estimativa de espera percebida.
- `conversation-refresh.service`: refresco de contexto de conversa.
- `agent-events.service`: EventSource separado para eventos de agentes.

## Leitura operacional
- `ConversationsComponent` escolhe entre REST e SSE com `streamingEnabled()`.
- `BackendApiService` cobre:
  - `startChat() -> POST /api/v1/chat/start`
  - `sendChatMessage() -> POST /api/v1/chat/message`
  - `getChatHistory()` e `getChatHistoryPaginated()`
  - `getChatStudyJob()` para polling de `pending_study`
  - no domínio de tools, `getTools()`, `getToolDetails()`, `getToolStats()`, `getToolCategories()`, `getToolPermissions()`, `listPendingActions()`, `approvePendingAction()` e `rejectPendingAction()`
- A feature `/tools` consome catálogo, estatísticas, auditoria e pending actions, mas não executa tool no browser.
- `ChatStreamService` usa `fetch` em vez de `EventSource` para poder enviar headers de auth no SSE principal.
- O stream principal interpreta `partial`, `done`, `error`, `cognitive_status` e aceita `token` como alias legado de `partial`.
- `AgentEventsService` usa `EventSource` puro em `/api/v1/chat/{conversationId}/events`, sem headers customizados.
- A própria feature reconcilia pending actions resolvidas tanto pelo payload estruturado quanto por mensagens `system` no histórico.

## Mapa por responsabilidade
### `BackendApiService`
- É o contrato HTTP do cockpit de conversa.
- Normaliza payloads de histórico/lista para a forma que a feature consegue renderizar.
- Expõe dois grupos que se misturam na tela de conversa:
  - chat puro
  - contexto lateral e ações operacionais, como documentos, memória, feedback e pending actions

### `ChatStreamService`
- Faz o SSE principal de resposta.
- Controla retry exponencial, parse de SSE, fallback entre `token` e `partial`, status de conexão e TTFT do ponto de vista da UI.
- É o único canal de conversa que transporta `Authorization`, `X-User-Id`, `X-Project-Id`, `X-Request-ID` e `traceparent`.

### `AgentEventsService`
- É um segundo stream, separado do stream de resposta.
- Existe para exibir eventos publicados pelo backend no broker, não para transportar a resposta do assistente.
- Usa `EventSource`, então depende mais do contexto autenticado do browser e do `user_id` em query string.

## Assimetrias importantes do frontend
- `getChatHistoryPaginated()` chama o endpoint `/history` com query params, não o endpoint `/history/paginated`; o nome do método frontend é mais amplo que o endpoint efetivamente usado.
- `startChat()` aceita `title`, mas o backend atual não preserva esse valor na criação da conversa.
- A tela usa SSE por padrão, então a experiência padrão do operador cai no caminho menos capaz do backend em comparação com o REST.
- O estado de confirmação visível depende de `pending_action_id` ou endpoints; `requires_confirmation=true` sozinho não vira CTA na tela.
- O histórico é reconciliado duas vezes:
  - no backend via status de pending action
  - no frontend via mensagens `system`

## Payloads que a UI realmente espera
- Para resposta final:
  - `response`
  - `conversation_id`
  - `message_id`
  - `citations`
  - `citation_status`
  - `understanding`
  - `confirmation`
  - `agent_state`
  - `delivery_status`
  - `failure_classification`
  - `provider`
  - `model`
- Para SSE:
  - `partial` ou `token`
  - `done`
  - `error`
  - `cognitive_status`
  - `tool_status`
- Para eventos auxiliares:
  - `agent_event`

## Relação com o fluxo de chat
- A feature `conversations` não é apenas chat.
- Ela também orquestra:
  - criação de conversa
  - histórico
  - HUD de streaming
  - eventos de agentes
  - feedback
  - aprovação/rejeição de pending actions
  - documentos da conversa
  - memória lateral
  - trace
- A nota [[04 - Fluxos End-to-End/Conversa e Chat]] descreve o comportamento end-to-end; esta nota foca no lado cliente.

## Arquivos-fonte
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/services/chat-auth-headers.util.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[03 - Frontend/Observability Frontend]]
- [[07 - Glossário e Inventários/Inventário de Endpoints]]

## Riscos/Lacunas
- `BackendApiService` segue como cliente monolítico.
- `ConversationsComponent` centraliza streaming, polling, pending actions, feedback, contexto e navegação.
- O stream principal e o stream de eventos usam tecnologias diferentes (`fetch` SSE vs `EventSource`), com superfícies de autenticação diferentes.
- A tela `/tools` opera como painel de observabilidade/aprovação, mas não cobre pending actions `langgraph` nem a execução real.
- O naming do client nem sempre espelha o endpoint real, o que dificulta leitura rápida do fluxo a partir apenas do frontend.
