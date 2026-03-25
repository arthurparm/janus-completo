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
- `backend/app/core/agents/graph_orchestrator.py`
- `backend/app/core/security/secret_validator.py`

## Saídas
- Checklist operacional de startup/shutdown com pontos de bloqueio e degradação.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[02 - Backend/Segurança e Infra]]

## Fase de montagem do app
1. `backend/app/main.py` é importado, escolhe `log_file` e chama `setup_logging()` antes mesmo do `lifespan`.
2. O módulo cria `app = FastAPI(..., lifespan=lifespan)` com `title` e `version` vindos de `settings`.
3. Ainda em tempo de importação, o código aplica `setup_tracing(app)`, instrumentação Prometheus se a dependência existir, middlewares, handlers de exceção, router `/api/v1`, middleware opcional de `PUBLIC_API_KEY`, `actor_binding`, content negotiation com MsgPack, health endpoints e static serving opcional.

## Fase de startup (`lifespan`, antes do `yield`)
1. `validate_production_secrets()` roda primeiro. Só bloqueia o boot quando `ENVIRONMENT=production` e algum segredo crítico ainda está em valor inseguro conhecido.
2. O `lifespan` valida a configuração de LangSmith. Falta de `LANGCHAIN_API_KEY` com `LANGCHAIN_TRACING_V2 == "true"` gera warning, não aborta.
3. `Kernel.get_instance().startup()` executa a sequência interna do backend.
4. Dentro do `Kernel`, `_init_infrastructure()` tenta `db.create_tables()`, tenta migração via `db_migration_service`, inicializa Neo4j, memória vetorial, broker e Redis em paralelo, tenta Firebase e então materializa `graph_db`, `memory_db`, `broker` e `agent_manager`.
5. Ainda no `Kernel`, `_init_mas_actors()` cria `PROJECT_MANAGER`, `CODER`, `RESEARCHER` e `SYSADMIN` se `INIT_MAS_AGENTS_ON_STARTUP` não estiver desabilitado.
6. `_build_dependency_graph()` monta repositórios, serviços, `GoalManager`, stack de chat, observabilidade e config service.
7. O `Kernel` registra ferramentas OS/UI, sobe monitor, config service, consolidadores, ingestion/training workers, outbox e scheduler. Depois agenda auto-index e warm-up LLM em background e tenta inicializar `VoiceManager`.
8. De volta ao `lifespan`, o app inicializa o graph orchestrator com `init_graph()`. Se o saver PostgreSQL falhar, o runtime degrada para `MemorySaver`.
9. O `lifespan` carrega prompts globais (`load_advanced_prompts`, `load_specialized_prompts`, `load_evolution_prompts`). Falhas aqui são registradas e toleradas.
10. O app publica dependências do `Kernel` em `app.state`, incluindo bancos, broker, manager, serviços, `goal_manager` e `workers`.
11. O app tenta criar `AutonomyAdminService`, tenta garantir o usuário de sistema, configura rate limits quando `LLM_RATE_LIMITS` está preenchido, sobe workers do orquestrador quando `START_ORCHESTRATOR_WORKERS_ON_STARTUP` está ativo e agenda o self-study check de startup.

## Fase de serving
- Depois do `yield`, o app passa a servir requests usando `request.app.state.*` como fonte de serviços para várias funções `get_*_service(request)`.
- `app.state.orchestrator_workers` não existe por padrão; ele só aparece quando o boot ou o endpoint de workers efetivamente iniciam essas tarefas.
- `kernel.workers` e `app.state.orchestrator_workers` representam conjuntos diferentes: o primeiro contém objetos/serviços de fundo do `Kernel`, o segundo rastreia tarefas do orquestrador HTTP-controláveis.

## Fase de shutdown
1. O `lifespan` tenta cancelar cada task presente em `app.state.orchestrator_workers`.
2. O app executa `close_graph()` sob `asyncio.shield()`.
3. O app executa `kernel.shutdown()` também sob `asyncio.shield()`.
4. O `Kernel` para workers rastreados, cancela handles internos de treinamento/consumo, para monitor e scheduler, fecha SQL e depois fecha `graph_db`, `memory_db` e `broker`.

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
- Abortam o boot: segredos inseguros em `production`, falhas em infraestrutura crítica, falhas na criação de agentes MAS e falhas na montagem do grafo de dependências do `Kernel`.
- Degradam sem abortar: saver do graph em Postgres, prompts globais, Firebase, `VoiceManager`, `AutonomyAdminService`, usuário de sistema, workers do orquestrador e self-study de startup.
- `_start_background_processes()` pode falhar e apenas registrar `background_workers` como `unhealthy`, deixando a API viva com runtime interno incompleto.
- Auto-index, warm-up LLM e self-study de startup são agendados em background sem coordenação explícita de shutdown.
