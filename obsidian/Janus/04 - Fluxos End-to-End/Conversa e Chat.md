---
tipo: fluxo
dominio: chat
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Conversa e Chat

## Objetivo
Reconstruir o fluxo real de conversa do Janus a partir do código, ligando UI Angular, serviços frontend, endpoints FastAPI, orquestração interna, memória/RAG, SSE, citações e confirmações.

## Responsabilidades
- Cobrir `start chat`, envio de mensagem, histórico, trace, eventos de agente e polling de study job.
- Explicar o caminho `UI -> client frontend -> endpoint -> service -> repositório/dependências`.
- Separar o que acontece em REST do que acontece em SSE.
- Explicitar onde entram role routing, memória ativa, RAG, grounding documental, citações, pending actions e fallback de estudo.

## Entradas
- Texto do usuário.
- `conversation_id`.
- `role`, `priority`, `timeout_seconds`.
- `user_id`, `project_id`, `knowledge_space_id`.
- Histórico recente da conversa.
- Contexto vetorial recuperado por Qdrant.
- Manifests documentais da conversa.

## Saídas
- Resposta textual do assistente.
- Metadados persistidos por mensagem:
  - `citations`
  - `citation_status`
  - `understanding`
  - `confirmation`
  - `agent_state`
  - `delivery_status`
  - `failure_classification`
  - `provider`
  - `model`
- Eventos SSE:
  - `start`
  - `protocol`
  - `ack`
  - `cognitive_status`
  - `heartbeat`
  - `token`
  - `partial`
  - `done`
  - `error`

## Dependências
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[03 - Frontend/Serviços de Integração]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Login e Identidade]]

## Peças do fluxo
- UI principal: `frontend/src/app/features/conversations/conversations.ts`
- Cliente HTTP principal: `frontend/src/app/services/backend-api.service.ts`
- Cliente SSE de resposta: `frontend/src/app/services/chat-stream.service.ts`
- Cliente SSE de eventos de agente: `frontend/src/app/core/services/agent-events.service.ts`
- Componentes compartilhados que moldam a UX do fluxo:
  - `frontend/src/app/shared/components/jarvis-avatar/jarvis-avatar.component.ts`
  - `frontend/src/app/shared/pipes/markdown.pipe.ts`
  - `frontend/src/app/shared/components/ui/ui-badge/ui-badge.component.ts`
  - `frontend/src/app/shared/components/skeleton/skeleton.component.ts`
- Endpoints de chat: `backend/app/api/v1/endpoints/chat/chat_message.py`, `chat_stream.py`, `chat_history.py`
- Confirmações/pending actions: `backend/app/api/v1/endpoints/pending_actions.py`
- Fachada de chat: `backend/app/services/chat_service.py`
- Lógica real de conversa: `backend/app/services/chat/conversation_service.py`
- Lógica real de envio REST: `backend/app/services/chat/message_orchestration_service.py`
- Lógica real de streaming SSE: `backend/app/services/chat/streaming_service.py`
- Heurísticas de entendimento: `backend/app/services/chat/message_helpers.py`
- Roteamento por intenção/papel: `backend/app/services/intent_routing_service.py`
- Citações: `backend/app/services/chat/chat_citation_service.py`
- Contratos de confirmação/estado: `backend/app/services/chat/chat_contracts.py`
- Repositório persistente: `backend/app/repositories/chat_repository_sql.py`

## Visão ponta a ponta
1. A tela de conversas carrega a lista com `listConversations()`, sincroniza o `conversationId` da rota e, ao selecionar uma conversa, dispara em paralelo:
   - histórico via `getChatHistoryPaginated()`
   - contexto lateral via `listDocuments()` e `getMemoryTimeline()`
   - SSE de eventos de agentes via `AgentEventsService.connect(conversationId)`
   - trace opcional via `getConversationTrace(conversationId)`
2. Ao enviar mensagem, a UI faz otimistic update: adiciona a mensagem do usuário localmente antes da resposta do backend.
3. O caminho padrão da UI é SSE porque `streamingEnabled` nasce `true`. O caminho REST continua implementado e pode ser usado quando o streaming é desligado.
4. O backend persiste conversa e mensagens em SQL via `ChatRepositorySQL`.
5. O enriquecimento contextual vem majoritariamente de Qdrant via `RAGService` e `MemoryService`; o chat normal não usa Neo4j como fonte principal de prompt.

## Superfície real da tela
### Estrutura principal
- A tela não é um chat isolado; ela junta três áreas sincronizadas pelo mesmo `conversationId`:
  - coluna lateral com busca, ordenação implícita por atividade, criação e seleção de conversas
  - feed principal com mensagens, estado de stream, entendimento, confirmação, citações e feedback
  - rail avançado opcional com contexto e operações paralelas à conversa
- O modo padrão de abertura é simples (`showAdvanced=false`), mas a preferência de modo e das abas é persistida em `localStorage`.
- `JarvisAvatarComponent` reflete o estado operacional percebido pelo usuário:
  - `thinking` quando o stream está `connecting`, `retrying` ou `open`
  - `speaking` quando `streamTyping()` está ativo
  - `idle` fora do ciclo de resposta

### Subfluxos embutidos na mesma feature
- `Insights`:
  - resume a última resposta com fontes, confiança, latência, provider e model
  - mostra `thoughtStream`, alimentado tanto pelo stream principal quanto por `AgentEventsService`
  - carrega `trace` sob demanda via `getConversationTrace()`
- `Cliente`:
  - `Docs`: upload (com progresso), link por URL, busca documental e biblioteca da conversa
  - `Memória`: criação e busca de memória generativa com campo `importance` numérico opcional, além da leitura de memória da conversa e do usuário. `generativeMemoryMetaLine()` formata tipo, importância, score e timestamp do item.
  - `RAG`: execução manual de consultas fora do envio principal do chat, com visualizações `Resposta`, `Fontes` e `Raw`. Modo `productivity` faz `ragProductivitySearch` e devolve `results` (não `answer`).
- `Autonomia`:
  - consulta `status`, `goals` e `tools`
  - permite iniciar/parar o loop autônomo
  - permite criar meta e alterar status de metas ativas
- `Feedback`:
  - cada resposta final do assistente ganha thumbs up/down e comentário opcional
  - o envio vai para `api/v1/feedback/thumbs-up|thumbs-down`
  - quick prompts fixos (resumo em 5 pontos, próximos passos, explicação simples) preenchem o composer e disparam envio normal
- `Admin code QA`:
  - se o operador for admin e digitar `/code ...`, a tela desvia do fluxo normal e chama `askAutonomyAdminCodeQa()`
  - o parsing do comando `/code` é isolado em `admin-code-qa.util.ts` via `parseAdminCodeQaCommand()`
  - reconciliação local de pending actions via regex `a[cç][aã]o pendente #(\d+) (aprovada|rejeitada)` em `reconcileResolvedPendingActions()` (detecta resoluções via mensagem de sistema)

### Onde a tela concentra complexidade
- A mesma classe coordena:
  - histórico otimista de mensagens
  - SSE principal
  - SSE de eventos de agente
  - polling de `study_job`
  - reconciliação local de pending actions resolvidas
  - refresh de documentos, memória e autonomia
  - persistência de preferências de visualização
- O componente não é só renderização; ele funciona como orquestrador de estado da feature.

## Persistência por camada no chat
- Postgres:
  - conversa, mensagens e metadados estruturados do turno
  - pending actions resolvidas e reconciliação do histórico
  - manifests usados para detectar grounding documental e `knowledge_space_id` ativo
- Qdrant:
  - `user_chat_<user_id>` para contexto episódico
  - `user_docs_<user_id>` para citações documentais e grounding
  - `user_memory_<user_id>` e `user_secret_<user_id>` para preferências, regras e segredos
- Neo4j:
  - não participa do caminho normal do prompt do chat
  - entra em fluxos de study/code QA e conhecimento estrutural
- Redis:
  - não persiste o chat, mas pode interferir em rate limit e quotas temporárias de tools

## Fluxo resumido por decisão
1. A UI cria ou reutiliza a conversa.
2. A UI adiciona a mensagem do usuário localmente.
3. O backend valida identidade e acesso.
4. O backend tenta resolver `knowledge_space_id` ativo.
5. O backend classifica intenção, risco e urgência para decidir papel efetivo.
6. O backend persiste a mensagem do usuário.
7. O backend entra em um branch:
   - comando
   - atalhos de prompt
   - grounding documental
   - knowledge space
   - secret recall
   - fluxo geral de LLM
8. O backend complementa o resultado com citações, confirmação e estado do agente.
9. A UI atualiza a mensagem do assistente e o preview da conversa.

## 1. Start conversation
1. `ConversationsComponent.ensureConversationId()` chama `BackendApiService.startChat(undefined, undefined, userId)`.
2. `BackendApiService.startChat()` envia `POST /api/v1/chat/start`.
3. `chat_message.start_chat()` resolve identidade com `resolve_authenticated_user_context(..., allow_anonymous_fallback=True)`.
4. Em modo de transição, o backend aceita ator autenticado, `user_id` explícito, `X-User-Id` ou fallback anônimo derivado de `client_ip + user-agent`.
5. `ChatService.start_conversation_async()` delega para `ConversationService.start_conversation_async()`.
6. `ConversationService.start_conversation()` chama `ChatRepository.start_conversation(persona, user_id, project_id)`.
7. Em `ChatRepositorySQL.start_conversation()`, a sessão nasce com `title or "Nova Conversa"`.
8. O contrato HTTP de saída é mínimo: `ChatStartResponse` devolve apenas `conversation_id`.

Ponto importante:
- `ChatStartRequest` aceita `title`, o frontend envia esse campo, o repositório suporta `title`, mas `chat_message.start_chat()` não propaga `title` para `ChatService`. Na prática, a conversa nasce sempre com o título padrão do repositório.

## 2. Envio pela UI
1. `ConversationsComponent.sendMessage()` impede reentrada com `sending()`, valida texto, garante `conversationId`, adiciona a mensagem do usuário ao estado local e atualiza o preview da conversa.
2. O papel padrão da UI é `orchestrator`.
3. A prioridade padrão da UI é `fast_and_cheap`.
4. Se `streamingEnabled()` estiver `true`, a UI chama `startStreaming(conversationId, message)`.
5. Se `streamingEnabled()` estiver `false`, a UI chama `sendClassic(conversationId, message)`.
6. Em ambos os caminhos, a UI mede latência local, atualiza preview, reconcilia citações/confirmation/agent_state no estado local e mantém um thought stream separado para diagnóstico.

### Estado local relevante da UI
- `messages`: histórico renderizado.
- `streamStatus`: `idle`, `connecting`, `open`, `streaming`, `retrying`, `closed`, `error`.
- `streamTyping`: indicador visual de geração.
- `thoughtStream`: trilha textual de status, cognitive events e agent events.
- `selectedRole`: papel pedido pelo operador.
- `selectedPriority`: prioridade pedida pelo operador.
- `streamingEnabled`: chave de escolha entre SSE e REST.
- `pendingActionLoading`: mapa de aprovação/rejeição em andamento.
- `showAdvanced`, `advancedRailTab`, `customerTab`: controlam a topologia da própria tela, não apenas detalhes cosméticos.
- `docs`, `memoryUser`, `generativeMemoryResults`, `ragResult`: mantêm o contexto lateral sincronizado com a conversa ativa.
- `feedbackStateByMessageId` e `feedbackCommentDraftByMessageId`: isolam feedback por resposta do assistente.
- `autonomyStatus`, `autonomyGoals`, `autonomyTools`: mantêm um mini-painel operacional dentro da conversa.

## 3. Caminho REST real
1. `sendClassic()` chama `BackendApiService.sendChatMessage(conversation_id, content, role, priority, ...)`.
2. O endpoint é `POST /api/v1/chat/message`.
3. `chat_message.send_message()` resolve identidade com `allow_anonymous_fallback=True`.
4. Se houver `knowledge_space_id` explícito ou inferido pelos manifests da conversa, `service.resolve_active_knowledge_space_id()` devolve o id ativo.
5. O endpoint chama `IntentRoutingService.resolve_role(payload.role, payload.message)`.

### Regras reais de routing
- Se o papel pedido for `auto`, o serviço pode escolher outro papel conforme intenção, risco e urgência.
- Se o papel pedido for `orchestrator`, o serviço ainda pode sobrescrever para outro papel quando a confiança do classificador for alta.
- Se o papel pedido for explicitamente `reasoner`, `code_generator`, `knowledge_curator` ou `security_auditor`, o routing não troca o papel; ele só registra a decisão.
- Se existir `knowledge_space_id` ativo, o endpoint força `ModelRole.ORCHESTRATOR` e zera `route_applied`.

### Sequência real dentro de `MessageOrchestrationService.send_message()`
1. Carrega a conversa do repositório e valida acesso por `user_id` e `project_id`.
2. Valida tamanho da mensagem contra `CHAT_MAX_MESSAGE_BYTES`.
3. Gera `understanding` heurístico com `build_understanding_payload()`.
4. `ChatService` não concentra lógica aqui: ele só delega para `MessageOrchestrationService`, que é onde o branch real é decidido.
5. Decide `use_light_chat` somente quando:
   - `role == ORCHESTRATOR`
   - `intent in {"general", "question"}`
   - mensagem tem até `CHAT_LIGHT_MAX_MESSAGE_CHARS` caracteres
6. Persiste a mensagem do usuário em SQL.
7. Agenda captura em memória ativa com `active_memory_service.maybe_capture_from_message()`.
8. Agenda indexação RAG do turno do usuário com `RAGService.maybe_index_message()`, que grava em `user_chat_<user_id>` via `MemoryService.index_interaction()`.
9. Segue por esta ordem de branches:
   - comando via `ChatCommandHandler`
   - intro de discovery
   - documentação de tools
   - capabilities locais
   - criação explícita de ferramenta
   - grounding documental / knowledge space
   - secret recall autorizado
   - fluxo geral de chat

### Mapa real de branches no REST
- `is_command(message)`: resposta curta e síncrona, sem fluxo geral de chat.
- `is_discovery_query(message)`: introdução/catálogo.
- `is_docs_query(message)`: documentação de ferramentas.
- `is_capabilities_query(message)`: capabilities locais.
- `is_tool_request(message) and is_explicit_tool_creation(message)`: tentativa de evolução/criação de tool.
- `generate_document_grounded_reply(...)`: domina a conversa se houver manifests documentais ou knowledge space resolvível.
- `generate_secret_recall_reply(...)`: recall explícito de segredo autorizado.
- `fluxo geral`: prompt completo + RAG + `invoke_llm()` leve ou `ChatAgentLoop.run_loop()`.

### Grounding documental e knowledge space no REST
1. `generate_document_grounded_reply()` consulta manifests da conversa.
2. Se um `knowledge_space_id` puder ser resolvido, `_generate_knowledge_space_reply()` roda primeiro e domina o fluxo.
3. Se não houver knowledge space resolvível, `_should_use_document_grounding()` decide se entra grounding documental.
4. No estado atual do código, `_should_use_document_grounding()` retorna `True` para qualquer conversa que tenha manifests. Na prática, basta existir documento vinculado para esse caminho dominar todas as mensagens daquela conversa.
5. Se os manifests ainda estiverem `queued` ou `processing`, o retorno é `document_processing`.
6. Se já houver chunks indexados, o serviço coleta citações em `user_docs_<user_id>` e monta resposta grounded estrita.
7. Se não houver evidência suficiente, o retorno vem com `citation_status` coerente e resposta de ausência de evidência.

### Fluxo geral de chat no REST
1. O serviço lê `history = get_recent_messages(conversation_id, limit=60)`.
2. Se existir `RAGService` e o fluxo não for light chat, resolve `knowledge_route = get_knowledge_routing_policy().resolve(RouteIntent.CHAT_CONTEXT_RETRIEVAL, include_graph=False, ...)`.
3. `RAGService.retrieve_context()` consulta:
   - memória episódica em `user_chat_<user_id>`
   - preferências/semântica
   - memória procedural
   - segredos autorizados
   - contexto documental leve da conversa quando a mensagem referencia material enviado
4. O prompt final é montado por `PromptBuilderService.build_prompt(persona, history, message, summary, relevant_memories)`.
5. Se `use_light_chat` for `True`, a resposta vem de `llm.invoke_llm()`.
6. Caso contrário, a resposta vem de `ChatAgentLoop.run_loop()`.

### Persistência real do turno no REST
- Mensagem do usuário:
  - sempre vira linha SQL de `Message`
  - pode ser capturada por `active_memory_service`
  - pode ser indexada em `user_chat_<user_id>`
- Mensagem do assistente:
  - sempre vira linha SQL
  - pode ser indexada em `user_chat_<user_id>`
  - recebe patch posterior com `citations`, `understanding`, `confirmation`, `agent_state` e estado de delivery

### O que o `ChatAgentLoop` realmente faz
- Publica eventos de raciocínio e tool call no event bus.
- Executa loop de até `max_iterations`.
- Aplica policy engine de risco e content safety.
- Faz fallback de LLM.
- Detecta tool calls, executa ferramentas e reitera o prompt com outputs.
- Pode produzir resposta final com `pending_action_id` embutido em texto ou via heurística posterior.

### Pós-processamento REST
1. A resposta passa por `apply_response_memory_policies()`.
2. O assistente é persistido em SQL.
3. O turno do assistente é indexado em Qdrant com `maybe_index_message()`.
4. O serviço tenta `maybe_summarize()` quando a conversa cresce.
5. `trigger_post_response_events()` publica payload de consolidação assíncrona no outbox ou direto no worker.
6. O endpoint completa o payload final com:
   - `citations`
   - `citation_status`
   - `understanding`
   - `confirmation`
   - `agent_state`
   - `delivery_status`
   - `failure_classification`
7. O endpoint busca a última mensagem do assistente e faz `update_message_payload()` para persistir metadados estruturados na linha SQL já gravada.

### Contrato de payload do REST
- `response`: texto final já sanitizado para UI.
- `conversation_id`: sempre presente.
- `message_id`: só existe quando o endpoint conseguiu localizar e atualizar a última mensagem do assistente.
- `citations` e `citation_status`: podem nascer no service ou ser recalculados no endpoint.
- `understanding`: nasce heurístico e depois pode ganhar:
  - `confidence_band`
  - `low_confidence`
  - `routing`
  - `risk`
  - `confirmation`
- `confirmation`: só aparece quando existe razão válida ou pending action estruturada.
- `agent_state`: deriva de `confirmation`, `understanding` e fase do fluxo.
- `delivery_status` e `failure_classification`: aparecem principalmente quando o endpoint converte a resposta em placeholder de `pending_knowledge_space` ou `pending_study`.
- `study_job` e `study_notice`: aparecem só no fallback assíncrono do REST.
- `knowledge_space_id`: pode voltar no payload final quando a conversa entra no ramo documental/knowledge space.

## 4. Caminho SSE real
1. `startStreaming()` cria uma mensagem local vazia do assistente e chama `ChatStreamService.start()`.
2. `ChatStreamService.start()` monta `GET /api/v1/chat/stream/{conversation_id}?message=...&role=...&priority=...`.
3. O cliente usa `fetch`, não `EventSource`, para poder enviar:
   - `Authorization: Bearer ...`
   - `X-User-Id`
   - `X-Project-Id`
   - `X-Request-ID`
   - `traceparent`
4. `chat_stream.stream_message()`:
   - resolve role/priority
   - valida origem com `ensure_origin_allowed()`
   - valida tamanho da mensagem
   - resolve identidade sem fallback anônimo
   - valida acesso à conversa
   - reserva capacidade com `acquire_sse_slot(user, channel="chat_stream")`
5. `StreamingService.stream_message()` emite, nesta ordem:
   - `start`
   - `protocol`
   - persistência da mensagem do usuário em SQL
   - `ack`
   - `cognitive_status`
   - zero ou mais `heartbeat`
   - `token` e `partial`
   - `done` ou `error`

### Handshake real do SSE
- O request do stream principal carrega auth e tracing em headers.
- O endpoint responde com:
  - `Content-Type: text/event-stream; charset=utf-8`
  - `Cache-Control: no-cache, no-transform`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- O backend controla slots por usuário e por canal:
  - `chat_stream`
  - `agent_events`

### Contrato real de eventos SSE
- `protocol` anuncia `version`, `supports_partial` e `deprecate_partial_at`.
- O cliente aceita `token` e `partial`, mas normaliza ambos para o mesmo canal incremental.
- `ChatStreamService` adota o primeiro modo recebido e ignora mistura posterior.
- `done` carrega o payload final com `message_id`, `citations`, `citation_status`, `understanding`, `confirmation` e `agent_state`.
- `error` carrega erro estruturado com `code`, `category`, `retryable` e `http_status`.
- `heartbeat` mantém a conexão viva enquanto a invocação principal ainda não terminou.
- `tool_status`: o cliente implementa parsing e estado local para esse evento, mas o backend do stream principal não emite `event: tool_status` no estado atual (apesar de existir no contrato documental).

### Sequência real interna do SSE
1. O stream tenta `generate_document_grounded_reply()` antes do fluxo geral.
2. Se houver grounding/knowledge space, o stream responde por esse ramo e encerra.
3. Se não houver, tenta `generate_secret_recall_reply()`.
4. Se também não houver, monta `history` e `relevant_memories` via `RAGService.retrieve_context()`.
5. Depois disso processa discovery/docs/capabilities.
6. No fluxo geral, o stream chama `llm.select_provider()` e `llm.invoke_llm()` diretamente.
7. O SSE não chama `ChatAgentLoop.run_loop()`.
8. O SSE não executa tools.
9. O SSE não agenda `RAGService.maybe_index_message()` nem para a mensagem do usuário nem para a do assistente.
10. O SSE não chama `RAGService.maybe_summarize()`.

### Mapa real de branches no SSE
- grounding documental / knowledge space
- secret recall
- discovery
- docs
- capabilities
- fluxo geral com `select_provider()` + `invoke_llm()`

### Persistência real do turno no SSE
- A mensagem do usuário sempre é persistida em SQL antes do fluxo principal.
- A mensagem do assistente é persistida em SQL no final do branch escolhido.
- O SSE persiste metadados estruturados no `add_message(..., metadata=...)` do assistente.
- O SSE não faz patch posterior equivalente ao REST; ele já grava a mensagem final com metadata no momento da persistência do assistente.

Consequência prática:
- O caminho padrão da UI é SSE, mas o pipeline que alimenta `user_chat_<user_id>` para RAG contextual só existe no REST. Se a conversa roda majoritariamente em SSE, o histórico SQL cresce, a memória ativa ainda pode capturar sinais do usuário, mas a memória vetorial episódica do chat pode ficar desatualizada.

## Impacto de falha por store no fluxo de chat
- Postgres falha:
  - o fluxo perde conversa persistida, histórico, pending actions e reconciliação de mensagens
- Qdrant falha:
  - o fluxo ainda pode responder com LLM, mas perde contexto, citações documentais e indexação vetorial do chat
- Neo4j falha:
  - o chat comum pouco sente; os efeitos aparecem em study/code QA e conhecimentos estruturais
- Redis falha:
  - afeta controle de tráfego e quotas temporárias, não o conteúdo persistido da conversa

## 5. Citações, memory e RAG

### Memória e RAG usados no chat
- `RAGService.retrieve_context()` usa Qdrant e retorna string já consolidada para o prompt.
- O retrieve do chat normal pede `include_graph=False`; o caminho normal não usa Neo4j como base de contexto.
- `MemoryService.index_interaction()` grava interações em `user_chat_<user_id>` com `memory_class=episodic`, `scope=session` e `conversation_id=session_id`.
- Quando a mensagem cita arquivo/anexo/documento, `RAGService` ainda tenta anexar contexto documental leve da conversa.

### Citações
1. `collect_chat_citations()` combina:
   - citações documentais em `user_docs_<user_id>`
   - hits de memória via `MemoryService.recall_filtered()` quando disponíveis
2. `build_citation_status()` classifica o retorno como:
   - `present`
   - `not_applicable`
   - `missing_required`
   - `retrieval_failed`
3. Quando a pergunta exige evidência rastreável e o status fica `missing_required`, REST e SSE divergem.

### O que conta como citação no chat
- Documento:
  - `doc_id`
  - `file_path` ou `title`
  - `snippet`
  - `line_start` / `line_end` quando aplicável
- Código no fallback de study:
  - `file_path`
  - linhas
  - snippet
- Memória:
  - fragmentos de conteúdo de `recall_filtered()`

### Divergência real REST x SSE para `missing_required`
- REST:
  - se houver knowledge space ativo, converte a última mensagem do assistente em placeholder `pending_knowledge_space`
  - se não houver, converte a mensagem em placeholder `pending_study`, cria `ChatStudyJob` e devolve `study_job` para polling
- SSE:
  - se houver knowledge space ativo, troca a resposta inline para `knowledge_space_pending`
  - se não houver, roda `ChatStudyService.answer_with_study()` dentro do próprio stream, emitindo `cognitive_status` de progresso e só depois conclui com `done`

### `ChatStudyService`
- Primeiro tenta `knowledge.ask_code_with_citations()` se `knowledge_service` existir.
- Depois tenta citações documentais da conversa.
- Se falhar, executa self-study opcional com `autonomy_admin_service.run_self_study()`.
- Em seguida escaneia o repositório local e sintetiza resposta com citações de arquivo/linha.
- Esse caminho é fallback de estudo, não o caminho normal do chat.

## 6. Confirmations e pending actions
1. `build_understanding_payload()` já pode marcar `requires_confirmation` para intenções como `action_request` e `reminder`.
2. O endpoint REST reforça confirmação por baixa confiança:
   - calcula `confidence_band`
   - seta `low_confidence`
   - para baixa confiança em ações/lembretes, muda a resposta para um pedido explícito de confirmação
3. REST e SSE reforçam confirmação por risco alto vindo de `IntentRoutingService`.
4. `maybe_create_fallback_pending_action()` cria pendência SQL quando:
   - já não existe `pending_action_id`
   - existe `user_id`
   - há `requires_confirmation`
   - e há sinal forte de alto risco ou marcador legado
5. Quando há `pending_action_id`, `build_confirmation_payload()` devolve endpoints SQL:
   - `/api/v1/pending_actions/action/{id}/approve`
   - `/api/v1/pending_actions/action/{id}/reject`
6. `normalize_understanding_payload()` injeta `confirmation` em `understanding`, normaliza `confirmation_reason` e deriva `risk`.
7. `build_agent_state()` devolve:
   - `waiting_confirmation`
   - `low_confidence`
   - ou o estado de stream/completed

### Fontes reais de confirmação
- heurística de intenção em `build_understanding_payload()`
- baixa confiança no endpoint REST
- risco alto vindo de `IntentRoutingService`
- pending action explícita vinda de tools ou marcador legado no texto
- fallback SQL criado por `maybe_create_fallback_pending_action()`

Ponto importante:
- o reforço por baixa confiança não existe no pipeline SSE; no stream principal, confirmação adicional entra por risco alto, marcador de pending action ou fallback heurístico em `chat_contracts.py`.

### Como a UI trata confirmação
- A UI só considera uma mensagem “acionável” se `confirmation` tiver `pending_action_id` ou endpoints.
- Confirmações heurísticas sem `pending_action_id` existem no backend, mas `messageConfirmation()` devolve `null` nesse caso.
- Resultado prático: o backend pode marcar `requires_confirmation`, porém a UI só mostra botões de aprovar/rejeitar quando existe pendência estruturada.
- Quando o backend só marca `understanding.low_confidence`, a UI não abre botões de aprovação; ela apenas mostra o card “Entendi assim” com CTA para preencher o composer com uma frase de confirmação.

### Aprovação/rejeição
1. `approvePendingActionForMessage()` e `rejectPendingActionForMessage()` chamam `BackendApiService.approvePendingAction()` ou `rejectPendingAction()`.
2. Para o chat normal, isso usa o ramo SQL `/api/v1/pending_actions/action/{action_id}/approve|reject`.
3. O endpoint muda o status em `PendingActionRepository`.
4. `_sync_chat_confirmation_for_action()` percorre o histórico SQL da conversa e faz `update_message_payload()` na mensagem do assistente correspondente.
5. `ConversationService.get_history()` ainda reconcilia pendências resolvidas ao carregar o histórico.
6. A UI faz uma segunda reconciliação local lendo mensagens de sistema do tipo `Ação pendente #N aprovada/rejeitada`.

## 6.5 Feedback da resposta
1. O bloco de feedback só aparece para mensagens do assistente que já terminaram de streamar.
2. `submitFeedback()` usa `conversation_id` da conversa ativa e prefere `backendMessageId`; se ele não existir, faz fallback para o `id` local da mensagem.
3. O comentário é opcional e fica separado por mensagem em `feedbackCommentDraftByMessageId`.
4. O backend é chamado por:
   - `POST /api/v1/feedback/thumbs-up`
   - `POST /api/v1/feedback/thumbs-down`
5. A UI trava reenvio enquanto `submitting=true` e, após sucesso, muda o bloco para estado de confirmação com a mensagem retornada pelo servidor.

Ponto importante:
- O feedback pertence à resposta específica, não à conversa como um todo; por isso o componente guarda estado por `message.id`.

## 7. Histórico, eventos e trace

### Histórico
- `loadHistory()` usa `getChatHistoryPaginated(conversationId, { limit: 80, offset: 0 })`.
- Apesar do nome do método frontend, ele chama `/api/v1/chat/{conversation_id}/history?limit=...`, não `/history/paginated`.
- O backend converte cada mensagem para `ChatMessage` preservando `citations`, `citation_status`, `understanding`, `confirmation`, `agent_state`, `delivery_status`, `provider` e `model`.

### Reconciliação de histórico
- Backend:
  - `ConversationService.get_history()` reconcilia mensagens que apontam para `pending_action_id` já resolvidos.
- Frontend:
  - `reconcileResolvedPendingActions()` também tenta detectar aprovações/rejeições a partir de mensagens `system`.
- Resultado:
  - o estado visual de confirmação é redundante por design, para sobreviver a inconsistências de timing entre SQL, SSE e mensagens de sistema.

### Eventos de agente
1. A UI usa um segundo canal SSE com `AgentEventsService`.
2. O endpoint é `GET /api/v1/chat/{conversation_id}/events`.
3. Esse cliente usa `EventSource`, então não consegue mandar `Authorization` customizado.
4. O serviço tenta anexar `?user_id=` na URL quando o usuário está disponível.
5. O backend:
   - valida origem
   - valida acesso à conversa
   - reserva slot `agent_events`
   - consome o broker em `janus.events` com routing key `janus.event.conversation.{conversation_id}.#`
   - retransmite como SSE `event: agent_event`
6. Esse canal mostra thought/tool events publicados pelo agent loop e por outros workers.

Ponto importante:
- O `thoughtStream` exibido ao operador é híbrido: ele mistura eventos vindos desse segundo SSE com estados internos do stream principal (`connecting`, `retrying`, `open`, `done`, `error`, `cognitive_status`).
- Como o backend resolve identidade com `allow_anonymous_fallback=False`, o endpoint pode retornar `CHAT_AUTH_REQUIRED` (401) quando `CHAT_AUTH_ENFORCE_REQUIRED=1` e o browser não tiver contexto de auth compatível com `EventSource`.

### Trace
- `GET /api/v1/chat/{conversation_id}/trace` existe e a UI carrega sob demanda.
- O trace não faz parte do fluxo de resposta normal; é observabilidade pós-fato.

## 8. Dependências externas realmente envolvidas
- SQLAlchemy/Postgres:
  - sessões e mensagens de chat
  - `pending_actions` SQL
  - checkpoints do fluxo LangGraph em pending actions não-SQL
- Qdrant:
  - `user_chat_<user_id>` para memória vetorial de chat
  - `user_docs_<user_id>` para citações documentais
- Broker de mensagens:
  - exchange `janus.events` para HUD/eventos de agentes
- Knowledge space/document manifests:
  - resolução do `knowledge_space_id` ativo por conversa
  - consultas grounded com `KnowledgeSpaceService`
- Serviços de memória:
  - active memory
  - procedural memory
  - secret memory
- Serviço de conhecimento/autonomia:
  - usados apenas em fallback de study, não no caminho normal do chat

## REST x SSE
### O que é equivalente
- validação de conversa e acesso
- role routing inicial
- grounding documental
- knowledge space
- secret recall
- `understanding`
- `confirmation`
- `agent_state`
- coleta de citações no final

### O que diverge estruturalmente
- REST:
  - pode usar `ChatAgentLoop`
  - pode executar tools
  - aplica reforço de confirmação por baixa confiança no endpoint
  - indexa user e assistant em RAG
  - pode resumir conversa
  - faz patch posterior da última mensagem do assistente
- SSE:
  - não usa `ChatAgentLoop`
  - não executa tools
  - não roda o threshold extra de baixa confiança do endpoint REST
  - não indexa em RAG
  - não resume conversa
  - entrega progresso via eventos e persiste a mensagem final já com metadata

## Payloads relevantes
### `understanding`
- Origem: `build_understanding_payload(message)`.
- Campos-base:
  - `intent`
  - `summary`
  - `confidence`
  - `requires_confirmation`
- Campos enriquecidos depois:
  - `confidence_band`
  - `low_confidence`
  - `signals`
  - `routing`
  - `risk`
  - `confirmation_reason`
  - `confirmation`

### `citation_status`
- Origem: `build_citation_status(message, citations, retrieval_failed)`.
- Estados observados:
  - `present`
  - `not_applicable`
  - `missing_required`
  - `retrieval_failed`

### `confirmation`
- Origem:
  - `build_confirmation_payload()`
- Modos observados:
  - `source="heuristic"`
  - `source="pending_actions_sql"`
- Campos relevantes:
  - `required`
  - `reason`
  - `pending_action_id`
  - `approve_endpoint`
  - `reject_endpoint`

### `agent_state`
- Origem:
  - `build_agent_state()`
- Estados observados:
  - `waiting_confirmation`
  - `low_confidence`
  - `completed`
  - estados de stream como `thinking` e `streaming_response` aparecem na UI por combinação de payload + estado local

## 9. Falhas comuns e comportamento real
- `CHAT_CONVERSATION_NOT_FOUND`: 404 quando a conversa não existe ou o acesso é negado durante validação.
- `CHAT_ACCESS_DENIED`: 403 quando `user_id` ou `project_id` não batem com a conversa.
- `CHAT_MESSAGE_TOO_LARGE`: 413; no REST valida contra `CHAT_MAX_MESSAGE_BYTES`, no SSE do stream principal valida um limite fixo de 10KB (10 * 1024 bytes).
- `CHAT_INVALID_ROLE_OR_PRIORITY`: 422 em REST e SSE.
- `CHAT_AUTH_REQUIRED`: o start aceita fallback anônimo em transição; o stream usa resolução mais estrita e depende de auth/header/explicit user id.
- `Origin not allowed`: o SSE é bloqueado por `ensure_origin_allowed()` se a origem não estiver em `CORS_ALLOW_ORIGINS`.
- `SSE capacity exceeded`: `acquire_sse_slot()` pode devolver 429 por usuário/canal ou global.
- `stream_closed`, `connection_error`, `parse_error`: o `ChatStreamService` entra em retry exponencial até `SSE_MAX_RETRIES`; depois fecha com status `error`.
- Erros de histórico: alguns endpoints de histórico retornam `detail` simples em vez de `chat_http_error_detail`, então o cliente deve tratar 404/500 sem depender de `code/category`.
- `missing_required` em citações:
  - no REST vira placeholder + polling assíncrono
  - no SSE vira estudo inline ou placeholder de knowledge space
- Conversa com documentos anexados:
  - qualquer manifest já faz o serviço tentar grounding antes do chat geral
  - isso altera profundamente o fluxo da conversa
- Divergência de memória:
  - REST indexa mensagens no RAG
  - SSE não indexa
  - como a UI usa SSE por padrão, a memória vetorial do chat pode ficar atrás do histórico SQL
- Divergência de confirmação:
  - o backend pode marcar confirmação heurística sem `pending_action_id`
  - a UI não mostra CTA sem pendência estruturada

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[03 - Frontend/Serviços de Integração]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[02 - Backend/LLM Routing e Prompts]]

## Riscos/Lacunas
- `ChatStartRequest.title` existe no contrato, mas o endpoint não o propaga ao service/repositório.
- O caminho padrão da UI é SSE, porém o caminho SSE tem menos capacidades que o REST.
- O SSE ainda captura memória ativa do usuário, mas não indexa o turno em `user_chat_<user_id>` nem roda sumarização; isso cria assimetria entre histórico SQL e memória vetorial.
- Qualquer conversa com manifests documentais tende a entrar primeiro no branch documental, mesmo para perguntas gerais.
- O stream principal e o stream de eventos usam tecnologias diferentes e superfícies de autenticação diferentes.
- O chat depende de SQL, Qdrant, broker e LLM em graus diferentes; falhas parciais geram sintomas visuais parecidos para o operador.

## Arquivos-fonte
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `frontend/src/app/services/chat-auth-headers.util.ts`
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/chat/chat_stream.py`
- `backend/app/api/v1/endpoints/chat/chat_history.py`
- `backend/app/api/v1/endpoints/chat/deps.py`
- `backend/app/api/v1/endpoints/pending_actions.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/chat/conversation_service.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat/chat_citation_service.py`
- `backend/app/services/chat/chat_contracts.py`
- `backend/app/services/chat/message_helpers.py`
- `backend/app/services/intent_routing_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/chat_study_service.py`
- `backend/app/repositories/chat_repository_sql.py`
