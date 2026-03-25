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
- Flags de startup como `INIT_MAS_AGENTS_ON_STARTUP`, `AUTO_INDEX_ON_STARTUP`, `START_ORCHESTRATOR_WORKERS_ON_STARTUP`, `FIREBASE_ENABLED` e `LLM_RATE_LIMITS`.
- Inicializadores de infraestrutura usados pelo `Kernel`: SQL (`db.create_tables`, migração), Neo4j, memória vetorial, broker e Redis.
- Componentes adicionais ligados pelo `lifespan`: graph orchestrator LangGraph, loaders de prompts, `AutonomyAdminService` e bootstrap opcional do usuário de sistema.

## Saídas
- `Kernel` singleton preenchido com infraestrutura, repositórios, serviços, workers rastreados e handles internos de tarefas assíncronas.
- `app.state` com bancos, broker, manager e serviços usados por dependências `Depends(...)`.
- Graph orchestrator inicializado para persistência de estado com fallback degradado se o saver em Postgres falhar.
- Runtime com monitoramento, scheduler e workers de fundo ativos, ou explicitamente degradado por warnings/logs quando a falha é tolerada.

## Dependências
- [[01 - Visão do Sistema/Sequência de Boot]]
- [[02 - Backend/Repositórios e Modelos]]
- [[02 - Backend/Autonomia e Workers]]
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Segurança e Infra]]

## Papel dos arquivos
- `backend/app/main.py` monta a aplicação FastAPI, registra tracing/middlewares/routers em tempo de importação e coordena startup/shutdown via `lifespan`.
- `backend/app/core/kernel.py` é o container singleton de dependências e o orquestrador do boot interno do backend.
- `backend/app/config.py` materializa `settings`, faz parsing/validação de flags usadas no boot e define defaults operacionais.
- `backend/app/core/agents/graph_orchestrator.py` inicializa o fluxo LangGraph com persistência em Postgres ou fallback em memória.
- `backend/app/core/security/secret_validator.py` aplica o gate de segredos inseguros antes do restante do startup.

## Ordem real de boot
- Na importação de `backend/app/main.py`, o módulo resolve `log_file`, chama `setup_logging()`, cria `app = FastAPI(..., lifespan=lifespan)`, aplica `setup_tracing(app)`, tenta ligar Prometheus, registra middlewares, handlers de exceção, routers, health endpoints, content negotiation e static serving opcional.
- Quando o servidor entra no `lifespan`, o primeiro gate é `validate_production_secrets()`. Em ambiente diferente de `production`, a validação apenas registra skip. Em `production`, o boot aborta se `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD` ou `AUTH_JWT_SECRET` ainda estiverem em valores inseguros conhecidos.
- O `lifespan` faz uma checagem não bloqueante de LangSmith. `LANGCHAIN_TRACING_V2 == "true"` sem `LANGCHAIN_API_KEY` gera warning, mas não interrompe a inicialização.
- `Kernel.startup()` executa em ordem fixa: `_init_infrastructure()` -> `_init_mas_actors()` -> `_build_dependency_graph()` -> `register_os_tools()` -> `register_ui_tools()` -> `_start_background_processes()` -> `asyncio.create_task(_run_auto_index())` se `AUTO_INDEX_ON_STARTUP` -> `asyncio.create_task(_warm_up_llms_async())` -> `_init_senses()`.
- Depois do `Kernel`, o `lifespan` inicializa o graph orchestrator com `init_graph()`, carrega prompts globais (`advanced`, `specialized`, `evolution`), publica dependências em `app.state`, tenta criar `AutonomyAdminService`, registra `kernel.workers`, tenta garantir o usuário de sistema, configura rate limits e sobe workers do orquestrador por flag.
- Ainda dentro do `lifespan`, o backend agenda `startup_self_study_check()` em `asyncio.create_task()` quando `autonomy_admin_service` existe. Essa tarefa não bloqueia o boot nem é aguardada no shutdown.

## Composição de dependências no `Kernel`
- Infraestrutura raiz: `self.graph_db`, `self.memory_db`, `self.broker` e `self.agent_manager`.
- Repositórios montados manualmente: `KnowledgeRepository(graph_db)`, `MemoryRepository(memory_db)`, `AgentRepository(agent_manager)`, `TaskRepository(broker)`, `ContextRepository()`, `SandboxRepository()`, `ToolRepository()`, `CollaborationRepository()`, `LLMRepository()`, `ChatRepositorySQL()`, `OptimizationRepository()`, `PromptRepository()`, `OutboxRepository()` e `DocumentManifestRepository()`.
- Observabilidade: `self.monitor = get_health_monitor()`, `pp_handler = get_poison_pill_handler()` e `ObservabilityRepository(self.monitor, pp_handler)`.
- Serviços base: `AgentService`, `MemoryService`, `KnowledgeService`, `TaskService`, `ContextService`, `SandboxService`, `ReflexionService`, `ToolService`, `OutboxService`, `CollaborationService`, `DocumentIngestionService`, `ObservabilityService`, `OptimizationService` e `PromptService`.
- Serviços de lógica: `LLMService(self.llm_repo, self.prompt_service)`, `AssistantService(self.llm_service)`, `GoalManager(self.memory_service)`, `AutonomyService(...)`, `PromptBuilderService(self.prompt_service)`, `ToolExecutorService()`, `RAGService(self.chat_repo, self.llm_service, self.memory_service)` e `ChatService(...)`.
- Componentes auxiliares construídos no mesmo grafo, mas não publicados em `app.state` por `main.py`: `config_service`, `chat_event_logger`, `prompt_builder_service`, `prompt_service`, `tool_executor`, `rag_service`, `scheduler`, `monitor` e `voice_manager`.

## Publicação em `app.state`
- Publicados sempre após `kernel.startup()`: `graph_db`, `memory_db`, `broker`, `agent_manager`, `agent_service`, `memory_service`, `knowledge_service`, `task_service`, `context_service`, `sandbox_service`, `reflexion_service`, `tool_service`, `collaboration_service`, `document_service`, `observability_service`, `optimization_service`, `autonomy_service`, `llm_service`, `chat_service`, `assistant_service`, `outbox_service`, `goal_manager` e `workers`.
- Publicados condicionalmente: `autonomy_admin_service` se a construção local não falhar, `system_user_id` se `ensure_system_user()` retornar um identificador, e `orchestrator_workers` somente quando os workers gerenciados pelo orquestrador são iniciados.
- Esse `app.state` é o barramento usado pelas funções `get_*_service(request)` espalhadas pelos serviços e endpoints. A injeção HTTP depende desse wiring já ter acontecido no `lifespan`.

## Background processes
- Iniciados dentro do `Kernel`: `monitor.check_all_components()`, `monitor.start_monitoring(interval_seconds=30)`, `config_service.start()`, `knowledge_consolidator.start(limit=10, min_score=0.0)`, `DataHarvester.start()`, `LifeCycleWorker.start()`, `OutboxService.start(interval_seconds=5)`, `start_consolidation_worker()`, `start_document_ingestion_worker()`, `start_neural_training_worker()`, `initialize_default_jobs(self.scheduler)` e `self.scheduler.start()`.
- `kernel.workers` rastreia apenas `knowledge_consolidator`, `data_harvester`, `life_cycle_worker` e `outbox_service` quando presente. Os handles assíncronos `_consolidation_consumer_task`, `_document_ingestion_consumer_task` e `_neural_training_task` ficam fora dessa lista.
- `AUTO_INDEX_ON_STARTUP` e o warm-up de pool LLM são disparados com `asyncio.create_task()` e não são armazenados para join/cancel explícito.
- Fora do `Kernel`, o `lifespan` também gerencia `init_graph()`, workers do orquestrador em `app.state.orchestrator_workers` e o `startup_self_study_check()` assíncrono.

## Shutdown
- Ao sair do `lifespan`, o app tenta cancelar cada `asyncio.Task` registrada em `app.state.orchestrator_workers`.
- Em seguida executa `await asyncio.shield(close_graph())`, fechando o checkpointer do graph orchestrator quando ele usa `AsyncPostgresSaver`.
- Depois executa `await asyncio.shield(kernel.shutdown())`. O `Kernel` tenta `stop()` em cada item de `kernel.workers`, cancela `_neural_training_task`, `_consolidation_consumer_task` e `_document_ingestion_consumer_task`, para o monitor, para o scheduler, chama `db.shutdown()` e fecha `graph_db`, `memory_db` e `broker` com `asyncio.gather(..., return_exceptions=True)`.
- O código não fecha explicitamente Redis, não chama teardown do `VoiceManager` e não aguarda término de tarefas fire-and-forget como auto-index, warm-up LLM e self-study de startup.

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
- `init_graph()` degrada para `MemorySaver` quando o saver em Postgres falha. O app sobe, mas perde persistência durável do estado do grafo nesse processo.
- Falhas em Firebase, `VoiceManager`, carregamento de prompts globais, `AutonomyAdminService`, `ensure_system_user()`, startup de workers do orquestrador e self-study de startup são toleradas com logs; o sistema pode servir requests em modo parcialmente degradado.
- `_start_background_processes()` captura falhas globalmente, registra um health check `background_workers` como `unhealthy`, mas não aborta o boot. Isso cria um modo "API respondeu, runtime interno incompleto".
- O comentário de `AUTO_INDEX_ON_STARTUP` sugere indexação apenas se o grafo estiver vazio, mas a checagem de vazio não aparece nesse caminho de startup; aqui a flag apenas agenda `_run_auto_index()`.
- O padrão de DI continua altamente centralizado em um único `Kernel`, o que simplifica wiring mas amplia o raio de falha de mudanças no boot.
