---
tipo: fluxo
dominio: chat
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Conversa e Chat

## Objetivo
Descrever o fluxo real de conversa a partir do código, cobrindo REST, SSE, citações, confirmação e eventos auxiliares.

## Responsabilidades
- Cobrir `start chat`, `send message`, `history`, `study-jobs`, `trace` e SSE.
- Registrar o caminho `request -> endpoint -> service -> dependências`.
- Explicar onde entram roteamento por papel/intenção, memória, RAG, tools e pending actions.

## Entradas
- Prompt do usuário.
- Contexto de conversa e usuário.
- `role`, `priority`, `project_id`, `knowledge_space_id`.

## Saídas
- Resposta do assistente.
- `understanding`, `citation_status`, `confirmation`, `agent_state`.
- Eventos SSE `start`, `protocol`, `ack`, `cognitive_status`, `token`, `partial`, `done`, `error`.

## Dependências
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[03 - Frontend/Serviços de Integração]]

## Fluxo principal
### 1. Abrir conversa
1. `frontend/src/app/features/conversations/conversations.ts` chama `BackendApiService.startChat()`.
2. `POST /api/v1/chat/start` em `backend/app/api/v1/endpoints/chat/chat_message.py` resolve identidade com `resolve_authenticated_user_context(..., allow_anonymous_fallback=True)`.
3. `ChatService.start_conversation_async()` delega para `ConversationService.start_conversation_async()`.
4. `ConversationService` chama `ChatRepository.start_conversation(persona, user_id, project_id)`.

Observação importante:
- `ChatStartRequest` aceita `title`, mas `start_chat()` não o propaga para `ChatService`; hoje o título inicial sempre nasce do repositório como `Nova Conversa`.

### 2. Enviar mensagem via REST
1. `ConversationsComponent.sendClassic()` chama `BackendApiService.sendChatMessage()`.
2. `POST /api/v1/chat/message` resolve identidade, knowledge space ativo e papel efetivo.
3. `IntentRoutingService.resolve_role()` classifica intenção, risco e urgência antes da chamada ao serviço.
4. `ChatService.send_message()` delega para `MessageOrchestrationService.send_message()`.
5. `MessageOrchestrationService` persiste a mensagem do usuário, agenda captura em `active_memory_service` e agenda `RAGService.maybe_index_message()` para a mensagem.
6. O fluxo então segue por um dos ramos abaixo:
   - comando rápido: `ChatCommandHandler`
   - atalhos de prompt: discovery, docs, capabilities
   - criação explícita de tool
   - resposta grounded em documentos / knowledge space
   - recuperação de segredo autorizado
   - conversa geral com prompt + RAG + `ChatAgentLoop`
7. Depois da resposta, o endpoint complementa o payload com citações, `citation_status`, `understanding`, `confirmation`, `agent_state` e atualiza o último registro da mensagem do assistente.

### 3. Enviar mensagem via SSE
1. `ConversationsComponent.startStreaming()` chama `ChatStreamService.start()`.
2. `ChatStreamService` abre `GET /api/v1/chat/stream/{conversation_id}` com `fetch`, `Accept: text/event-stream`, `Authorization`, `X-User-Id`, `X-Project-Id` e `X-Request-ID`.
3. `chat_stream.py` resolve papel/intenção, valida origem, tamanho da mensagem, identidade e capacidade SSE por usuário com `acquire_sse_slot()`.
4. `ChatService.stream_message()` delega para `StreamingService.stream_message()`.
5. O stream emite:
   - `start`
   - `protocol`
   - `ack`
   - `cognitive_status`
   - `heartbeat` quando a geração demora
   - `token` e `partial`
   - `done` ou `error`
6. O frontend consome `partial` para montar a resposta incremental e usa `done` para aplicar `citations`, `understanding`, `confirmation` e `agent_state`.

### 4. Histórico, reconciliação e eventos auxiliares
- `GET /api/v1/chat/{conversation_id}/history`: `ConversationService.get_history()` retorna mensagens e reconcilia `pending_action_id` já resolvidos consultando `PendingActionRepository`.
- `GET /api/v1/chat/{conversation_id}/history/paginated`: mesmo fluxo com paginação.
- `GET /api/v1/chat/{conversation_id}/events`: `StreamingService.stream_events()` assina `janus.events` no broker e retransmite `agent_event` por SSE.
- `GET /api/v1/chat/study-jobs/{job_id}`: usado quando o REST devolve `delivery_status=pending_study`; a UI faz polling até receber `final_response`.

## REST vs SSE
### REST
- Usa `MessageOrchestrationService`.
- Pode entrar em `ChatAgentLoop` e executar tool calls via `ToolExecutorService`.
- Faz `RAGService.retrieve_context()` com decisão explícita de rota (`get_knowledge_routing_policy().resolve(...)`).
- Agenda `RAGService.maybe_index_message()` para usuário e assistente.
- Tenta `RAGService.maybe_summarize()` após certas respostas.
- Pode devolver `pending_study` e disparar `ChatStudyJobService`.

### SSE
- Também cobre grounding em documentos, knowledge space, secret recall e atalhos de prompt.
- No caminho geral chama `llm.select_provider()` e `llm.invoke_llm()` diretamente.
- Não usa `ChatAgentLoop`, não passa por `ChatCommandHandler` e não executa tools.
- Não agenda indexação RAG nem sumarização de conversa.
- Recupera contexto via `RAGService.retrieve_context()`, mas sem a política explícita usada no REST.

## Payloads relevantes
### `understanding`
- Nasce em `build_understanding_payload()` com `intent`, `summary`, `confidence` e `requires_confirmation`.
- Pode receber `routing`, `risk`, `confirmation_reason`, `confirmation` e `confidence_band`.

### `citation_status`
- É montado em `build_citation_status()`.
- Estados observados no código: `present`, `not_applicable`, `missing_required`, `retrieval_failed`.
- Quando a pergunta pede fonte rastreável e não há evidência, o fluxo pode degradar para `pending_study`, `knowledge_space_pending` ou devolver a guarda textual de citação obrigatória.

### `confirmation` e `pending actions`
- `build_confirmation_payload()` produz payload heurístico ou com origem `pending_actions_sql`.
- `maybe_create_fallback_pending_action()` cria pendência quando há risco alto, marcador legado ou `requires_confirmation`.
- Sem `user_id`, o fallback de pending action não cria registro estruturado.

### `agent_state`
- Deriva de `build_agent_state()`.
- Estados visíveis no código: `waiting_confirmation`, `low_confidence`, `completed` e estados de stream/cognição.

## Arquivos-fonte
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/chat/chat_stream.py`
- `backend/app/api/v1/endpoints/chat/chat_history.py`
- `backend/app/api/v1/endpoints/chat/chat_study_jobs.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat/conversation_service.py`
- `backend/app/services/chat/chat_contracts.py`
- `backend/app/services/chat_agent_loop.py`
- `backend/app/services/intent_routing_service.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[04 - Fluxos End-to-End/Login e Identidade]]

## Riscos/Lacunas
- REST e SSE não são equivalentes: o REST passa por `ChatAgentLoop` e tools; o SSE não.
- `ChatStartRequest.title` existe no contrato, mas não chega ao repositório.
- `ChatStudyJobService` mantém jobs em memória no `app.state`; reinício do processo perde o estado de polling.
- `GET /events` depende de broker ativo; se a autenticação estrita for ligada, o `EventSource` atual do frontend não envia `Authorization`.
- O chat concentra identidade, RAG, memória, citações, pending actions e broker; incidentes aparecem para a UI como falhas genéricas de conversa.
