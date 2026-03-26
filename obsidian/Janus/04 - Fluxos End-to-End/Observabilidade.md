---
tipo: fluxo
dominio: observabilidade
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Observabilidade

## Objetivo
Mapear a superfície real de observabilidade exposta pelo backend: saúde lógica, métricas, auditoria, poison pills, SLOs, higiene do grafo e status de workers.

## Responsabilidades
- Consolidar sinais vindos de `HealthMonitor`, `PoisonPillHandler`, auditoria SQL, Neo4j, broker e registries de workers.
- Explicar o que cada endpoint realmente mede e o que o operador consegue inferir dele.

## Entradas
- `HealthMonitor.last_results` e checks registrados em `backend/app/core/monitoring/health_monitor.py`.
- `PoisonPillHandler` global em `backend/app/core/monitoring/poison_pill_handler.py`.
- Eventos de auditoria persistidos em `AuditEvent`.
- Estado `app.state.orchestrator_workers`.
- Consultas Neo4j de auditoria de grafo.

## Saídas
- Snapshots de saúde lógica.
- Relatórios operacionais por domínio.
- Visões de quarentena e trilha de request.
- Sinais auxiliares para auto-healing.

## Dependências
- [[03 - Frontend/Observability Frontend]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Componentes reais
- `ObservabilityService` é a camada de orquestração e instrumentação Prometheus do domínio observability.
- `ObservabilityRepository` lê `HealthMonitor`, `PoisonPillHandler`, banco SQL e Neo4j.
- `HealthMonitor` mantém o último snapshot dos componentes e recalcula score global.
- `PoisonPillHandler` rastreia falhas por mensagem, quarentena e estatísticas por fila.
- `DomainSLOMetricsMiddleware` incrementa métricas Prometheus por domínio HTTP, mas o relatório de SLO não lê essas métricas.
- `auto_healer` consome os snapshots do `HealthMonitor` e tenta corrigir broker, fila, poison pills e LLM router.
- Famílias Prometheus realmente emitidas nesse recorte:
  - `HealthMonitor`: `component_health_status`, `system_health_score`, `health_check_duration_seconds`, `component_observed_latency_seconds`, `component_recommended_timeout_seconds`, `janus_system`.
  - `PoisonPillHandler`: `poison_pill_detected_total`, `poison_pill_quarantined_total`, `poison_pill_in_quarantine`.
  - `ObservabilityService`: `janus_observability_operations_total`, `janus_observability_operation_duration_seconds`, `janus_observability_result_items`, `janus_observability_ux_metrics_total`, `janus_observability_ux_latency_seconds`.

## Endpoints de observabilidade

### Saúde lógica
- `GET /api/v1/observability/health/system`
  - Retorna o snapshot agregado do `HealthMonitor`.
  - Não executa checks novos.
  - Consolida `status`, `score`, `message`, `components`, `last_check` e `suggested_timeouts`.
  - Se `HealthMonitor.last_results` ainda estiver vazio, responde `status=unknown`, `score=0` e `Nenhum health check executado ainda`.
- `POST /api/v1/observability/health/check-all`
  - Força a execução paralela de todos os checks registrados e devolve um mapa `componente -> resultado`.
  - Atualiza `HealthMonitor.last_results`, que passa a alimentar o health agregado.
- `GET /api/v1/observability/health/components/llm_router`
  - Executa um check novo do componente; não lê `last_results`.
  - Lê estado de circuit breakers e pool de instâncias LLM.
- `GET /api/v1/observability/health/components/multi_agent_system`
  - Executa um check novo do componente; não lê `last_results`.
  - Informa contagem de agentes, tarefas do workspace e se há project manager.
- `GET /api/v1/observability/health/components/poison_pill_handler`
  - Executa um check novo do componente; não lê `last_results`.
  - Hoje sofre com incompatibilidade de status entre `warning`/`critical` do handler e o enum `healthy`/`degraded`/`unhealthy`/`unknown` aceito pelo `HealthMonitor`.

### Poison pills
- `GET /api/v1/observability/poison-pills/quarantined`
  - Lista mensagens em quarentena, com `message_id`, `queue`, `reason`, `failure_count` e `quarantined_at`.
  - Aceita `queue` opcional para filtrar uma fila específica.
- `POST /api/v1/observability/poison-pills/release`
  - Remove uma mensagem da quarentena; opcionalmente mantém possibilidade de retry.
- `POST /api/v1/observability/poison-pills/cleanup`
  - Limpa mensagens expiradas com base em `quarantine_duration`.
  - O payload atual é mínimo: `{ "removed": <n> }`.
- `GET /api/v1/observability/poison-pills/stats`
  - Retorna estatísticas globais ou por fila.
  - Sem `queue`, devolve `total_tracked_messages`, `total_quarantined`, `by_queue` e `quarantine_duration_hours`.
  - Com `queue`, devolve `total_failures`, `total_quarantined`, `consecutive_failures` e `quarantined_count` da fila.

### Métricas e uso
- `GET /api/v1/observability/metrics/summary`
  - Consolida apenas três blocos: LLM pool/circuit breakers, contagens do multi-agent system e saúde do poison pill handler.
  - Não devolve um snapshot amplo de Prometheus.
- `GET /metrics`
  - Só existe se `prometheus_fastapi_instrumentator` estiver disponível no ambiente Python.
  - Expõe as métricas HTTP genéricas do instrumentator e as famílias customizadas de `HealthMonitor`, `PoisonPillHandler`, domínio HTTP e `ObservabilityService`.
- `POST /api/v1/observability/metrics/ux`
  - Incrementa `janus_observability_ux_metrics_total` por `outcome` e `provider`.
  - Observa `janus_observability_ux_latency_seconds` com `metric=ttft|latency` e converte ms para segundos.
  - Faz log estruturado.
  - Não persiste a métrica em banco.
- `GET /api/v1/observability/llm/usage`
  - Resume uso de `openai` e `google_gemini` lendo eventos de auditoria com `status=ok`.
  - Depende de `details_json` conter `input_tokens`, `output_tokens` e `cost_usd`.

### Superfície operacional adjacente, mas fora de `api/v1/observability/*`
- `GET /api/v1/workers/status`
  - lê apenas `app.state.orchestrator_workers`
  - não mede consumers por fila
- `POST /api/v1/workers/start-all`
  - registra o conjunto do orquestrador no estado da aplicação
- `POST /api/v1/workers/stop-all`
  - cancela só o conjunto rastreado pelo orquestrador
- `GET /api/v1/tasks/queue/{queue_name}`
  - é a única superfície HTTP simples que mostra `messages` e `consumers` reais por fila
- `GET /api/v1/tasks/queue/{queue_name}/policy`
  - mostra argumentos reais da fila
- `GET /api/v1/system/overview`
  - agrega o status simplificado de workers para o frontend operador

### SLOs e anomalias
- `GET /api/v1/observability/slo/domains`
  - Classifica eventos de auditoria nos domínios `chat`, `rag`, `tools` e `workers`.
  - Calcula `error_rate_pct`, `availability_pct` e `latency_p95_ms`.
  - Compara contra thresholds em `settings`.
  - Marca `insufficient_data` quando o domínio não atinge `min_events`.
  - Defaults atuais:
    - `chat`: erro `<= 5%`, p95 `<= 3500ms`
    - `rag`: erro `<= 5%`, p95 `<= 4500ms`
    - `tools`: erro `<= 3%`, p95 `<= 2500ms`
    - `workers`: erro `<= 3%`, p95 `<= 4000ms`
  - O payload agregado fica em `status=degraded` quando existe qualquer breach ativo; `status=insufficient_data` só aparece quando todos os domínios ficaram sem dados suficientes; caso contrário fica `ok`.
- `GET /api/v1/observability/anomalies/predictive`
  - Lê eventos de auditoria e snapshots de filas do broker.
  - Delegado ao serviço de detecção preditiva.
  - Pode retornar `disabled` por feature flag.

### Auditoria e trilha de request
- `GET /api/v1/observability/audit/events`
  - Pretende listar eventos de auditoria paginados e total.
- `GET /api/v1/observability/audit/export`
  - Pretende exportar os mesmos eventos em CSV ou JSON.
- `GET /api/v1/observability/requests/{request_id}/dashboard`
  - Agrupa eventos por `trace_id`.
  - Entrega resumo de contagens por `status`, `endpoint`, `action` e `tool`, mais timeline ordenada.
- `GET /api/v1/observability/errors/taxonomy`
  - Exibe o catálogo padronizado de erros.

### Grafo
- `GET /api/v1/observability/graph/audit`
  - Executa auditoria de higiene no Neo4j.
  - Retorna tipos de relacionamento presentes, registrados, não registrados, fora do padrão, além de `quarantine_count` e `mentions_count`.
- `GET /api/v1/observability/graph/quarantine`
  - Lista nós `Quarantine` com `node_id`, `reason`, `type`, `from_name`, `to_name`, `confidence` e `source_snippet`.
- `POST /api/v1/observability/graph/quarantine/promote`
  - Registra o tipo de relacionamento se necessário, cria ou atualiza a aresta entre nós encontrados por `name` e marca o nó `Quarantine` com `status='promoted'` e `promoted_at`.

## Health checks registrados
- `llm_router` é crítico.
- `message_broker` é crítico.
- `episodic_memory_qdrant` é crítico.
- `multi_agent_system` é não crítico.
- `poison_pill_handler` é não crítico.
- `rabbitmq_consolidation_queue_policy` é não crítico.
- `background_workers` só aparece se a inicialização de processos de fundo falhar.

## Como o status agregado é calculado
- O `score` varia de `0` a `100`.
- Cada componente `healthy` vale `1.0`; `degraded` vale `0.5`; os demais valem `0`.
- Se qualquer componente crítico estiver `unhealthy`, o sistema inteiro vira `unhealthy`.
- Sem crítico `unhealthy`, o sistema fica `healthy` com score `>= 80`, `degraded` com score `>= 50` e `unhealthy` abaixo disso.
- `GET /api/v1/observability/health/system` devolve o último snapshot; o refresh periódico vem de `monitor.start_monitoring(interval_seconds=30)` no `Kernel`.

## O que o operador realmente consegue enxergar
- Saúde lógica dos componentes centrais registrados no `HealthMonitor`.
- Quantidade e detalhes das mensagens em quarentena por poison pill.
- SLO por domínio baseado em eventos auditados, não em tráfego bruto HTTP.
- Higiene do grafo e backlog de quarentena de relações.
- Timeline por `request_id` quando os eventos usam `trace_id`, com contagens por `status`, `endpoint`, `action` e `tool`.
- Estado das tarefas rastreadas pelo orquestrador de workers, inclusive `disabled`, `composite`, `children`, `reason` e `detail` quando presentes.
- Quantidade real de consumers por fila somente quando cruza a leitura com `/api/v1/tasks/queue/{queue_name}`.

## O que a UI `/observability` realmente mostra
- A tela Angular não usa `GET /api/v1/observability/health/system` nem os demais endpoints principais de `api/v1/observability/*`.
- **Refresh real**: 
  - Toggle de auto-refresh só controla painel "Modo Operador"
  - Cada widget tem polling próprio de 5s, independente do toggle
  - `SystemStatusWidget` não refresca `servicesHealth` - fica congelado após carga inicial
  - `KnowledgeHealthWidget` não refresca `detailed` nem `recommendations` continuamente
- O frontend atual consome apenas:
  - `GET /api/v1/system/status`
  - `GET /api/v1/system/health/services`
  - `GET /api/v1/system/db/validate`
  - `GET /api/v1/knowledge/health`
  - `GET /api/v1/knowledge/health/detailed`
  - `POST /api/v1/knowledge/health/reset-circuit-breaker`
  - `GET /api/v1/workers/status`
  - `GET /api/v1/tasks/queue/{queue_name}`
- A seção `Modo Operador` mostra apenas:
  - workers de `app.state.orchestrator_workers`;
  - quatro filas fixas hardcoded no Angular (`router`, `agent.tasks`, `knowledge.consolidation`, `codex`).
- **Limitações técnicas**:
  - Filas são fixas no frontend; filas novas no backend não aparecem sem mudança de código Angular
  - UI reduz payload de workers para `name`, `state` e `running`, ocultando `exception`, `reason`, `detail`, `children`, `tracked`
  - Fallback de filas trata `messages=-1` como indisponível, mas não explica causa operacional

## Limites de Contexto vs Runtime Real
- **Workers contextuais**: UI mostra apenas `app.state.orchestrator_workers`, mas `Kernel` inicia workers adicionais não rastreados
- **Fila vs Consumers**: `/tasks/queue/{queue_name}` pode revelar mais consumers que painel de workers sugere
- **Heartbeat sintético**: `system/overview` fabrica `last_heartbeat` com `datetime.now()` e usa `tasks_processed` default `0`
- **Distinguir estados**: UI não separa visualmente:
  - Worker parado por `disabled`
  - Worker falhando com `exception` 
  - Worker composto com filhos em estados diferentes
  - Backlog por política vs erro de broker

## Limites reais da implementação
- O relatório de SLO lê `AuditEvent`; ele não usa `janus_domain_requests_total` nem `janus_domain_request_latency_seconds` do middleware HTTP.
- `metrics/summary` não é um dump de métricas do sistema; ele é um resumo curto de três subsistemas.
- `request_pipeline_dashboard` depende de `trace_id`; sem esse preenchimento a trilha por request desaparece.
- `graph/audit` mede higiene estrutural do grafo, não disponibilidade do Neo4j como serviço.
- A rota frontend chamada `observability` nao expoe poison pills, SLOs, anomalias, auditoria, request tracing nem higiene do grafo.
- A UI reduz o payload de workers para `name`, `state` e `running`, ocultando `exception`, `reason`, `detail`, `children` e `tracked`.
- A UI trata falha de fila com fallback local `messages=-1`; isso diferencia indisponibilidade da fila na interface, mas nao explica a causa operacional.

## Fluxo real de leitura de workers na operação
1. O runtime sobe loops internos do `Kernel` e, opcionalmente, o conjunto do orquestrador em `app.state.orchestrator_workers`.
2. `GET /api/v1/workers/status` enxerga apenas o segundo conjunto.
3. `GET /api/v1/system/overview` simplifica ainda mais o payload e injeta `last_heartbeat` sintético.
4. `GET /api/v1/tasks/queue/{queue_name}` pode revelar mais consumers do que o painel de workers sugere.
5. Quando há mismatch entre workers e filas, a fila é a fonte mais próxima do runtime observado.

## Lacuna observada no runtime
- No PC TESTE, em 25 de março de 2026:
  - `GET /api/v1/workers/status` retornou `tracked=21`
  - `google_productivity` apareceu como `disabled`
  - `janus.knowledge.consolidation`, `janus.document.ingestion` e `janus.neural.training` mostraram `consumers=2`
- Isso é compatível com o código: o `Kernel` sobe esses consumers e o `lifespan` pode subi-los novamente via `start_all_workers()`.
- Portanto, o operador não deve inferir cardinalidade real de consumers só a partir de `/workers/status` ou `/system/overview`.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/services/observability_service.py`
- `backend/app/repositories/observability_repository.py`
- `backend/app/core/monitoring/*`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/workers.py`

## Fluxos relacionados
- [[03 - Frontend/Observability Frontend]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Riscos/Lacunas
- `poison_pill_handler.get_health_status()` retorna `warning` e `critical`, mas `HealthMonitor.check_component()` só aceita `healthy`, `degraded`, `unhealthy` e `unknown`. Qualquer quarentena diferente de zero pode degradar para erro de parsing e aparecer como `unhealthy`.
- `GET /api/v1/observability/audit/events` e `GET /api/v1/observability/audit/export` chamam `service.get_audit_events(...)` com argumentos posicionais desalinhados. Na prática, `limit` cai no parâmetro `endpoint`, o que tende a zerar a consulta e distorcer a superfície operacional.
- `workers/status` e `system/overview` enxergam apenas `app.state.orchestrator_workers`. Os workers iniciados pelo `Kernel` e outros processos de fundo não entram nessa visão.
- `system/overview` fabrica `last_heartbeat` com `datetime.now()` e usa `tasks_processed` default `0`; isso não representa heartbeat real nem throughput real.
- `workers/status` também não distingue quando uma mesma fila foi consumida por handles iniciados em superfícies diferentes do runtime.
- Há duas fontes de sinal para domínio (`AuditEvent` e métricas Prometheus do middleware), mas elas não são reconciliadas em um mesmo relatório.
- A tela `/observability` pode dar a impressao de painel completo, mas ela opera sobre um subconjunto pequeno da malha de observabilidade exposta pelo backend.
- O toggle visual de auto-refresh nao pausa os widgets; quem usa a tela pode presumir congelamento total e tomar decisao sobre dados ainda mudando.
