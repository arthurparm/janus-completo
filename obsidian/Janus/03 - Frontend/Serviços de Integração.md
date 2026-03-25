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
- `ChatStreamService` usa `fetch` em vez de `EventSource` para poder enviar headers de auth no SSE principal.
- O stream principal interpreta `partial`, `done`, `error`, `cognitive_status` e aceita `token` como alias legado de `partial`.
- `AgentEventsService` usa `EventSource` puro em `/api/v1/chat/{conversationId}/events`, sem headers customizados.
- A própria feature reconcilia pending actions resolvidas tanto pelo payload estruturado quanto por mensagens `system` no histórico.

## Arquivos-fonte
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/chat-auth-headers.util.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[07 - Glossário e Inventários/Inventário de Endpoints]]

## Riscos/Lacunas
- `BackendApiService` segue como cliente monolítico.
- `ConversationsComponent` centraliza streaming, polling, pending actions, feedback, contexto e navegação.
- O stream principal e o stream de eventos usam tecnologias diferentes (`fetch` SSE vs `EventSource`), com superfícies de autenticação diferentes.
