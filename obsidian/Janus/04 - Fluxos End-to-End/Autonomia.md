---
tipo: fluxo
dominio: autonomia
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Autonomia

## O que esta area realmente faz hoje
O dominio de Autonomia tem dois fluxos diferentes:

1. `AutonomyLoop`: controla metas, monta um plano e enfileira um `TaskState` para o Parlamento via `router`.
2. `Self-study admin`: aprende sobre o codigo e atualiza memoria/grafo quando disparado manualmente, no startup ou na conclusao de metas.

O loop principal nao executa o plano passo a passo dentro de `AutonomyService`. O comportamento real atual e:

1. Ler metricas do sistema.
2. Escolher a proxima meta `pending`.
3. Marcar a meta como `in_progress`.
4. Usar um plano fornecido externamente ou gerar um plano via planner.
5. Escolher um unico passo desse plano.
6. Enfileirar um `TaskState` com contexto de autonomia para o `router`.

## Fluxo end-to-end real
1. O cliente chama `POST /api/v1/autonomy/start`.
2. Se `plan` vier no request, cada passo e validado por shape, existencia da ferramenta no `action_registry`, compatibilidade com `args_schema` e allowlist/blocklist do proprio request.
3. `AutonomyService.start()` monta `AutonomyConfig`, calcula um `scope_key` de lease (`global`, `user:<id>`, `project:<id>` ou `user:<id>:project:<id>`), tenta adquirir lock e recria o `PolicyEngine`.
4. Se o lease for obtido, o service restaura a run SQL ativa mais recente do mesmo escopo ou cria uma nova `AutonomyRun`.
5. O loop sobe em background com `asyncio.create_task(self._run_loop())`.
6. Em cada ciclo, o loop:
   - consulta `OptimizationService.get_system_health()`;
   - busca a proxima meta `pending` ordenada por `priority asc, created_at asc`;
   - muda a meta para `in_progress`;
   - usa `config.plan` se existir; caso contrario chama o planner Reflexion; se falhar, usa fallback seguro;
   - escolhe um passo preferindo `search_web` ou `get_enriched_context`; se nao houver, usa o ultimo passo do plano;
   - cria ou reaproveita um registro idempotente em `autonomy_enqueue_ledger`;
   - publica um `TaskState` para o `router` com `meta.autonomy.goal_id`, `execution_mode=enqueue_router`, `plan`, `selected_step` e `autonomy_run_id`.
7. O `router` passa a tarefa para os workers/agentes do Parlamento.
8. Quando um `TaskState` autonomo volta ao `router` em estado terminal, `CollaborationService` fecha a meta automaticamente:
   - `completed` vira goal `completed`;
   - qualquer outro terminal (`failed`, `blocked`, `cancelled`) vira goal `failed`.
9. Se a meta terminou com sucesso, o sistema tenta disparar `run_self_study(mode="incremental")`.

## Nomes logicos do fluxo vs nomes observados em runtime
- O `AutonomyLoop` publica para o Parlamento usando `next_agent_role`, nao usando `WORKER_NAMES`.
- Mapeamentos relevantes:
  - `thinker` -> fila `janus.tasks.agent.thinker` -> worker observado `thinker_agent`
  - `coder` -> fila `janus.tasks.agent.coder` -> worker observado `code_agent`
  - `red_team` -> fila `janus.tasks.agent.red_team` -> worker observado `red_team_agent`
  - `professor` -> fila `janus.tasks.agent.professor` -> worker observado `professor_agent`
  - `sandbox` -> fila `janus.tasks.agent.sandbox` -> worker observado `sandbox_agent`
  - `knowledge_consolidator` -> fila `janus.knowledge.consolidation` -> worker observado `knowledge_consolidation`
- Isso explica por que o vocabulário de `/api/v1/workers/status` não coincide com o vocabulário do plano ou do `TaskState`.

## Contratos HTTP principais
### `POST /api/v1/autonomy/start`
- Sincrono no request.
- Valida `plan` apenas se o request trouxe passos.
- Inicia o loop em background e devolve `{"status":"started"}`.
- Se o lease do escopo ja estiver ocupado por outra instancia, devolve `409`.
- Se a propria instancia ja estiver ativa, devolve `400`.

### `POST /api/v1/autonomy/stop`
- Sincrono no request.
- Marca `_running=false`, cancela a task assincrona, tenta marcar a run como `stopped` e liberar o lease.
- Se nao houver loop ativo, devolve `400`.

### `GET /api/v1/autonomy/status`
- Sincrono no request.
- Exponhe:
  - `active`
  - `cycle_count`
  - `last_cycle_at`
  - `config`
  - `runtime_lock`

### `PUT /api/v1/autonomy/plan`
- Sincrono no request.
- Revalida o plano contra a allowlist/blocklist correntes do service.
- Substitui apenas `self._config.plan` em memoria.
- Nao persiste o plano em banco.

### `PUT /api/v1/autonomy/policy`
- Sincrono no request.
- Atualiza em memoria `risk_profile`, `auto_confirm`, allowlist, blocklist e cotas.
- Reconstroi o `PolicyEngine`.
- Nao revalida o plano que ja estava carregado.
- Nao persiste a politica na run ja existente.

### `GET /api/v1/autonomy/plan`
- Sincrono no request.
- Retorna o plano atual em memoria, inclusive quando o loop estiver parado.

### Goals em `POST/GET/PATCH/DELETE /api/v1/autonomy/goals`
- CRUD sincrono em SQL via `GoalManager`.
- `PATCH /goals/{id}/status` aceita apenas `pending|in_progress|completed|failed`.
- Quando o patch marca `completed`, o endpoint agenda um trigger de self-study em `BackgroundTasks`.

## Plan update e validacao de steps
`_validate_plan_steps()` valida apenas planos recebidos via API (`/start` com `plan` explicito e `PUT /plan`):

- cada passo precisa ser `dict`;
- `tool` precisa existir e ser `str`;
- `args` precisa ser `dict`;
- `tool` nao pode estar na `blocklist`;
- se houver `allowlist`, `tool` precisa estar nela;
- a ferramenta precisa existir no `action_registry`;
- se a ferramenta expuser `args_schema`, os argumentos sao validados por Pydantic.

O planner interno usa uma validacao diferente e mais fraca:

- remove tools bloqueadas pela `blocklist`;
- ignora tools inexistentes;
- forca `args` para `dict`;
- aceita metadados como `critical`, `retry` e `fallback_tool`;
- nao valida `args_schema`;
- nao faz a mesma checagem de allowlist usada pelo endpoint.

## Policy update e cobertura real de politica
`PolicyEngine` sabe lidar com:

- `risk_profile`
- `auto_confirm`
- allowlist/blocklist de tool
- capability allowlist
- scope allowlist
- command allowlist/blocklist
- deteccao de prompt injection
- simulacao de impacto destrutivo
- quota por ciclo

Mas o `AutonomyLoop` atual usa so uma parte disso no caminho real:

- `start()` e `update_policy()` apenas recriam o `PolicyEngine`;
- o planner usa a `blocklist` e parte do `risk_profile` para listar tools;
- o endpoint valida allowlist/blocklist/schema apenas para planos enviados manualmente.

O loop nao chama `validate_tool_call()`, `validate_content_safety()`, `simulate_tool_call()` nem `can_continue_cycle()` antes de enfileirar o passo selecionado.

## Allowlist e blocklist
Existem dois niveis de comportamento:

1. Nivel HTTP/manual:
   - `POST /start` e `PUT /plan` aplicam allowlist/blocklist diretamente nos passos enviados.
2. Nivel `PolicyEngine`:
   - usado para reconstruir politica e filtrar parte do planner, mas nao para validar a publicacao do `selected_step` no modo `enqueue_router`.

Na pratica, o sistema esta mais estrito para planos manuais do que para planos gerados pelo LLM.

## Goals
### Fonte de verdade
- SQL em `autonomy_goals` e `autonomy_goal_transitions`.
- Firestore e apenas espelho opcional.

### Estados
- `pending`
- `in_progress`
- `completed`
- `failed`

### Selecionar meta
- `GoalManager.get_next_goal()` pega a primeira meta `pending` por `priority asc, created_at asc`.

### Fechar meta
- O loop muda `pending -> in_progress` ao selecionar.
- Se falhar antes de publicar o enqueue, a meta volta para `pending`.
- Se o `TaskState` autonomo termina e volta ao `router`, a meta fecha via `CollaborationService`.
- `completed` no `TaskState` fecha a goal como `completed`.
- `failed`, `blocked` e `cancelled` fecham a goal como `failed`.

## Runtime lock
O lock de runtime vive em `autonomy_loop_leases`.

### Como funciona
- `scope_key` e derivado de `user_id` e `project_id`.
- `owner_id` e gerado como `autonomy-loop:<uuid>`.
- TTL = `max(30, interval_seconds * 3)`.
- `start()` tenta `try_acquire`.
- a cada ciclo o loop chama `renew()`.
- `stop()` chama `release()`.

### O que aparece em `/status`
`runtime_lock` exposto pelo endpoint inclui:

- `scope_key`
- `owner_id`
- `expires_at`
- `lease_held`

Isso permite ver se a instancia atual segura o lease ou apenas enxerga outro owner no mesmo escopo.

## O que e sincrono, assincrono, agendado e protegido por politica
### Sincrono
- `POST /start`, `POST /stop`, `GET /status`, `GET /plan`, `PUT /plan`, `PUT /policy`
- CRUD de goals
- leitura de historico em `autonomy_history`

### Assincrono
- `AutonomyService._run_loop()`
- publicacao de `TaskState` para o `router`
- execucao pelos workers do Parlamento
- trigger de self-study disparado por `BackgroundTasks` ou `asyncio.create_task()`

### Agendado/no boot
- `startup_self_study_check()` e agendado no startup do app, de forma nao bloqueante
- os workers do orquestrador sobem no startup apenas se `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`
- o `Kernel` ja sobe `knowledge_consolidation`, `document_ingestion` e `neural_training` antes disso
- quando o orquestrador tambem sobe no startup, essas filas podem ficar com dois consumers no mesmo processo

## Filas side-effect do fluxo
- `router_worker`
  - publica `knowledge_consolidation` em paralelo quando o `TaskState` termina com conhecimento aproveitavel
  - publica `knowledge_distillation` em paralelo quando o `TaskState` termina com sucesso
- `reflexion_worker`
  - publica `janus.failure.detected` quando o ciclo falha ou fica abaixo do limiar
- `meta_agent_worker`
  - consome `janus.failure.detected` e dispara `janus.meta_agent.cycle`

## Papéis que o fluxo consegue publicar mas não têm consumer iniciado no conjunto analisado
- `blue_team`
  - usado pelo `router_worker` como escape de loop quando detecta repetição de `red_team`
  - o `CollaborationService` publica em `janus.tasks.agent.blue_team`
  - não há worker correspondente em `backend/app/core/workers/*`
- `security_judge`
  - o `CollaborationService` publica em `janus.tasks.agent.security_judge`
  - não há worker correspondente em `backend/app/core/workers/*`

### Protegido por politica hoje
- validacao HTTP de planos manuais
- filtro parcial do planner por `blocklist` e `risk_profile`
- regras do `PolicyEngine` disponiveis para execucao de tools, mas nao acionadas pelo `AutonomyLoop` no modo atual

## Observabilidade e rastreio
O dominio registra:

- `autonomy_runs`
- `autonomy_steps`
- `autonomy_enqueue_ledger`
- `autonomy_goal_transitions`
- `autonomy_self_study_runs`
- `autonomy_self_study_files`
- `autonomy_loop_leases`

APIs de historico:

- `GET /api/v1/autonomy-history/runs`
- `GET /api/v1/autonomy-history/runs/{run_id}`
- `GET /api/v1/autonomy-history/runs/{run_id}/steps`
- `GET /api/v1/autonomy-history/runs/{run_id}/enqueues`

## Riscos e lacunas reais
- O nome "AutonomyLoop" sugere execucao direta de plano, mas o comportamento atual e apenas `enqueue_router`.
- O loop escolhe um unico passo do plano; o restante do plano e contexto, nao contrato de execucao.
- `PUT /policy` nao revalida o plano que ja esta carregado.
- O planner interno nao valida `args_schema` nem a allowlist do mesmo jeito que a API valida planos manuais.
- O fechamento automatico da meta depende do `TaskState` terminal voltar ao `router` com `meta.autonomy.goal_id`.
- O patch manual para `completed` sempre agenda self-study, mesmo quando a meta ja estava `completed`.
- O caminho de perda de lease encerra o loop, mas nao passa pelo mesmo cleanup de `stop()`.
- O fluxo de autonomia consegue publicar para `blue_team` e `security_judge`, mas o conjunto de workers iniciado pelo runtime analisado não cobre esses papéis.
- O operador que olha só `/api/v1/workers/status` não enxerga cardinalidade real de consumers nas filas da autonomia.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/api/v1/endpoints/autonomy_admin.py`
- `backend/app/api/v1/endpoints/autonomy_history.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/core/autonomy/goal_manager.py`
- `backend/app/core/autonomy/policy_engine.py`
- `backend/app/core/autonomy/planner.py`
- `backend/app/core/autonomy/taskstate_status.py`
- `backend/app/services/autonomy_lock_service.py`
- `backend/app/core/workers/router_worker.py`
- `backend/app/main.py`

## Fluxos relacionados
- [[02 - Backend/Autonomia e Workers]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
