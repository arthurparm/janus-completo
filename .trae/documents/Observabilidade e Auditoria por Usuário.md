## Objetivo
- Implementar observabilidade e auditoria centradas no usuário: correlação por `TRACE_ID` e `user_id`, spans por ação/ferramenta, métricas e trilhas de auditoria consultáveis.

## Escopo e Resultados
- Correlação automática de `TRACE_ID`/`user_id` em logs, traces e métricas.
- Painéis Grafana por usuário (latência, erros, top ações/ferramentas).
- Endpoints de auditoria e atividade por usuário com filtros.
- Conformidade com privacidade/retenção e mascaramento de segredos.

## Implementação Técnica
### 1) Contexto e Correlação
- Middleware de correlação: estender `CorrelationMiddleware` para extrair `X-User-Id` e bind em contexto (`structlog.contextvars.bind_contextvars(user_id=...)`).
  - Referências: `janus/app/core/infrastructure/correlation_middleware.py:10-24`.
- ContextVar para `USER_ID` + processador de log: espelhar padrão de `TRACE_ID`.
  - Referências: `janus/app/core/infrastructure/logging_config.py:19,38-51`.
- Preencher `request.state.correlation_id` com o mesmo ID do request.
  - Referências: `janus/app/api/problem_details.py:39-53` (usa `request.state.correlation_id`); alinhar com middleware.

### 2) Logging Estruturado
- Incluir `user_id`, `session_id`, `conversation_id` nos logs via processador.
- Garantir redação de segredos ativa.
  - Referências: `janus/app/core/infrastructure/logging_config.py:57-74`.
- Desativar sampling para eventos de auditoria.
  - Referências: `janus/app/core/infrastructure/logging_config.py:85-122`.
- Considerar sink de logs (Loki/ELK) opcional para centralização.

### 3) Tracing (OTEL)
- Ativar OTEL e propagar atributos `trace_id`, `user_id`, `session_id` em spans.
  - Referências: `janus/app/core/infrastructure/logging_config.py:123-146`, `janus/app/main.py:216`.
- Instrumentar pontos críticos: ferramentas, LLM, memória, broker.
  - LLM: `janus/app/core/llm/llm_manager.py` (métodos principais)
  - Vetor/Grafo: `janus/app/db/vector_store.py`, `janus/app/db/graph.py`
  - Broker: `janus/app/core/infrastructure/message_broker.py:69-123`

### 4) Métricas Prometheus por Usuário
- Confirmar e ampliar métricas existentes (requests, latência, erros) com label `user_id` quando aplicável.
  - Exposição: `janus/app/main.py:219`.
- Completar métricas referenciadas por dashboards:
  - `memory_operations_total` (memória): implementar contadores na camada de memória.
  - `llm_cache_hits_total`/`llm_cache_requests_total` (cache LLM): adicionar contadores no cache/roteador.
- Manter métrica de resiliência e multi-agente com labels úteis.
  - Referências: `janus/app/core/infrastructure/resilience.py:38-62`, `janus/app/core/agents/multi_agent_system.py:174-192`.

### 5) Auditoria Persistente
- Repositório de auditoria: persistir eventos por usuário (ação, endpoint, tool, status, latência, `trace_id`).
  - Estender `ObservabilityRepository`/`Service` com CRUD de auditoria.
  - Referências: `janus/app/repositories/observability_repository.py:88-167,169-229`, `janus/app/services/observability_service.py:32-130`.
- Endpoints:
  - `GET /audit/user` com filtros (`user_id`, período, ferramenta, status) e paginação.
  - `GET /metrics/user`, `GET /activity/user` já existentes; padronizar `user_id` via header e contexto.
  - Referências: `janus/app/api/v1/endpoints/observability.py:108-125,137-140,150-153`.

### 6) Dashboards Grafana centrados no usuário
- Criar painel “Janus User Overview”:
  - Latência por ação: `increase(metric_latency_seconds_bucket{user_id=...}[5m])`.
  - Erros por ferramenta: `sum by (tool,user_id)(metric_errors_total)`.
  - Top ferramentas/ações: `topk(...)` por `user_id`.
- Validar e ajustar `janus-overview.json` e `janus-llm-performance.json` para suportar labels de usuário.
  - Referências: `janus/grafana/dashboards/janus-overview.json`, `janus/grafana/dashboards/janus-llm-performance.json`.

### 7) Segurança, Privacidade e Retenção
- Redação de PII nos logs, revisão de headers sensíveis.
- RBAC para endpoints de auditoria.
- Retenção configurável por usuário/grupo; export de auditoria.

## Modificações Planejadas (pontos no código)
- `logging_config.py`: adicionar `USER_ID` `ContextVar` e processador; ativar OTEL conforme envs.
  - `janus/app/core/infrastructure/logging_config.py:19,38-51,123-146`.
- `correlation_middleware.py`: bind de `user_id` e `request.state.correlation_id`.
  - `janus/app/core/infrastructure/correlation_middleware.py:10-24`.
- `problem_details.py`: garantir leitura correta de `trace_id` do `request.state`.
  - `janus/app/api/problem_details.py:20,39-53`.
- `observability_repository.py`/`service.py`/`observability.py`: novos métodos/endpoints de auditoria e padronização de `user_id`.
  - `janus/app/repositories/observability_repository.py:88-229`, `janus/app/services/observability_service.py:32-130`, `janus/app/api/v1/endpoints/observability.py:90-153`.
- Métricas faltantes: implementar nos módulos de memória/LLM cache.
  - `janus/app/core/llm/llm_manager.py`, `janus/app/core/memory/memory_core.py`.
- `main.py`: confirmar `setup_logging()` e `setup_tracing(app)`.
  - `janus/app/main.py:68,216,219,240-246`.

## Configuração/DevOps
- Env vars: `OTEL_ENABLED=true`, `OTEL_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces`, `OTEL_SERVICE_NAME=janus`.
  - `janus/app/config.py:262-266`.
- Prometheus já provisionado; Grafana com dashboards na pasta `Janus`.
  - `janus/grafana/provisioning/datasources/datasource.yml:4-9`, `dashboards.yml:3-13`.

## Critérios de Aceitação
- Tracing completo por conversa/ação com `TRACE_ID` e `user_id` presentes.
- Painel por usuário com latência, erros e atividade.
- Endpoints de auditoria retornam eventos com paginação e filtros.
- Logs estruturados com mascaramento de segredos e sem sampling para auditoria.

## Marcos
- Fase 1: Correlação e logging (middleware, processadores, ProblemDetails).
- Fase 2: Tracing OTEL e métricas por usuário (inclui métricas faltantes).
- Fase 3: Auditoria persistente e dashboards por usuário.

## Riscos e Mitigações
- PII em logs: reforçar redator e revisar campos.
- Custo de cardinalidade `user_id` nas métricas: usar amostragem controlada e limites.
- Dependência de DB: adicionar fallback e retentativas em repositório.

## Verificação
- Testes de integração para correlação (`TRACE_ID`/`user_id`) e endpoints de auditoria.
- Validação dos dashboards com dados sintéticos e tráfego de carga controlado.
- Inspeção de logs/traces para confirmar atributos presentes e consistentes.