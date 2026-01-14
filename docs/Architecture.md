# Arquitetura do Sistema

Este documento detalha a arquitetura do Janus com referência direta ao código atual e links internos para consulta rápida. Para uma visão consolidada (inclui fluxos e funções críticas), consulte o [README.md](../README.md) principal.

## Visão Geral

- API `FastAPI` expõe endpoints REST sob `/api/v1` e saúde (`/healthz`, `/readyz`). Montagem e middlewares em `janus/app/main.py:202-221`.
- Serviços de domínio coordenam lógica (LLM, Ferramentas, Memória, Aprendizado, Contexto, Observabilidade) instanciados no `lifespan` (`janus/app/main.py:83-114`).
- Núcleo cognitivo: roteamento de LLMs, memória, reflexion e meta-agente (`janus/app/core/*`).
- Workers assíncronos: consolidação, coleta e treinamento (`janus/app/main.py:153-175`).
- Infra: RabbitMQ, Neo4j e Qdrant. Conexão robusta ao broker em `janus/app/core/infrastructure/message_broker.py:30-61`.
- Observabilidade: `/metrics` e dashboards Grafana (`janus/grafana/dashboards/*.json`).

## Componentes Principais

- API e Endpoints: `janus/app/main.py`, `janus/app/api/v1/endpoints/*.py`.
  - Exemplos: `system_status.py` (status), `llm.py` (LLM), `context.py` (contexto), `observability.py` (observabilidade), `workers.py` (workers).
- Serviços de Domínio: `janus/app/services/*` (status, llm, context, observability, learning, knowledge).
- Repositórios: `janus/app/repositories/*` (Neo4j/Qdrant, cache e CBs).
- Núcleo: `janus/app/core/*` (llm_manager, memória, reflexion, meta-agente, resiliência).
- Workers: `janus/app/core/workers/*` (neural_training_worker, data_harvester, knowledge_consolidator).
- Infra: `janus/app/core/infrastructure/*` (message_broker, health_monitor, rate_limit).
- Config: `janus/app/config.py` (variáveis, validações, políticas).

## Fluxos de Dados

1) Chamada de LLM (roteamento, cache e circuit breakers)
- Cliente → `POST /api/v1/llm/invoke` → `LLMService` → `llm_manager.get_llm_client()`.
- Circuit breakers: `GET /api/v1/llm/circuit-breakers` / reset.
- Cache: `GET /api/v1/llm/cache/status` / `POST /api/v1/llm/cache/invalidate`.
- Observabilidade: latência, tokens e gastos (`janus/app/core/llm/llm_manager.py:1076-1145`).

2) Status e Saúde de Serviços
- `GET /healthz` saúde geral; `GET /readyz` readiness.
- `GET /api/v1/system/status` status detalhado.
- `GET /api/v1/system/health/services` saúde de componentes (agent, knowledge, memory, llm).

3) Workers e Orquestração
- `GET /api/v1/workers/status`, `POST /api/v1/workers/start-all`, `POST /api/v1/workers/stop-all`.
- Filas RabbitMQ e inicialização em `janus/app/main.py:150-175`.

4) Contexto e Web Search
- `GET /api/v1/context/current`, `GET /api/v1/context/web-search`.
- Cache: `GET /api/v1/context/web-cache/status`, `POST /api/v1/context/web-cache/invalidate`.

5) Observabilidade e Poison Pills
- `GET /api/v1/observability/health/system`, `GET /api/v1/observability/metrics/summary`.
- `GET /api/v1/observability/poison-pills/quarantined`, `POST /api/v1/observability/poison-pills/cleanup`, `GET /api/v1/observability/poison-pills/stats`.

## Diagramas (Descrições)

- Fluxo Cognitivo: Input → Orquestrador → (Ferramentas ↔ LLM) → Memória (Neo4j/Qdrant) → Saída.
- Data Path LLM: Frontend → API `/llm/invoke` → `LLMService` → `llm_manager` → Provider → Cache/CBs → Métricas.
- Orquestrador-Workers: API/Serviços → publish em RabbitMQ → Workers processam → Métricas.
- Observabilidade: Prometheus → Grafana; API expõe saúde/métricas.

## Decisões de Design (Justificativas)

- Orquestrador-Trabalhador: desacopla processamento intensivo; escala horizontal.
- Multi-LLM com roteamento adaptativo: custo/latência/qualidade; fallback local.
- Memória dual (Neo4j + Qdrant): grafo + vetor.
- CBs e Cache: resiliência e economia.
- API Unificada: governança sob `/api/v1`.
- Observabilidade: métricas e tracing opcionais.

## Integridade e Comportamento do Sistema

- Contratos estáveis: DTOs Pydantic em `janus/app/models/schemas.py`; validações em `janus/app/config.py`.
- Tolerância a falhas: CBs, retries, quarentena.
- Segurança: sandbox e rate limiting.
- Compatibilidade: endpoints versão `/api/v1`.
- Observabilidade contínua: health e métricas.

## Referências de Código

- Endpoints: `janus/app/api/v1/endpoints/system_status.py`, `janus/app/api/v1/endpoints/llm.py`, `janus/app/api/v1/endpoints/context.py`, `janus/app/api/v1/endpoints/observability.py`, `janus/app/api/v1/endpoints/workers.py`
- Serviços: `janus/app/services/system_status_service.py`, `janus/app/services/llm_service.py`, `janus/app/services/context_service.py`, `janus/app/services/observability_service.py`
- Repositórios: `janus/app/repositories/llm_repository.py`, `janus/app/repositories/observability_repository.py`, `janus/app/repositories/context_repository.py`
- Núcleo: `janus/app/core/llm/*`, `janus/app/core/optimization/reflexion_core.py`, `janus/app/core/workers/*`
- Infra: `janus/app/core/infrastructure/message_broker.py`, `janus/app/core/monitoring/*`
- Configs: `janus/app/config.py`, `janus/app/models/schemas.py`
