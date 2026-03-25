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

## Endpoints de observabilidade

### Saúde lógica
- `GET /api/v1/observability/health/system`
  - Retorna o snapshot agregado do `HealthMonitor`.
  - Não executa checks novos.
  - Consolida `status`, `score`, `message`, `components`, `last_check` e `suggested_timeouts`.
- `POST /api/v1/observability/health/check-all`
  - Força a execução paralela de todos os checks registrados e devolve um mapa `componente -> resultado`.
- `GET /api/v1/observability/health/components/llm_router`
  - Lê estado de circuit breakers e pool de instâncias LLM.
- `GET /api/v1/observability/health/components/multi_agent_system`
  - Informa contagem de agentes, tarefas do workspace e se há project manager.
- `GET /api/v1/observability/health/components/poison_pill_handler`
  - Deveria refletir o estado do handler, mas hoje sofre com incompatibilidade de status entre `warning`/`critical` e o enum do `HealthMonitor`.

### Poison pills
- `GET /api/v1/observability/poison-pills/quarantined`
  - Lista mensagens em quarentena, com `message_id`, `queue`, `reason`, `failure_count` e `quarantined_at`.
- `POST /api/v1/observability/poison-pills/release`
  - Remove uma mensagem da quarentena; opcionalmente mantém possibilidade de retry.
- `POST /api/v1/observability/poison-pills/cleanup`
  - Limpa mensagens expiradas com base em `quarantine_duration`.
- `GET /api/v1/observability/poison-pills/stats`
  - Retorna estatísticas globais ou por fila.

### Métricas e uso
- `GET /api/v1/observability/metrics/summary`
  - Consolida apenas três blocos: LLM pool/circuit breakers, contagens do multi-agent system e saúde do poison pill handler.
  - Não devolve um snapshot amplo de Prometheus.
- `POST /api/v1/observability/metrics/ux`
  - Registra métricas Prometheus de UX (`ttft` e `latency`) e faz log estruturado.
  - Não persiste a métrica em banco.
- `GET /api/v1/observability/llm/usage`
  - Resume uso de `openai` e `google_gemini` lendo eventos de auditoria com `status=ok`.
  - Depende de `details_json` conter `input_tokens`, `output_tokens` e `cost_usd`.

### SLOs e anomalias
- `GET /api/v1/observability/slo/domains`
  - Classifica eventos de auditoria nos domínios `chat`, `rag`, `tools` e `workers`.
  - Calcula `error_rate_pct`, `availability_pct` e `latency_p95_ms`.
  - Compara contra thresholds em `settings`.
  - Marca `insufficient_data` quando o domínio não atinge `min_events`.
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
  - Lista nós `Quarantine` com metadados suficientes para triagem manual.
- `POST /api/v1/observability/graph/quarantine/promote`
  - Registra o tipo de relacionamento se necessário, cria ou atualiza a aresta e marca o nó como `promoted`.

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
- Timeline por `request_id` quando os eventos usam `trace_id`.
- Estado das tarefas rastreadas pelo orquestrador de workers.

## O que a UI `/observability` realmente mostra
- A tela Angular nao usa `GET /api/v1/observability/health/system` nem os demais endpoints principais de `api/v1/observability/*`.
- O frontend atual consome apenas:
  - `GET /api/v1/system/status`
  - `GET /api/v1/system/health/services`
  - `GET /api/v1/system/db/validate`
  - `GET /api/v1/knowledge/health`
  - `GET /api/v1/knowledge/health/detailed`
  - `POST /api/v1/knowledge/health/reset-circuit-breaker`
  - `GET /api/v1/workers/status`
  - `GET /api/v1/tasks/queue/{queue_name}`
- A secao `Modo Operador` mostra apenas:
  - workers de `app.state.orchestrator_workers`;
  - quatro filas fixas hardcoded no Angular (`router`, `agent.tasks`, `knowledge.consolidation`, `codex`).
- Os widgets mostram:
  - status do sistema em formato resumido;
  - validacao do schema do banco;
  - saude da memoria/grafo com foco em Neo4j, Qdrant e circuit breaker.

## Auto-refresh real da UI
- O toggle de auto-refresh do cabecalho controla so o painel `Modo Operador`.
- Esse painel usa polling a cada `5s` com disparo imediato (`startWith(0)`).
- Cada widget tem polling proprio de `5s`, independente do toggle da tela.
- `System Status` atualiza apenas `/system/status` no polling; `/system/health/services` fica congelado apos a carga inicial.
- `Knowledge Health` atualiza apenas o payload basico; o payload detalhado nao acompanha o refresh continuo.

## Limites reais da implementação
- O relatório de SLO lê `AuditEvent`; ele não usa `janus_domain_requests_total` nem `janus_domain_request_latency_seconds` do middleware HTTP.
- `metrics/summary` não é um dump de métricas do sistema; ele é um resumo curto de três subsistemas.
- `request_pipeline_dashboard` depende de `trace_id`; sem esse preenchimento a trilha por request desaparece.
- `graph/audit` mede higiene estrutural do grafo, não disponibilidade do Neo4j como serviço.
- A rota frontend chamada `observability` nao expoe poison pills, SLOs, anomalias, auditoria, request tracing nem higiene do grafo.
- A UI reduz o payload de workers para `name`, `state` e `running`, ocultando `exception`, `reason`, `detail`, `children` e `tracked`.
- A UI trata falha de fila com fallback local `messages=-1`; isso diferencia indisponibilidade da fila na interface, mas nao explica a causa operacional.

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
- Há duas fontes de sinal para domínio (`AuditEvent` e métricas Prometheus do middleware), mas elas não são reconciliadas em um mesmo relatório.
- A tela `/observability` pode dar a impressao de painel completo, mas ela opera sobre um subconjunto pequeno da malha de observabilidade exposta pelo backend.
- O toggle visual de auto-refresh nao pausa os widgets; quem usa a tela pode presumir congelamento total e tomar decisao sobre dados ainda mudando.
