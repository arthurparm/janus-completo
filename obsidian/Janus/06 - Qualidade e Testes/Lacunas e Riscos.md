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
- O dominio de tools mistura catalogo em memoria, import side-effects, pendencias SQL e pendencias LangGraph sob a mesma UX operacional.

## Lacunas percebidas
- Pouca evidencia de E2E de UX completa.
- Diferenca potencial entre saude de container e saude logica.
- Parte das integracoes de LLM/local runtime depende fortemente de configuracao.
- O frontend escuta `tool_status`, mas o backend atual nao emite esse evento em `StreamingService`.
- O fluxo SSE nao indexa mensagens no RAG nem chama `maybe_summarize()`, entao historico e grounding podem divergir do caminho REST.
- A criacao de pending action fallback depende de `user_id`; em cenarios anonimos ou mal resolvidos a UI pode receber confirmacao sem ID estruturado.
- A tela `/tools` lista apenas pending actions SQL (`include_graph: false`), embora o backend tambem tenha pending actions LangGraph com semantica diferente de retomada.
- `approve_sql_action()` e `reject_sql_action()` apenas mudam o status em `pending_actions` e sincronizam o historico do chat; a aprovacao SQL nao reexecuta a tool pendente.
- O catalogo de tools e process-local: `action_registry`, historico de chamadas e rate limits em memoria sao perdidos em restart e nao representam necessariamente outros processos/workers.
- O registro de tools depende de side-effects de import. `Kernel.startup()` garante `os_tools` e `ui_tools`, mas varias tools de `agent_tools` so entram no registry quando esse modulo e importado por outro fluxo.
- `ActionRegistry.register()` permite sobrescrever uma tool existente pelo mesmo nome; a permissao efetiva e a implementacao efetiva dependem da ordem de registro.
- `ToolService.PROTECTED_TOOLS` protege apenas parte das tools built-in; outras tools nativas continuam removiveis via `DELETE /api/v1/tools/{tool_name}`.
- As rotas de criacao dinamica de tool nao recebem `requires_confirmation`; uma tool criada em runtime entra no registry sem esse guardrail explicito, salvo bloqueios indiretos de politica/permissao.
- `execute_system_command()` declara "sem restricoes" no docstring, mas a implementacao usa `run_restricted_command()`; a documentacao inline do proprio codigo ja diverge da execucao real.

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
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `qa/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- Esta nota e deliberadamente viva e deve crescer conforme incidentes reais forem mapeados.
