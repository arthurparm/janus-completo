---
tipo: dominio
dominio: backend
camada: composicao
fonte-de-verdade: codigo
status: ativo
---

# Kernel e Startup

## Objetivo
Documentar como o backend monta o runtime a partir de `FastAPI`, `lifespan` e `Kernel`, com a ordem real de boot, a composição manual de dependências e o wiring publicado em `app.state`.

## Responsabilidades
- Inicializar infraestrutura crítica antes de aceitar tráfego.
- Compor repositórios, serviços e objetos de orquestração no `Kernel`.
- Publicar dependências selecionadas em `app.state` para consumo dos endpoints.
- Subir processos de fundo, tarefas opcionais e componentes de runtime paralelos ao caminho HTTP.
- Encerrar recursos de forma ordenada no shutdown.

## Entradas
- `settings = AppSettings()` carregado do ambiente e de `app/.env`.
- Flags de startup como `INIT_MAS_AGENTS_ON_STARTUP`, `AUTO_INDEX_ON_STARTUP`, `START_ORCHESTRATOR_WORKERS_ON_STARTUP`, `FIREBASE_ENABLED`, `LANGCHAIN_TRACING_V2` e `LLM_RATE_LIMITS`.
- Defaults relevantes vindos de `backend/app/config.py`: `INIT_MAS_AGENTS_ON_STARTUP=True`, `AUTO_INDEX_ON_STARTUP=True`, `START_ORCHESTRATOR_WORKERS_ON_STARTUP=True`, `FIREBASE_ENABLED=False`, `SERVE_STATIC_FILES=False` e `LLM_RATE_LIMITS={}`.
- Inicializadores de infraestrutura usados pelo `Kernel`: SQL (`db.create_tables`, migração), Neo4j, memória vetorial, broker e Redis.
- Componentes adicionais ligados pelo `lifespan`: graph orchestrator LangGraph, loaders de prompts, `AutonomyAdminService` e bootstrap opcional do usuário de sistema.

## Saídas
- `Kernel` singleton preenchido com infraestrutura, repositórios, serviços, workers rastreados e handles internos de tarefas assíncronas.
- `app.state` com um subconjunto curado do `Kernel`: bancos, broker, manager, serviços de domínio, `goal_manager`, `workers` e, condicionalmente, `autonomy_admin_service`, `system_user_id` e `orchestrator_workers`.
- Runtime com duas superfícies de trabalho assíncrono: `kernel.workers` para objetos/serviços de fundo e `app.state.orchestrator_workers` para tasks do orquestrador iniciadas pelo `lifespan`.
- Runtime que pode chegar ao serving mesmo com partes opcionais degradadas, porque vários blocos do `lifespan` e `_start_background_processes()` registram warnings/logs em vez de abortar o processo.

## Dependências
- [[01 - Visão do Sistema/Sequência de Boot]]
- [[02 - Backend/Repositórios e Modelos]]
- [[02 - Backend/Autonomia e Workers]]
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Segurança e Infra]]

## Papel dos arquivos
- `backend/app/main.py` monta a aplicação FastAPI, registra tracing/middlewares/routers em tempo de importação, publica dependências em `app.state` e coordena startup/shutdown via `lifespan`.
- `backend/app/core/kernel.py` é o container singleton de dependências e o orquestrador do boot interno do backend.
- `backend/app/config.py` materializa `settings`, faz parsing/validação de listas e mapas usados no boot e define defaults operacionais.
- Neste escopo, `main.py` apenas chama `validate_production_secrets()`, `init_graph()` e `close_graph()`: os detalhes internos dessas rotinas ficam fora desta nota.

## Ordem real de boot
- Na importação de `backend/app/main.py`, o módulo resolve `log_file`, chama `setup_logging()`, cria `app = FastAPI(..., lifespan=lifespan)`, aplica `setup_tracing(app)`, tenta ligar Prometheus, registra middlewares e handlers, injeta o middleware opcional de `PUBLIC_API_KEY` via `getattr(settings, "PUBLIC_API_KEY", None)`, registra `actor_binding`, inclui `/api/v1`, aplica content negotiation MsgPack, expõe `/`, `/healthz`, `/health` e monta `/static` apenas se `SERVE_STATIC_FILES=True`.
- Quando o servidor entra no `lifespan`, o primeiro gate é a chamada a `validate_production_secrets()`. O contrato exato de validação fica fora do escopo desta nota, mas a posição do gate no boot é fixa: ele roda antes de qualquer inicialização do `Kernel`.
- O `lifespan` faz uma checagem não bloqueante de LangSmith. `LANGCHAIN_TRACING_V2 == "true"` sem `LANGCHAIN_API_KEY` gera warning, mas não interrompe a inicialização.
- `Kernel.startup()` reconfigura logging e executa em ordem fixa: `_init_infrastructure()` -> `_init_mas_actors()` -> `_build_dependency_graph()` -> `register_os_tools()` -> `register_ui_tools()` -> `_start_background_processes()` -> `asyncio.create_task(_run_auto_index())` se `AUTO_INDEX_ON_STARTUP` -> `asyncio.create_task(_warm_up_llms_async())` -> `_init_senses()`.
- Dentro de `_init_infrastructure()`, `db.create_tables()` e a migração via `db_migration_service` são best-effort com warning. Em seguida, o caminho crítico usa `asyncio.gather(...)` para `initialize_graph_db()`, `initialize_memory_db()`, `initialize_broker()` e `RedisManager.get_instance().initialize()`. Só depois o `Kernel` materializa `graph_db`, `memory_db`, `broker` e `agent_manager`; `_init_firebase()` roda no meio desse fluxo, mas é tolerante a falha.
- Depois do `Kernel`, o `lifespan` chama `init_graph()`, carrega prompts globais (`advanced`, `specialized`, `evolution`), publica dependências em `app.state`, tenta criar `AutonomyAdminService`, registra `kernel.workers`, tenta garantir o usuário de sistema, configura rate limits apenas quando `LLM_RATE_LIMITS` estiver preenchido e sobe workers do orquestrador por flag.
- Ainda dentro do `lifespan`, o backend agenda `startup_self_study_check()` em `asyncio.create_task()` quando `autonomy_admin_service` existe. Essa tarefa não bloqueia o boot nem é aguardada no shutdown.

## Composição de dependências no `Kernel`
- Infraestrutura raiz: `self.graph_db`, `self.memory_db`, `self.broker` e `self.agent_manager`.
- Repositórios montados manualmente: `KnowledgeRepository(graph_db)`, `MemoryRepository(memory_db)`, `AgentRepository(agent_manager)`, `TaskRepository(broker)`, `ContextRepository()`, `SandboxRepository()`, `ToolRepository()`, `CollaborationRepository()`, `LLMRepository()`, `ChatRepositorySQL()`, `OptimizationRepository()`, `PromptRepository()`, `OutboxRepository()` e `DocumentManifestRepository()`.
- Observabilidade: `self.monitor = get_health_monitor()`, `pp_handler = get_poison_pill_handler()` e `ObservabilityRepository(self.monitor, pp_handler)`.
- Serviços base: `AgentService`, `MemoryService`, `KnowledgeService`, `TaskService`, `ContextService`, `SandboxService`, `ReflexionService`, `ToolService`, `OutboxService`, `CollaborationService`, `DocumentIngestionService`, `ObservabilityService`, `OptimizationService` e `PromptService`.
- Serviços e componentes de lógica: `config_service = get_config_service()`, `LLMService(self.llm_repo, self.prompt_service)`, `AssistantService(self.llm_service)`, `GoalManager(self.memory_service)`, `AutonomyService(..., collaboration_service=self.collaboration_service, lock_service=AutonomyLockService())`, `PromptBuilderService(self.prompt_service)`, `ToolExecutorService()`, `RAGService(self.chat_repo, self.llm_service, self.memory_service)`, `ChatEventDbLogger(self.observability_repo)` e `ChatService(...)`.
- Componentes auxiliares construídos no mesmo grafo, mas não publicados em `app.state` por `main.py`: `config_service`, `chat_event_logger`, `prompt_builder_service`, `prompt_service`, `tool_executor`, `rag_service`, `scheduler`, `monitor` e `voice_manager`.

## Dependências por store dentro do `Kernel`
- Postgres:
  - base de `db`, `ChatRepositorySQL`, `PromptRepository`, `OutboxRepository`, `DocumentManifestRepository` e todos os repositórios SQL de autonomia/usuário
- Redis:
  - inicializado em `_init_infrastructure()`, mas usado principalmente por middleware e serviços de coordenação, não como repositório de domínio central do `Kernel`
- Qdrant:
  - entra via `initialize_memory_db()` e `MemoryRepository(memory_db)`
  - depois é consumido por `MemoryService`, `RAGService`, serviços de documentos e fluxos de memória específica por usuário
- Neo4j:
  - entra via `initialize_graph_db()` e `KnowledgeRepository(graph_db)`
  - depois é consumido por `KnowledgeService` e fluxos administrativos/estruturais
- RabbitMQ:
  - entra via `initialize_broker()` e `TaskRepository(broker)` e sustenta workers/outbox

## Publicação em `app.state`
- Publicados sempre após `kernel.startup()`: `graph_db`, `memory_db`, `broker`, `agent_manager`, `agent_service`, `memory_service`, `knowledge_service`, `task_service`, `context_service`, `sandbox_service`, `reflexion_service`, `tool_service`, `collaboration_service`, `document_service`, `observability_service`, `optimization_service`, `autonomy_service`, `llm_service`, `chat_service`, `assistant_service`, `outbox_service`, `goal_manager` e `workers`.
- Publicados condicionalmente: `autonomy_admin_service` se a construção local não falhar, `system_user_id` se `ensure_system_user()` retornar um identificador, e `orchestrator_workers` somente quando os workers gerenciados pelo orquestrador são iniciados.
- `autonomy_admin_service` não sai do `Kernel`: ele é montado diretamente no `lifespan` com `kernel.llm_service` e `kernel.knowledge_service`.
- Itens importantes que ficam fora de `app.state`: `prompt_service`, `prompt_builder_service`, `tool_executor`, `rag_service`, `config_service`, `scheduler`, `monitor` e os handles internos `_neural_training_task`, `_consolidation_consumer_task` e `_document_ingestion_consumer_task`.
- Esse `app.state` é o barramento usado pelas funções `get_*_service(request)` espalhadas pelos serviços e endpoints. A injeção HTTP depende desse wiring já ter acontecido no `lifespan`.

## Background processes
- Iniciados dentro do `Kernel`: `monitor.check_all_components()`, `monitor.start_monitoring(interval_seconds=30)`, `config_service.start()`, `knowledge_consolidator.start(limit=10, min_score=0.0)`, `DataHarvester.start()`, `LifeCycleWorker.start()`, `OutboxService.start(interval_seconds=5)`, `start_consolidation_worker()`, `start_document_ingestion_worker()`, `start_neural_training_worker()`, `initialize_default_jobs(self.scheduler)` e `self.scheduler.start()`.
- `DataHarvester` nasce com `MemoryConnector(self.memory_repo)` e ainda é publicado em `app.core.workers.data_harvester.harvester`, criando um ponto global de acesso fora do `Kernel`.
- `kernel.workers` rastreia apenas `knowledge_consolidator`, `data_harvester`, `life_cycle_worker` e `outbox_service` quando presente. Os handles assíncronos `_consolidation_consumer_task`, `_document_ingestion_consumer_task` e `_neural_training_task` ficam fora dessa lista.
- O conteúdo concreto dos jobs do scheduler não é definido em `kernel.py`; neste escopo, o arquivo apenas chama `initialize_default_jobs(self.scheduler)` antes de `self.scheduler.start()`.
- `AUTO_INDEX_ON_STARTUP` e o warm-up de pool LLM são disparados com `asyncio.create_task()` e não são armazenados para join/cancel explícito.
- Fora do `Kernel`, o `lifespan` também gerencia `init_graph()`, workers do orquestrador em `app.state.orchestrator_workers` e o `startup_self_study_check()` assíncrono.
- O `lifespan` pode iniciar um segundo plano de workers para filas: `start_all_workers()` sobe novamente tasks gerenciadas pelo orquestrador quando `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`.
- Não existe, nesses três arquivos, uma deduplicação cruzada entre os consumers iniciados em `_start_background_processes()` e os iniciados por `start_all_workers()`. O risco de duplicidade vem do desenho atual do boot.

## Persistência tocada por esses processos de fundo
- `knowledge_consolidator`:
  - lê Qdrant
  - grava Neo4j
  - atualiza metadata de consolidação no próprio Qdrant
- `document_ingestion_worker`:
  - lê arquivo staged em disco
  - atualiza manifesto em Postgres
  - grava chunks em Qdrant
- `outbox_service`:
  - lê/escreve Postgres
  - publica RabbitMQ
- `startup_self_study_check()`:
  - consulta/escreve Postgres
  - grava experiências em Qdrant
  - atualiza SelfMemory/Experience no Neo4j

## Shutdown
- Ao sair do `lifespan`, o app tenta cancelar cada `asyncio.Task` registrada em `app.state.orchestrator_workers`, mas não faz `await` explícito dessas tasks após o `cancel()`.
- Em seguida executa `await asyncio.shield(close_graph())`, encerrando o ciclo de vida do graph orchestrator antes do teardown do `Kernel`.
- Depois executa `await asyncio.shield(kernel.shutdown())`. O `Kernel` tenta `stop()` em cada item de `kernel.workers`, cancela `_neural_training_task`, `_consolidation_consumer_task` e `_document_ingestion_consumer_task` sem `await` do término, para o monitor, para o scheduler, chama `db.shutdown()` e fecha `graph_db`, `memory_db` e `broker` com `asyncio.gather(..., return_exceptions=True)`.
- O código não fecha explicitamente Redis, não chama teardown do `VoiceManager` e não aguarda término de tarefas fire-and-forget como auto-index, warm-up LLM e self-study de startup.
- Como `app.state.orchestrator_workers` e `kernel.workers` rastreiam conjuntos diferentes, o shutdown também desmonta duas superfícies assíncronas distintas.

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/config.py`
- `backend/app/core/agents/graph_orchestrator.py`
- `backend/app/core/security/secret_validator.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- Infraestrutura, criação de atores MAS e construção do grafo de dependências são tratadas como críticas. Falha nessas fases levanta `KernelError` e aborta o boot.
- `db.create_tables()` e a migração de schema são tolerantes a falha, mas `initialize_graph_db()`, `initialize_memory_db()`, `initialize_broker()` e `RedisManager.get_instance().initialize()` participam do mesmo `asyncio.gather(...)` crítico. Se qualquer um desses quatro falhar, o boot aborta.
- Falhas em Firebase, `VoiceManager`, carregamento de prompts globais, `AutonomyAdminService`, `ensure_system_user()`, startup de workers do orquestrador e self-study de startup são toleradas com logs; o sistema pode servir requests em modo parcialmente degradado.
- `_start_background_processes()` captura falhas globalmente, registra um health check `background_workers` como `unhealthy`, mas não aborta o boot. Isso cria um modo "API respondeu, runtime interno incompleto".
- `start_neural_training_worker()` não tem `try/except` local como os dois consumers anteriores; se falhar, cai no handler externo e degrada o startup de background inteiro.
- O comentário de `AUTO_INDEX_ON_STARTUP` sugere indexação apenas se o grafo estiver vazio, mas a checagem de vazio não aparece nesse caminho de startup; aqui a flag apenas agenda `_run_auto_index()`.
- `PUBLIC_API_KEY` é lido dinamicamente em `main.py` com `getattr(settings, "PUBLIC_API_KEY", None)`, embora não apareça como campo tipado em `AppSettings`. Isso torna o gate global de API key dependente de configuração extra fora da superfície declarada de `config.py`.
- O padrão de DI continua altamente centralizado em um único `Kernel`, o que simplifica wiring mas amplia o raio de falha de mudanças no boot.
- O boot mistura loops internos, consumers de fila e tarefas fire-and-forget sem uma única registry canônica de runtime.
- Quando o orquestrador também inicia workers no startup, o contrato HTTP de workers não revela sozinho a multiplicidade de consumers já criada pelo `Kernel`.
