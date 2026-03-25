---
tipo: dominio
dominio: backend
camada: execucao
fonte-de-verdade: codigo
status: ativo
---

# Autonomia e Workers

## Leitura arquitetural correta
O backend separa autonomia em quatro blocos:

1. `AutonomyService`: loop de controle, lease, run history e enqueue do Parlamento.
2. `GoalManager`: CRUD de metas e transicoes de status.
3. `PolicyEngine` + `planner`: governanca declarativa e geracao/refino de plano.
4. `AutonomyAdminService`: backlog tecnico, self-study, memoria de codigo e auditoria admin.

O ponto mais importante: o `AutonomyLoop` atual nao e um executor local de tools. O `execution_mode` aceito e somente `enqueue_router`.

## Componentes principais
### `AutonomyService`
Responsabilidades reais:

- manter configuracao em memoria (`AutonomyConfig`);
- adquirir e renovar runtime lock;
- restaurar ou criar `AutonomyRun`;
- contar ciclos e registrar `AutonomyStep`;
- escolher a meta atual;
- montar o plano;
- escolher um passo do plano;
- enfileirar `TaskState` para o `router`.

### `GoalManager`
Responsabilidades reais:

- persistir goals em SQL;
- espelhar em Firestore se habilitado;
- registrar transicoes em `autonomy_goal_transitions`;
- expor `get_next_goal()` ordenado por prioridade e antiguidade.

### `PolicyEngine`
Capacidades implementadas:

- risco por permission level (`conservative|balanced|aggressive`);
- allowlist/blocklist de tools;
- capability allowlist;
- scope allowlist por tags `scope:*`;
- allowlist e blocklist de comandos sensiveis;
- deteccao de prompt injection;
- simulacao de destrutividade;
- quota por numero de acoes e tempo de ciclo.

Cobertura real no fluxo de autonomia:

- forte no caminho HTTP de planos manuais;
- parcial no planner;
- ausente como gate final antes do enqueue do passo escolhido.

### `planner`
Implementa um ciclo Reflexion:

1. draft
2. critique
3. refine
4. fallback seguro

Ele gera um array de passos, mas a validacao interna e limitada a existencia da tool, formato de `args`, blocklist e metadados opcionais.

### `AutonomyAdminService`
Nao faz parte do loop principal, mas e parte importante do dominio:

- sincroniza backlog tecnico em metas;
- executa self-study incremental/full;
- atualiza memoria vetorial e SelfMemory no grafo;
- responde code QA administrativo com citacoes.

## O que roda em cada contexto
### Durante o request HTTP
- validar payloads de `/autonomy`
- alterar config em memoria
- CRUD de goals
- iniciar/parar o loop
- consultar historico

### Em background dentro do processo da API
- `AutonomyService._run_loop()` via `asyncio.create_task`
- `startup_self_study_check()` via `asyncio.create_task`
- triggers de self-study apos meta concluida

### Em workers/filas
- `router_worker` consome o `TaskState` gerado pelo loop
- demais agentes do Parlamento executam o trabalho real
- knowledge distillation e consolidacao sao side-effects do roteamento
- o publish sai de `next_agent_role` no `CollaborationService`, nao do nome observado pelo endpoint de workers

### No startup do app
- `Kernel` injeta `autonomy_service`, `goal_manager` e `autonomy_admin_service` em `app.state`
- `start_all_workers()` sobe consumers do orquestrador se a flag permitir
- `startup_self_study_check()` roda sem bloquear o boot

## Runtime lock
O lease de autonomia e uma protecao cross-instance em banco:

- tabela: `autonomy_loop_leases`
- unidade de disputa: `scope_key`
- dono: `owner_id`
- heartbeat: renovado a cada ciclo
- expiracao: TTL = `max(30, interval_seconds * 3)`

Escopos possiveis:

- `global`
- `user:<user_id>`
- `project:<project_id>`
- `user:<user_id>:project:<project_id>`

Na pratica, o lock protege a subida simultanea do loop no mesmo escopo, nao a execucao interna de cada agente/worker.

## Plano e politica: contrato real
### Plano manual
Plano manual e o mais governado:

- passa por allowlist/blocklist do request/config atual;
- exige tool registrada;
- valida `args_schema` quando a tool declara schema.

### Plano gerado pelo planner
Plano gerado automaticamente e menos governado:

- respeita `blocklist`;
- tenta respeitar parte do `risk_profile`;
- nao chama `PolicyEngine.validate_tool_call()`;
- nao valida `args_schema`;
- nao garante que o `selected_step` final seja o unico tool permitido pela politica.

### Policy update
`PUT /policy` atualiza apenas estado em memoria do service.

Impactos:

- a politica nova vale para futuros ciclos do service atual;
- a run SQL nao e regravada;
- o plano que ja estava em memoria nao e revalidado;
- o modo `enqueue_router` continua sem gate de policy no ponto final de publish.

## Metas e fechamento de ciclo
### Origem
- `POST /autonomy/goals`
- `AutonomyAdminService.sync_backlog()`

### Selecionar
- sempre a primeira `pending` por `priority asc, created_at asc`

### Progredir
- `pending -> in_progress` quando o loop seleciona a meta
- `in_progress -> pending` se o publish do enqueue falhar

### Finalizar
- via `PATCH /goals/{id}/status`
- ou automaticamente quando um `TaskState` autonomo terminal volta ao `router`

Mapeamento do hook automatico:

- `TaskState.completed` => goal `completed`
- `TaskState.failed|blocked|cancelled` => goal `failed`

## Workers relevantes para autonomia
O `AutonomyLoop` nao aparece em `WORKER_NAMES`; ele e uma task propria do service. O que o orquestrador sobe e o ecossistema que consome o trabalho enfileirado.

### Essenciais para o fluxo atual
- `router`
- `code_agent`
- `professor_agent`
- `sandbox_agent`
- `red_team_agent`
- `thinker_agent`
- `distillation`

### Nomes logicos usados para publicar
- `router` -> `janus.tasks.router`
- `thinker` -> `janus.tasks.agent.thinker` -> nome observado `thinker_agent`
- `coder` -> `janus.tasks.agent.coder` -> nome observado `code_agent`
- `red_team` -> `janus.tasks.agent.red_team` -> nome observado `red_team_agent`
- `professor` -> `janus.tasks.agent.professor` -> nome observado `professor_agent`
- `sandbox` -> `janus.tasks.agent.sandbox` -> nome observado `sandbox_agent`
- `knowledge_consolidator` e aliases (`knowledge`, `consolidator`, `librarian`, `memory`) -> `janus.knowledge.consolidation` -> nome observado `knowledge_consolidation`

### Sobem via `start_all_workers()`
- `memory_maintenance`
- `knowledge_consolidation`
- `document_ingestion`
- `agent_tasks`
- `neural_training`
- `reflexion`
- `meta_agent`
- `failure_consumer`
- `auto_scaler`
- `auto_healer`
- `router`
- `code_agent`
- `red_team_agent`
- `professor_agent`
- `sandbox_agent`
- `thinker_agent`
- `distillation`
- `google_productivity` quando `ENABLE_GOOGLE_PRODUCTIVITY_WORKER=true`
- `debate_proponent`
- `debate_critic`
- `codex_worker`

### Side-effects do `router_worker`
- em sucesso, o router side-publishes `knowledge_consolidation` para `janus.knowledge.consolidation` quando detecta payload com conteudo de conhecimento
- em sucesso, o router side-publishes `knowledge_distillation` para `janus.knowledge.distillation`
- esses publishes sao paralelos ao roteamento principal do `TaskState`

### Papéis publicaveis sem worker correspondente
- `blue_team`
  - o `router_worker` usa `blue_team` como escape para loops repetidos de `red_team`
  - o `CollaborationService` publica em `janus.tasks.agent.blue_team`
  - nenhum worker em `backend/app/core/workers/*` e nenhum nome em `WORKER_NAMES` consomem essa fila
- `security_judge`
  - o `CollaborationService` publica em `janus.tasks.agent.security_judge`
  - nenhum worker em `backend/app/core/workers/*` e nenhum nome em `WORKER_NAMES` consomem essa fila

### Gap observado entre codigo e runtime
- `Kernel._start_background_processes()` sempre sobe consumers de:
  - `janus.knowledge.consolidation`
  - `janus.document.ingestion`
  - `janus.neural.training`
- `main.py` tambem pode subir esses mesmos consumers via `start_all_workers()` quando `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`
- no PC TESTE, em 25 de marco de 2026, as filas `janus.knowledge.consolidation`, `janus.document.ingestion` e `janus.neural.training` estavam com `consumers=2`
- `/api/v1/workers/status` mostrava apenas um nome por worker orquestrado e nao expunha essa duplicacao

## Persistencia operacional
Tabelas principais do dominio:

- `autonomy_runs`
- `autonomy_steps`
- `autonomy_enqueue_ledger`
- `autonomy_goals`
- `autonomy_goal_transitions`
- `autonomy_self_study_runs`
- `autonomy_self_study_files`
- `autonomy_self_study_state`
- `autonomy_loop_leases`

## Persistência por banco no domínio de autonomia
### Postgres
- é a fonte de verdade de runs, steps, goals, transições, evidence, self-study state e lease cross-instance
- também registra o ledger de enqueue e permite reconstruir histórico operacional

### Qdrant
- recebe experiências de `self_study` como `code_summary` em `janus_episodic_memory`
- recebe espelhos e material vetorial usado por code QA administrativo e busca híbrida

### Neo4j
- recebe `Experience` de self-study
- recebe `SelfMemory` e suas relações com arquivos e símbolos
- sustenta a parte estrutural do code QA administrativo

### RabbitMQ
- transporta o trabalho publicado pelo loop para o `router` e demais workers

### Redis
- não é persistência de autonomia
- pode influenciar quotas temporárias e governança de tools no ecossistema ao redor, mas não guarda o estado do loop

## Impacto de falha por banco no domínio
- Postgres falha:
  - o loop perde runs, steps, goals, leases e capacidade de coordenação durável
- RabbitMQ falha:
  - o loop ainda pode selecionar metas, mas o trabalho deixa de sair do processo via enqueue
- Qdrant falha:
  - self-study deixa de persistir memória vetorial e code recall híbrido degrada
- Neo4j falha:
  - self-memory e code graph deixam de ser atualizados; o domínio continua parcialmente vivo só com SQL

## Riscos e lacunas reais
- O loop nao consome `max_actions_per_cycle` como quota de passos executados; hoje ele so escolhe um passo e enfileira.
- `PolicyEngine` e mais poderoso do que o caminho real do `AutonomyLoop`.
- A autonomia depende do `router` para fechamento automatico de goals; sem esse retorno a meta pode ficar presa em `in_progress`.
- O caminho de lease perdido nao chama o mesmo cleanup de `stop()`, o que pode deixar rastros operacionais inconsistentes.
- `AutonomyAdminService.run_self_study()` nao usa lock proprio; startup, trigger manual e trigger por meta podem sobrepor execucoes.
- O fluxo consegue publicar para `blue_team` e `security_judge`, mas o conjunto de workers iniciado pelo orquestrador nao cobre esses papeis.
- Ler apenas `/api/v1/workers/status` nao basta para inferir quantos consumers reais existem nas filas da autonomia.

## Arquivos-fonte
- `backend/app/services/autonomy_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/core/autonomy/goal_manager.py`
- `backend/app/core/autonomy/policy_engine.py`
- `backend/app/core/autonomy/planner.py`
- `backend/app/core/autonomy/taskstate_status.py`
- `backend/app/services/autonomy_lock_service.py`
- `backend/app/core/workers/orchestrator.py`
- `backend/app/core/workers/router_worker.py`
- `backend/app/core/kernel.py`
- `backend/app/main.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Autonomia]]
- [[07 - Glossário e Inventários/Inventário de Workers]]
- [[06 - Qualidade e Testes/Lacunas e Riscos]]
