---
tipo: operacao
dominio: infra
camada: saude
fonte-de-verdade: codigo
status: ativo
---

# Healthchecks e Contratos Operacionais

## Objetivo
Separar liveness de container, health lógico e status operacional da aplicação com base apenas nos endpoints e serviços reais do backend.

## Responsabilidades
- Dizer qual endpoint serve para qual tipo de decisão operacional.
- Evitar misturar "processo de pé" com "subsistema saudável".

## Entradas
- Endpoints de status e observabilidade.
- `HealthMonitor`, `SystemStatusService` e registry de workers.

## Saídas
- Mapa de contratos para probes, operadores e troubleshooting.

## Dependências
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Checklist de Validação]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Contratos por endpoint

### Liveness e prontidão mínima
- `GET /healthz`
  - Sempre responde `{"status":"ok"}`.
  - Não toca dependências, não lê `HealthMonitor`, não verifica workers.
  - É o melhor contrato de "processo web subiu e responde HTTP".
- `GET /health`
  - Responde `status`, `service`, `version`, `environment` e, se ativo, dados de Tailscale.
  - Pode incluir `build_ref`.
  - Também não executa health checks de dependências.
  - Se `PUBLIC_API_KEY` estiver configurado, `/healthz` fica fora da proteção global, mas `/health` não.

### Status operacional da aplicação
- `GET /api/v1/system/status`
  - É um snapshot do `SystemStatusService`.
  - Retorna `status: OPERATIONAL`, `timestamp`, `uptime_seconds`, dados de sistema, processo, performance e config.
  - Não consulta RabbitMQ, Qdrant, Neo4j, workers nem `HealthMonitor`.
  - Serve para inspeção operacional e inventário do runtime, não para dizer se a aplicação está funcional ponta a ponta.

### Saúde lógica de componentes
- `GET /api/v1/observability/health/system`
  - Lê o último resultado agregado do `HealthMonitor`.
  - É o endpoint mais próximo de "health lógico" do sistema.
- `POST /api/v1/observability/health/check-all`
  - Executa todos os checks na hora e atualiza o snapshot.
- `GET /api/v1/observability/health/components/*`
  - Permite inspecionar componentes individualmente.

### Saúde operacional por serviço
- `GET /api/v1/system/health/services`
  - Monta uma visão resumida para `agent`, `knowledge`, `memory` e `llm`.
  - `memory` é inferido por uso de RAM em MB, não por check funcional de storage.
  - `knowledge` e `llm` vêm de outros serviços, não do `HealthMonitor`.

### Estado agregado para tela operacional
- `GET /api/v1/system/overview`
  - Junta `system_status`, `services_status` e `workers_status`.
  - Útil para painel, mas não é uma visão canônica única da saúde.

### Estado dos workers orquestrados
- `GET /api/v1/workers/status`
  - Mostra apenas workers guardados em `app.state.orchestrator_workers`.
  - Cada worker recebe `running`, `done`, `cancelled`, `exception` e `state`.
  - Workers desativados por flag aparecem com `state=disabled`.

## Componentes de health lógico registrados
- `llm_router`
- `message_broker`
- `episodic_memory_qdrant`
- `multi_agent_system`
- `poison_pill_handler`
- `rabbitmq_consolidation_queue_policy`
- `background_workers` apenas em falha de startup de processos de fundo

## Leitura operacional
- Use `/healthz` para saber se o processo responde.
- Use `/health` para ler metadados do runtime exposto.
- Use `/api/v1/system/status` para inventário operacional do processo.
- Use `/api/v1/observability/health/system` e `/health/check-all` para saúde lógica.
- Use `/api/v1/system/health/services` e `/api/v1/system/overview` para um resumo voltado à operação humana.
- Use `/api/v1/workers/status` apenas para o subconjunto orquestrado de tarefas.

## Métricas e superfícies auxiliares
- `/metrics` só existe se `prometheus_fastapi_instrumentator` estiver disponível.
- `DomainSLOMetricsMiddleware` registra métricas Prometheus por domínio HTTP.
- `/api/v1/observability/slo/domains` não lê essas métricas; ele recalcula o SLO a partir de `AuditEvent`.

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/services/system_status_service.py`
- `backend/app/core/monitoring/health_monitor.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Mapa de Testes]]

## Riscos/Lacunas
- `/healthz` e `/health` podem parecer saudáveis enquanto broker, Qdrant, workers ou SLOs já estão degradados.
- `/api/v1/system/status` sempre retorna `OPERATIONAL` e hoje não rebaixa status por falha de dependência.
- `/api/v1/system/overview` simplifica demais o status de workers e injeta heartbeat sintético.
- O health lógico depende do snapshot periódico do `HealthMonitor`; fora de `check-all` ele não é uma execução on-demand.
- O endpoint de workers não é autoritativo para todos os processos em background iniciados pelo `Kernel`.
