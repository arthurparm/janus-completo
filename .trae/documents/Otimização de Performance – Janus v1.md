## Visão Geral
- Backend `FastAPI` com métricas Prometheus, CORS e middlewares: `janus/app/main.py:67-210`
- Inicialização paralela de Neo4j, Qdrant, RabbitMQ e workers: `janus/app/main.py:72,141-166`
- Routers v1 e flag para API mínima: `janus/app/api/v1/router.py:1-27`
- Frontend Angular com build e deploy via CI: `.github/workflows/action-locaweb.yml:41-60`

## Fase 1: Quick Wins (baixo risco, alto impacto)
1. Qdrant assíncrono
- Migrar `scroll` e `search` usados em funções `async` para `AsyncQdrantClient` (`janus/app/db/vector_store.py:69-79,129-156`)
- Alvos imediatos: `memory_core.arecall` `janus/app/core/memory/memory_core.py:237-248` e loop de consolidação `janus/app/core/workers/knowledge_consolidator_worker.py:483-489`
2. Executor LLM
- Substituir `ThreadPoolExecutor` por pool singleton por provider/role, evitando criação por requisição: `janus/app/core/llm/llm_manager.py:961-969,1172-1181`
- Avaliar uso de clients assíncronos quando o provider suportar
3. Tools HTTP assíncronas
- Trocar `requests` por `httpx.AsyncClient` em ferramentas: `janus/app/core/tools/action_module.py:161`
4. Logging e sampling
- Garantir nível `INFO` em produção e sampling para eventos de alta frequência: `janus/app/core/infrastructure/logging_config.py:84-121`
5. Rate Limit
- Substituir `threading.Lock` por `asyncio.Lock` ou shard por chave (bucket): `janus/app/core/infrastructure/rate_limit_middleware.py:32-86`

## Fase 2: Otimizações Estruturais
1. Batching no Neo4j
- Agrupar `MERGE` de entidades/relacionamentos em transações únicas, reduzindo N+1: `janus/app/core/workers/knowledge_consolidator_worker.py:269-339`; usar `AsyncTransaction` via `janus/app/db/graph.py:122-131`
2. Cache de curto prazo
- Limitar custo da similaridade (O(n)) com pré-filtros ou LSH; ajustar `MEMORY_SHORT_MAX_ITEMS` `janus/app/config.py:55` conforme perfil real: `janus/app/core/memory/memory_core.py:216-230`
3. Montagem de estáticos
- Se o backend servir front, montar `StaticFiles` com `Cache-Control`; caso contrário, manter CDN/servidor estático. Import já presente: `janus/app/main.py:52`
4. Timeouts e retries
- Homologar timeouts de LLM (`janus/app/config.py:74`), Qdrant e Neo4j com circuit breakers/resilientes: `janus/app/core/infrastructure/resilience.py`

## Fase 3: Observabilidade e Testes de Carga
1. Métricas e dashboards
- Usar métricas existentes: LLM, DB, broker, cache (`janus/app/core/llm/llm_manager.py:20-43,180-228`; `janus/app/db/graph.py:16-18`; `janus/app/core/infrastructure/message_broker.py:18-21`; `janus/app/core/llm/response_cache.py:26-29`)
- Validar painéis Grafana: `janus/grafana/dashboards/*.json`
2. Perf profiling
- APM/OpenTelemetry para latências por rota e spans (correlação já prevista): `janus/app/core/infrastructure/logging_config.py:39-50`
- Coletar p95/p99, throughput, erro
3. Testes de carga
- Definir cenários críticos (conversa, busca de memória, consolidação) e metas; usar ferramenta de carga (Locust/k6)

## Critérios de Aceite
- p95 de rotas principais dentro de alvo definido
- Ausência de bloqueios no event loop nas rotas principais
- Redução de round-trips Neo4j (queda significativa em contagem de queries por operação)
- Utilização estável de CPU/Memória, sem contenção de locks

Confirma este plano? Se sim, sigo com a execução da Fase 1 e entrego patches verificáveis e testes de carga mínimos para validação.