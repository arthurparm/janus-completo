# Arquitetura do Sistema

Este documento descreve a arquitetura do Janus AI Architect, organizada para garantir clareza, consistência e escalabilidade. O sistema adota um paradigma multiagente com padrão Orquestrador-Trabalhador, API assíncrona, barramento de mensagens, memória hierárquica e observabilidade profunda.

## Visão Geral

- API (`FastAPI`) expõe endpoints REST sob ` /api/v1` e ` /healthz`.
- Serviços de domínio coordenam lógica (LLM, Ferramentas, Memória, Aprendizado, Contexto, Observabilidade).
- Núcleo cognitivo provê roteamento de LLMs, memória, reflexões e meta-agente.
- Workers assíncronos processam tarefas de treinamento e consolidação.
- Infraestrutura desacoplada via RabbitMQ, Neo4j (grafo) e Qdrant (vetores).
- Observabilidade com métricas Prometheus e dashboards Grafana.

## Componentes Principais

- API e Endpoints: `app/main.py`, `app/api/v1/endpoints/*.py`
  - Exemplos: `system_status.py` (status), `llm.py` (LLM), `context.py` (contexto), `observability.py` (observabilidade), `workers.py` (workers).
- Serviços de Domínio: `app/services/*`
  - `system_status_service.py`, `llm_service.py`, `context_service.py`, `observability_service.py`, `learning_service.py`, `knowledge_service.py`.
- Repositórios: `app/repositories/*`
  - Integrações e persistência (Neo4j/Qdrant), cache e circuit breakers.
- Núcleo Cognitivo: `app/core/*`
  - `llm_manager`, memória semântica, Reflexion, meta-agente, resilience utils.
- Workers: `app/core/workers/*`
  - `neural_training_worker.py`, `router_worker.py`, `data_harvester.py`.
- Infraestrutura: `app/core/infrastructure/*`
  - `message_broker.py` (RabbitMQ), `health_monitor.py`, rate limiting.
- Configuração: `app/config.py`
  - Padrões, validações e variáveis para todos os módulos.

## Fluxos de Dados

1) Chamada de LLM (roteamento, cache e circuit breakers)
- Cliente → `POST /api/v1/llm/invoke` → `llm_service` → `llm_manager` (seleção de provedor).
- Circuit breakers: `GET /api/v1/llm/circuit-breakers` e reset via serviço (quando exposto).
- Cache: `GET /api/v1/llm/cache/status` e `POST /api/v1/llm/cache/invalidate`.
- Observabilidade registra latência, erros e quotas (Prometheus).

2) Status do Sistema e Saúde de Serviços
- `GET /healthz` para saúde geral da aplicação.
- `GET /api/v1/system/status` para status detalhado (app, env, uptime, métricas).
- `GET /api/v1/system/health/services` lista serviços: Agent, Knowledge, Memory, LLM Gateway com métricas.

3) Workers e Orquestração
- `GET /api/v1/workers/status` para estado de workers rastreados.
- `POST /api/v1/workers/start-all` / `POST /api/v1/workers/stop-all` para controle operacional.
- Mensageria: filas RabbitMQ mapeadas em `message_broker.py` e inicialização em `app/main.py`.

4) Contexto e Web Search
- `GET /api/v1/context/current` retorna contexto ambiental atual.
- `GET /api/v1/context/web-search` com `query`, `max_results`, `search_depth` para pesquisa web.
- Cache web: `GET /api/v1/context/web-cache/status` e `POST /api/v1/context/web-cache/invalidate`.

5) Observabilidade e Poison Pills
- `GET /api/v1/observability/health/system`, `GET /api/v1/observability/metrics/summary`.
- `GET /api/v1/observability/poison-pills/quarantined`, `POST /api/v1/observability/poison-pills/cleanup`, `GET /api/v1/observability/poison-pills/stats`.

## Diagramas (Descrições)

- Fluxo Cognitivo: Input → Orquestrador → (Ferramentas locais ↔ LLM Cloud) → Memória (Neo4j/Qdrant) → Saída.
- Data Path LLM: Frontend → API `/llm/invoke` → `llm_service` → `llm_manager` → Provedor → Cache/CBs → Métricas.
- Orquestrador-Workers: API/Serviços → `publish` em RabbitMQ → Workers processam e emitem eventos/artefatos → Observabilidade coleta métricas.
- Observabilidade: Coletores → Prometheus → Dashboards Grafana; API expõe saúde, resumo de métricas e quarentenas.

## Decisões de Design (Justificativas)

- Orquestrador-Trabalhador: desacopla processamento intensivo e permite escala horizontal por fila/worker.
- Multi-LLM com roteamento: otimiza custo/latência/qualidade, com fallback local para resiliência.
- Memória Semântica dual (Neo4j + Qdrant): combina relações simbólicas e similaridade vetorial.
- Circuit Breakers e Cache: reduzem impacto de falhas transitórias e custos com reuso de respostas.
- API Unificada: simplifica integração e governança via `router.py` com `PUBLIC_API_MINIMAL` para modularidade.
- Observabilidade integrada: sustenta confiabilidade em produção e feedback de melhorias.

## Integridade e Comportamento do Sistema

- Contratos estáveis: DTOs Pydantic em `app/models/schemas.py` e validações em `app/config.py`.
- Tolerância a falhas: CBs, retries, DLQ/Quarentena; workers isolam falhas sem derrubar o sistema.
- Segurança operacional: sandbox para execução de ferramentas e rate limiting por IP/chave.
- Compatibilidade: endpoints versionados sob ` /api/v1`, manutenção de backward-compat quando possível.
- Observabilidade contínua: health endpoints e métricas garantem detecção e resposta rápida a anomalias.

## Referências de Código

- Endpoints: `app/api/v1/endpoints/system_status.py`, `llm.py`, `context.py`, `observability.py`, `workers.py`
- Serviços: `app/services/system_status_service.py`, `llm_service.py`, `context_service.py`, `observability_service.py`
- Repositórios: `app/repositories/llm_repository.py`, `observability_repository.py`, `context_repository.py`
- Núcleo: `app/core/llm/*`, `app/core/optimization/reflexion_core.py`, `app/core/workers/*`
- Infra: `app/core/infrastructure/message_broker.py`, `app/core/monitoring/*`
- Configs: `app/config.py`, `app/models/schemas.py`