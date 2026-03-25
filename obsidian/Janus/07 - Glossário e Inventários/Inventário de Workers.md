---
tipo: inventario
dominio: backend
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Workers

## Objetivo
Listar o plano assíncrono real do backend e separar com precisão:

- arquivo Python
- nome lógico usado no roteamento
- nome observado em `/api/v1/workers/status`
- fila ou loop efetivo de runtime
- lacunas entre o que o código consegue publicar e o que realmente tem consumer registrado

## Responsabilidades
- Diferenciar workers do orquestrador, processos de fundo do `Kernel` e helpers sem superfície própria de runtime.
- Mostrar quando o nome exposto ao operador não coincide com o nome lógico do fluxo.
- Registrar as lacunas entre contrato HTTP e runtime real.

## Entradas
- `backend/app/core/workers/*`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/tasks.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/models/schemas.py`

## Saídas
- Matriz `arquivo -> worker -> fila/loop -> status`.
- Índice de nomes observados na API.
- Lista de discrepâncias entre código e runtime.

## Dependências
- [[02 - Backend/Autonomia e Workers]]
- [[02 - Backend/Kernel e Startup]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Superfícies reais de runtime
- `app.state.orchestrator_workers`
  - preenchido por `main.py` ou por `POST /api/v1/workers/start-all`
  - é a única fonte de `GET /api/v1/workers/status`
- `app.state.workers`
  - recebe `kernel.workers`
  - contém só objetos long-lived selecionados pelo `Kernel`
  - não é consumido por `/api/v1/workers/status`
- `GET /api/v1/tasks/queue/{queue_name}`
  - expõe `messages` e `consumers` por fila
  - é a forma mais objetiva de observar duplicação de consumers

## Workers observados pelo orquestrador

| Nome observado | Arquivo principal | Entrada de runtime | Fila ou loop | Tarefa efetiva |
| --- | --- | --- | --- | --- |
| `memory_maintenance` | `backend/app/core/workers/memory_maintenance_worker.py` | `memory_maintenance_worker.start()` | loop interno | poda de memórias via `generative_memory_service.prune_memories()` |
| `knowledge_consolidation` | `backend/app/core/workers/async_consolidation_worker.py` | `start_consolidation_worker()` | `janus.knowledge.consolidation` | consome `knowledge_consolidation` com modos `batch`, `single` e `knowledge_space` |
| `document_ingestion` | `backend/app/core/workers/document_ingestion_worker.py` | `start_document_ingestion_worker()` | `janus.document.ingestion` | consome `document_ingestion` com `doc_id` obrigatório e `auto_consolidate` opcional |
| `agent_tasks` | `backend/app/core/workers/agent_tasks_worker.py` | `start_agent_tasks_worker()` | `janus.agent.tasks` | consome `agent_task` com `question` e `agent_type` |
| `neural_training` | `backend/app/core/workers/neural_training_worker.py` | `start_neural_training_worker()` | `janus.neural.training` | consome `neural_training` com `dataset_version`, `model_name` e `training_params` |
| `reflexion` | `backend/app/core/workers/reflexion_worker.py` | `start_reflexion_worker()` | `janus.tasks.reflexion` | consome `reflexion_task`; em falha ou score baixo publica `janus.failure.detected` |
| `meta_agent` | `backend/app/core/workers/meta_agent_worker.py` | `start_meta_agent_worker()` | `janus.meta_agent.cycle` | consome `meta_agent_cycle` |
| `failure_consumer` | `backend/app/core/workers/meta_agent_worker.py` | `start_failure_event_consumer()` | `janus.failure.detected` | transforma falhas em memória compacta e aciona novo ciclo do meta-agent |
| `auto_scaler` | `backend/app/core/workers/auto_scaler.py` | `start_auto_scaler()` | loop interno | ajusta consumers próprios para `janus.agent.tasks`, `janus.neural.training`, `janus.knowledge.consolidation` e `janus.meta_agent.cycle` |
| `auto_healer` | `backend/app/core/monitoring/auto_healer.py` | `start_auto_healer()` | loop interno | reconecta broker, reconcilia políticas de fila, limpa poison pills e pode disparar meta-agent |
| `router` | `backend/app/core/workers/router_worker.py` | `start_router_worker()` | `janus.tasks.router` | consome `task_state`, roteia o próximo papel e side-publishes consolidação/destilação |
| `code_agent` | `backend/app/core/workers/code_agent_worker.py` | `start_code_agent_worker()` | `janus.tasks.agent.coder` | consome `task_state`, gera código e encaminha para `red_team` |
| `red_team_agent` | `backend/app/core/workers/red_team_agent_worker.py` | `start_red_team_agent_worker()` | `janus.tasks.agent.red_team` | consome `task_state`, audita segurança e devolve para `coder` ou `professor` |
| `professor_agent` | `backend/app/core/workers/professor_agent_worker.py` | `start_professor_agent_worker()` | `janus.tasks.agent.professor` | consome `task_state`, revisa e decide `sandbox`, `router` ou retorno ao `coder` |
| `sandbox_agent` | `backend/app/core/workers/sandbox_agent_worker.py` | `start_sandbox_agent_worker()` | `janus.tasks.agent.sandbox` | consome `task_state`, executa `script_code` em Docker restrito e volta para `coder` ou `router` |
| `thinker_agent` | `backend/app/core/workers/thinker_agent_worker.py` | `start_thinker_agent_worker()` | `janus.tasks.agent.thinker` | consome `task_state`, gera plano e envia para `coder` |
| `distillation` | `backend/app/core/workers/distillation_worker.py` | `start_distillation_worker()` | `janus.knowledge.distillation` | consome `knowledge_distillation` com `task_state` e salva dataset de treino |
| `google_productivity` | `backend/app/core/workers/google_productivity_worker.py` | `start_google_productivity_consumer()` | `janus.productivity.google.calendar` + `janus.productivity.google.mail` | consumer composto; processa `google_calendar_add_event` e `google_mail_send` |
| `debate_proponent` | `backend/app/core/workers/debate_proponent_worker.py` | `start_debate_proponent_worker()` | `janus.tasks.agent.debate.proponent` | consome `task_state` e propõe/refina código |
| `debate_critic` | `backend/app/core/workers/debate_critic_worker.py` | `start_debate_critic_worker()` | `janus.tasks.agent.debate.critic` | consome `task_state`, aprova/reprova e pode iterar até 5 ciclos |
| `codex_worker` | `backend/app/core/workers/codex_worker.py` | `start_codex_worker()` | `janus.tasks.codex` | consome `codex_fix` e `codex_review` |

## Arquivos de workers que não viram nome próprio em `/workers/status`

| Arquivo | Papel real | Superfície de runtime |
| --- | --- | --- |
| `backend/app/core/workers/__init__.py` | só reexporta `start_all_workers` | nenhuma |
| `backend/app/core/workers/data_harvester.py` | define `MemoryConnector` e `DataHarvester` | iniciado pelo `Kernel`; não aparece em `/workers/status` |
| `backend/app/core/workers/knowledge_consolidator_worker.py` | define `KnowledgeConsolidator` e o singleton `knowledge_consolidator` | loop próprio via `knowledge_consolidator.start(...)`; não vira nome observado |
| `backend/app/core/workers/life_cycle_worker.py` | loop interno do ciclo de vida | iniciado pelo `Kernel`; não aparece em `/workers/status` |
| `backend/app/core/workers/neural_training_system.py` | biblioteca de treino (`TrainingConfig`, `NeuralTrainer` etc.) | nenhuma |
| `backend/app/core/workers/orchestrator.py` | monta a lista `WORKER_NAMES` e sobe o conjunto do orquestrador | não é worker; é o registrador do runtime observado |

## Nomes lógicos vs nomes observados

### Casos 1:1
- `router` -> nome observado `router`
- `distillation` -> nome observado `distillation`
- `reflexion` -> nome observado `reflexion`
- `meta_agent` -> nome observado `meta_agent`

### Casos em que o nome lógico difere do nome observado
- `coder`, `code`, `code_agent` no `CollaborationService` publicam em `janus.tasks.agent.coder`, mas o operador vê `code_agent`.
- `professor`, `review`, `professor_agent`, `curator` publicam em `janus.tasks.agent.professor`, mas o operador vê `professor_agent`.
- `sandbox`, `tester`, `test` publicam em `janus.tasks.agent.sandbox`, mas o operador vê `sandbox_agent`.
- `red_team`, `security`, `auditor` publicam em `janus.tasks.agent.red_team`, mas o operador vê `red_team_agent`.
- `thinker`, `thinker_agent`, `architect`, `reasoning` publicam em `janus.tasks.agent.thinker`, mas o operador vê `thinker_agent`.
- `knowledge_consolidator`, `knowledge`, `consolidator`, `librarian`, `memory` publicam em `janus.knowledge.consolidation`, mas o operador vê `knowledge_consolidation`.
- `google_productivity` é um nome observado único, mas por baixo dele existem duas filas distintas e o endpoint pode devolver um worker composto com `children`.

## Papéis lógicos que o código publica mas o orquestrador não sobe
- `blue_team`
  - o `CollaborationService` publica em `janus.tasks.agent.blue_team`
  - o `router_worker` pode forçar escape para `blue_team` quando detecta loop repetido de `red_team`
  - não existe `start_blue_team_worker()` nem nome correspondente em `WORKER_NAMES`
- `security_judge`
  - o `CollaborationService` publica em `janus.tasks.agent.security_judge`
  - não existe consumer correspondente no orquestrador

## Processos de fundo do `Kernel` fora da API de workers
- `knowledge_consolidator.start(limit=10, min_score=0.0)`
  - loop periódico de consolidação em lote
- `DataHarvester.start()`
  - loop interno de harvesting
- `LifeCycleWorker.start()`
  - heartbeat de metas e consolidação periódica
- `OutboxService.start(interval_seconds=5)`
  - despacho do outbox transacional
- `SchedulerService.start()`
  - agenda:
  - `meta_agent_analysis` a cada 300 s
  - `memory_health_check` a cada 600 s
  - `daily_cleanup` diariamente às 03:00
  - `audit_retention_cleanup` em intervalo configurável
  - `update_gemini_quotas` a cada 3600 s

## Contrato real de `/api/v1/workers/status`
- O endpoint nunca consulta broker, scheduler ou `HealthMonitor`.
- Ele só serializa o registro já existente em `app.state.orchestrator_workers`.
- `asyncio.Task`
  - `state=running` quando `done() == False` e `cancelled() == False`
  - `state=error` quando terminou com exceção
  - `state=stopped` quando terminou sem exceção
- `tuple` ou `list`
  - vira `composite=true`
  - agrega `children`
  - usa o primeiro `exception` encontrado
- `DisabledWorkerHandle`
  - vira `state=disabled`
  - inclui `reason` e `detail`

## O que `POST /api/v1/workers/start-all` e `POST /api/v1/workers/stop-all` realmente fazem
- `start-all`
  - recusa novo start se algum item de `app.state.orchestrator_workers` ainda estiver `running`
  - chama `start_all_workers()`
  - associa a cada handle um nome de `WORKER_NAMES`
  - grava o payload em `app.state.orchestrator_workers`
- `stop-all`
  - cancela apenas as tasks registradas em `app.state.orchestrator_workers`
  - para worker composto, cancela cada child recursivamente
  - limpa o registry HTTP, mas não desmonta os loops internos do `Kernel`

## O que `GET /api/v1/system/overview` mostra sobre workers
- O endpoint reaproveita `_task_status()` e simplifica o resultado para:
  - `disabled`
  - `running`
  - `error`
  - `unknown`
  - `stopped`
- `last_heartbeat` é sempre `datetime.now(UTC)` no momento da resposta.
- `tasks_processed` vem de `w.get("tasks_processed", 0)`, mas o orquestrador não mantém esse contador.
- Resultado: `system/overview` é útil como painel resumido, não como fonte confiável de heartbeat nem throughput.

## Relação entre nomes observados e filas monitoráveis
- `GET /api/v1/workers/status`
  - responde no vocabulário de `WORKER_NAMES`
- `GET /api/v1/tasks/queue/{queue_name}`
  - responde no vocabulário de `QueueName` ou de filas literais como `janus.productivity.google.calendar`
- `CollaborationService.pass_task(...)`
  - publica no vocabulário de papéis lógicos (`coder`, `thinker`, `professor`, `sandbox`, `red_team`, `knowledge_consolidator`, etc.)
- Para entender um incidente operacional, quase sempre é preciso cruzar as três superfícies.

## Observação prática do runtime
- Em 25 de março de 2026, no PC TESTE (`100.89.17.105`), `GET /api/v1/workers/status` retornou `tracked=21`.
- No mesmo runtime:
  - `google_productivity` apareceu como `disabled` com `detail=ENABLE_GOOGLE_PRODUCTIVITY_WORKER=false`
  - `GET /api/v1/tasks/queue/janus.knowledge.consolidation` retornou `consumers=2`
  - `GET /api/v1/tasks/queue/janus.document.ingestion` retornou `consumers=2`
  - `GET /api/v1/tasks/queue/janus.neural.training` retornou `consumers=2`
  - `GET /api/v1/tasks/queue/janus.meta_agent.cycle` retornou `consumers=1`
  - `GET /api/v1/tasks/queue/janus.failure.detected` retornou `consumers=1`

## Lacunas reais entre código e runtime
- O `Kernel` sobe `knowledge_consolidation`, `document_ingestion` e `neural_training` por conta própria.
- O `lifespan` também pode subir esses mesmos consumers via `start_all_workers()` quando `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`.
- Resultado: a fila pode ter mais consumers do que o endpoint de workers deixa evidente.
- `/api/v1/workers/status` não mostra `knowledge_consolidator`, `data_harvester`, `life_cycle_worker`, `outbox_service` nem `scheduler`.
- O runtime aceita publicar para `blue_team` e `security_judge`, mas o inventário de consumers iniciados não cobre esses papéis.
- `google_productivity` é um único nome observado, mas operacionalmente representa duas filas e pode virar worker composto.

## Arquivos-fonte
- `backend/app/core/workers/orchestrator.py`
- `backend/app/core/workers/agent_tasks_worker.py`
- `backend/app/core/workers/async_consolidation_worker.py`
- `backend/app/core/workers/document_ingestion_worker.py`
- `backend/app/core/workers/neural_training_worker.py`
- `backend/app/core/workers/meta_agent_worker.py`
- `backend/app/core/workers/router_worker.py`
- `backend/app/core/workers/google_productivity_worker.py`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/services/scheduler_service.py`

## Fluxos relacionados
- [[02 - Backend/Autonomia e Workers]]
- [[02 - Backend/Kernel e Startup]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- Nome observado, fila e papel lógico não são a mesma coisa; ler só `WORKER_NAMES` produz conclusões erradas.
- A visão HTTP de workers é parcial e pode mascarar duplicação de consumers.
- Existem filas publicáveis sem consumer registrado no conjunto analisado.
