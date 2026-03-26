---
tipo: visao
dominio: sistema
camada: startup
fonte-de-verdade: codigo
status: ativo
---

# Sequência de Boot

## Objetivo
Registrar a ordem real de inicialização e encerramento do backend, distinguindo o que acontece na montagem do app, no `lifespan` e dentro do `Kernel`.

## Responsabilidades
- Mostrar a ordem de boot efetivamente executada pelo código.
- Separar fases críticas de degradações toleradas.
- Explicitar onde o runtime publica dependências e onde ele apenas agenda tarefas em background.

## Entradas
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/config.py`
- Chamadas externas feitas por `main.py` durante o boot: `validate_production_secrets()`, `init_graph()` e `close_graph()`

## Saídas
- Checklist operacional de startup/shutdown com pontos de bloqueio e degradação.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[02 - Backend/Segurança e Infra]]

## Fase de montagem do app
1. `backend/app/main.py` é importado, escolhe `log_file` e chama `setup_logging()` antes mesmo do `lifespan`.
2. O módulo cria `app = FastAPI(..., lifespan=lifespan)` com `title` e `version` vindos de `settings`.
3. Ainda em tempo de importação, o código aplica `setup_tracing(app)`, instrumentação Prometheus se a dependência existir, middlewares, handlers de exceção, router `/api/v1`, middleware opcional de `PUBLIC_API_KEY` via `getattr(settings, "PUBLIC_API_KEY", None)`, `actor_binding`, content negotiation com MsgPack, health endpoints e static serving opcional.
4. `config.py` já entra nesse ponto com alguns defaults que influenciam a superfície HTTP: `SERVE_STATIC_FILES=False`, `TAILSCALE_SERVE_ENABLED=False` e `CORS_ALLOW_ORIGINS` preenchido automaticamente com localhost em ambiente não produtivo quando a lista vier vazia.

## Fase de startup (`lifespan`, antes do `yield`)
1. `validate_production_secrets()` roda primeiro. O detalhe da política de validação fica fora do escopo desta nota, mas o posicionamento do gate é inequívoco: nada do `Kernel` sobe antes dele.
2. O `lifespan` valida a configuração de LangSmith. Falta de `LANGCHAIN_API_KEY` com `LANGCHAIN_TRACING_V2 == "true"` gera warning, não aborta.
3. `Kernel.get_instance().startup()` executa a sequência interna do backend.
4. Dentro do `Kernel`, `_init_infrastructure()` tenta `db.create_tables()`, tenta migração via `db_migration_service`, inicializa `graph_db`, `memory_db`, broker e Redis em um `asyncio.gather(...)` crítico, tenta Firebase e então materializa `graph_db`, `memory_db`, `broker` e `agent_manager`.
5. Ainda no `Kernel`, `_init_mas_actors()` cria `PROJECT_MANAGER`, `CODER`, `RESEARCHER` e `SYSADMIN` se `INIT_MAS_AGENTS_ON_STARTUP` não estiver desabilitado. O default em `config.py` é subir esses atores.
6. `_build_dependency_graph()` monta repositórios, serviços, `GoalManager`, stack de chat, observabilidade, `config_service` e os componentes auxiliares de chat/RAG.
7. O `Kernel` registra ferramentas OS/UI, sobe monitor, config service, consolidadores, ingestion/training workers, outbox e scheduler. Depois agenda auto-index e warm-up LLM em background e tenta inicializar `VoiceManager`.
8. De volta ao `lifespan`, o app chama `init_graph()`, carrega prompts globais (`load_advanced_prompts`, `load_specialized_prompts`, `load_evolution_prompts`) e tolera falhas nesses loaders com log.
9. O app publica dependências do `Kernel` em `app.state`, incluindo bancos, broker, manager, serviços, `goal_manager` e `workers`.
10. O app monta `AutonomyAdminService` diretamente no `lifespan`, tenta garantir o usuário de sistema, configura rate limits só quando `LLM_RATE_LIMITS` está preenchido, sobe workers do orquestrador quando `START_ORCHESTRATOR_WORKERS_ON_STARTUP` está ativo e agenda o self-study check de startup.

## Dependências de persistência materializadas no boot
- `graph_db`, `memory_db`, broker e Redis entram todos no caminho crítico de `_init_infrastructure()`.
- Em termos de código, `initialize_graph_db()`, `initialize_memory_db()`, `initialize_broker()` e `RedisManager.get_instance().initialize()` são aguardados juntos antes do backend poder servir tráfego.
- `db.create_tables()` e a migração de schema são tentativas tolerantes a falha antes desse bloco crítico.
- Firebase é opcional: só tenta inicializar quando `FIREBASE_ENABLED` e `FIREBASE_CREDENTIALS_PATH` estiverem preenchidos, e falhas ali não derrubam o boot.

## Fase de serving
- Depois do `yield`, o app passa a servir requests usando `request.app.state.*` como fonte de serviços para várias funções `get_*_service(request)`.
- `app.state.orchestrator_workers` não existe por padrão; ele só aparece quando o boot ou o endpoint de workers efetivamente iniciam essas tarefas.
- `kernel.workers` e `app.state.orchestrator_workers` representam conjuntos diferentes: o primeiro contém objetos/serviços de fundo do `Kernel`, o segundo rastreia tarefas do orquestrador HTTP-controláveis.
- `autonomy_admin_service` também não é garantido: ele só existe em `app.state` se a construção local no `lifespan` não falhar.

## Degradação por store observada no código
- Postgres:
  - o boot tolera falha em `create_tables()` e na migração, mas vários repositórios e serviços SQL assumem que a camada estará utilizável depois
- Redis:
  - participa do `asyncio.gather(...)` crítico da infraestrutura; falha aqui aborta o boot
- Qdrant / memory DB:
  - participa do `asyncio.gather(...)` crítico da infraestrutura; falha aqui aborta o boot
- Neo4j / graph DB:
  - participa do `asyncio.gather(...)` crítico da infraestrutura; falha aqui aborta o boot
- RabbitMQ / broker:
  - participa do `asyncio.gather(...)` crítico da infraestrutura; falha aqui aborta o boot

## Fase de shutdown
1. O `lifespan` tenta cancelar cada task presente em `app.state.orchestrator_workers`.
2. O app executa `close_graph()` sob `asyncio.shield()`.
3. O app executa `kernel.shutdown()` também sob `asyncio.shield()`.
4. O `Kernel` para workers rastreados, cancela handles internos de treinamento/consumo sem aguardar join explícito, para monitor e scheduler, fecha SQL e depois fecha `graph_db`, `memory_db` e `broker`.

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/core/agents/graph_orchestrator.py`
- `backend/app/config.py`
- `backend/app/core/security/secret_validator.py`

## Fluxos relacionados
- [[02 - Backend/Autonomia e Workers]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[02 - Backend/LLM Routing e Prompts]]

## Riscos/Lacunas
- Abortam o boot: falha no gate inicial `validate_production_secrets()`, falhas em infraestrutura crítica, falhas na criação de agentes MAS e falhas na montagem do grafo de dependências do `Kernel`.
- Degradam sem abortar: prompts globais, Firebase, `VoiceManager`, `AutonomyAdminService`, usuário de sistema, workers do orquestrador e self-study de startup.
- `_start_background_processes()` pode falhar e apenas registrar `background_workers` como `unhealthy`, deixando a API viva com runtime interno incompleto.
- Auto-index, warm-up LLM e self-study de startup são agendados em background sem coordenação explícita de shutdown.
- `START_ORCHESTRATOR_WORKERS_ON_STARTUP=True` por default e o `Kernel` também inicia consumers próprios; sem uma registry única, o desenho do boot aceita duplicidade potencial de workers.
