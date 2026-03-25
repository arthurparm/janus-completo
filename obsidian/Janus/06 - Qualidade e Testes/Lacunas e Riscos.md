---
tipo: qualidade
dominio: testes
camada: riscos
fonte-de-verdade: codigo
status: ativo
---

# Lacunas e Riscos

## Objetivo
Registrar as fragilidades percebidas a partir do codigo e da cobertura.

## Responsabilidades
- Sinalizar acoplamentos altos.
- Sinalizar zonas de baixa visibilidade.

## Entradas
- Leitura estrutural do backend/frontend.
- Inventario de testes.

## Saidas
- Backlog tecnico de risco arquitetural.

## Dependencias
- [[06 - Qualidade e Testes/Mapa de Testes]]
- [[02 - Backend/Como o Backend Pensa]]

## Riscos principais
- `BackendApiService` concentra contratos demais.
- `ConversationsComponent` concentra subfluxos demais.
- O kernel compoe quase tudo manualmente.
- O deploy distribuido PC1/PC2 aumenta superficie de falha.
- Capacidades internas do backend sao maiores que a UX operacional atual.
- REST e SSE do chat tem capacidades diferentes apesar de servirem a mesma UX.
- `ChatStudyJobService` e in-memory e perde estado em restart.
- `GET /api/v1/chat/start` aceita `title`, mas a implementacao descarta o valor.
- `AgentEventsService` depende de `EventSource` sem headers; se `CHAT_AUTH_ENFORCE_REQUIRED` subir, o stream de eventos tende a quebrar.

## Lacunas percebidas
- Pouca evidencia de E2E de UX completa.
- Diferenca potencial entre saude de container e saude logica.
- Parte das integracoes de LLM/local runtime depende fortemente de configuracao.
- O frontend escuta `tool_status`, mas o backend atual nao emite esse evento em `StreamingService`.
- O fluxo SSE nao indexa mensagens no RAG nem chama `maybe_summarize()`, entao historico e grounding podem divergir do caminho REST.
- A criacao de pending action fallback depende de `user_id`; em cenarios anonimos ou mal resolvidos a UI pode receber confirmacao sem ID estruturado.

## Autonomia: riscos reais do codigo atual
- O `AutonomyLoop` nao executa um plano inteiro; ele escolhe um unico `selected_step` e publica um `TaskState` para o `router`. O restante do plano vira contexto, nao contrato de execucao.
- `PUT /policy` reconstrui o `PolicyEngine`, mas nao revalida o plano atual em memoria nem persiste a politica atualizada na `AutonomyRun` ja aberta.
- O caminho manual de plano (`POST /start` com `plan`, `PUT /plan`) valida `args_schema`, allowlist e blocklist; o planner interno nao aplica a mesma validacao.
- O `PolicyEngine` possui gates de comando, escopo, capability, content safety e simulacao destrutiva, mas o `AutonomyLoop` em `enqueue_router` nao chama `validate_tool_call()`, `validate_content_safety()`, `simulate_tool_call()` nem `can_continue_cycle()` antes do enqueue.
- Se o lease de runtime for perdido durante `_run_loop()`, o loop encerra por `break`, mas esse caminho nao passa pelo cleanup completo de `stop()`. Isso pode deixar `AUTONOMY_ACTIVE` stale e a `AutonomyRun` ainda marcada como `running`.
- O fechamento automatico da meta depende de um `TaskState` terminal com `meta.autonomy.goal_id` retornar ao `router`. Se a cadeia de workers falhar antes desse retorno, a goal pode ficar presa em `in_progress`.
- `PATCH /autonomy/goals/{id}/status` com `completed` sempre agenda self-study em `BackgroundTasks`, mesmo quando o status ja era `completed`.
- `AutonomyAdminService.run_self_study()` nao tem lock proprio. Startup, trigger manual e trigger por conclusao de goal podem iniciar runs concorrentes sobre o mesmo repo.
- O self-study limita tempo e quantidade de arquivos (`MAX_RUN_SECONDS`, `MAX_FILES_PER_RUN`) e pode fechar como `partial`; isso protege o processo, mas tambem significa cobertura incompleta sem alerta forte na API.

## Arquivos-fonte
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_study_service.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/core/autonomy/policy_engine.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/main.py`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `qa/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- Esta nota e deliberadamente viva e deve crescer conforme incidentes reais forem mapeados.
