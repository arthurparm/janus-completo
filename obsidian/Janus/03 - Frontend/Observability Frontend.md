---
tipo: dominio
dominio: frontend
camada: feature
fonte-de-verdade: codigo
status: ativo
---

# Observability Frontend

## Objetivo
Descrever o comportamento real da rota `/observability` no Angular e separar claramente o que a UI mostra do que a API de observabilidade consegue expor.

## Responsabilidades
- Mapear a composicao da tela.
- Explicar auto-refresh, operator view, widgets e servicos usados.
- Registrar limites da UI frente aos contratos backend.

## Entradas
- `frontend/src/app/features/observability/observability.ts`
- `frontend/src/app/features/observability/widgets/*`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/core/services/app-logger.service.ts`
- `frontend/src/app/app.routes.ts`

## Saidas
- Leitura operacional da tela.
- Mapa frontend -> endpoints realmente consumidos.

## Dependencias
- [[03 - Frontend/Features e Experiência]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Lacunas e Riscos]]

## Rota e composicao
- A rota e `'/observability'` e passa por `AuthGuard`.
- O componente raiz `ObservabilityComponent` monta:
  - cabecalho da tela;
  - painel `Modo Operador` com workers e filas;
  - `SystemStatusWidgetComponent`;
  - `DatabaseHealthWidgetComponent`;
  - `KnowledgeHealthWidgetComponent`.
- Nao existe service frontend dedicado para a feature. A tela injeta `BackendApiService` diretamente em cada componente e usa `AppLoggerService` apenas no componente raiz.

## Servicos frontend realmente usados
- `BackendApiService`
  - `getWorkersStatus() -> GET /api/v1/workers/status`
  - `getQueueInfo(queueName) -> GET /api/v1/tasks/queue/{queue_name}`
  - `getSystemStatus() -> GET /api/v1/system/status`
  - `getServicesHealth() -> GET /api/v1/system/health/services`
  - `getSystemDbValidate() -> GET /api/v1/system/db/validate`
  - `getKnowledgeHealth() -> GET /api/v1/knowledge/health`
  - `getKnowledgeHealthDetailed() -> GET /api/v1/knowledge/health/detailed`
  - `resetKnowledgeCircuitBreaker() -> POST /api/v1/knowledge/health/reset-circuit-breaker`
- `AppLoggerService`
  - registra no console quando o auto-refresh do painel principal liga/desliga;
  - registra erro quando o refresh agregado do operator view falha.

## Auto-refresh real
- O toggle de auto-refresh fica no componente raiz e nasce ligado (`signal(true)`).
- O toggle controla apenas o painel `Modo Operador`.
- **Comportamento por widget**:
  - `SystemStatusWidget`: atualiza apenas `systemStatus` no polling; `servicesHealth` fica congelado após carga inicial
  - `DatabaseHealthWidget`: atualiza snapshot completo de validação a cada 5s
  - `KnowledgeHealthWidget`: atualiza apenas health básico; detalhado não acompanha refresh contínuo
- O painel do operador faz polling a cada `5000ms` com `interval(...).pipe(startWith(0))`, então a primeira coleta acontece imediatamente ao montar a tela.
- Desligar o toggle cancela apenas `refreshOperatorView()`. Os três widgets continuam com seus pollings próprios.
- `getSystemStatus()` envia `ngsw-bypass: true`; os demais requests da tela não fazem esse bypass explicitamente.

## Operator view
- O painel superior junta duas fontes:
  - `workers`: resposta de `GET /api/v1/workers/status`;
  - `queues`: quatro chamadas paralelas para filas hardcoded.
- As filas monitoradas sao fixas no frontend:
  - `janus.tasks.router`
  - `janus.agent.tasks`
  - `janus.knowledge.consolidation`
  - `janus.tasks.codex`
- Para filas, o frontend trata erro individualmente e fabrica um fallback local com:
  - `name=<fila>`
  - `messages=-1`
  - `consumers=0`
- A UI interpreta:
  - `messages < 0` como `indisponivel`;
  - `messages > 0` como alerta visual;
  - `messages === 0` como fila sem backlog visivel.
- O `lastRefreshAt` reflete somente a coleta do operator view.
- Se o `forkJoin` principal falhar, a tela zera workers e filas, mostra erro textual e segue viva.

## Como a UI trata workers
- A tela usa apenas `response.workers`; ela ignora `tracked`.
- Cada item renderiza so:
  - `name`
  - `state`
  - `running`
- Campos existentes no contrato e invisiveis na UI:
  - `done`
  - `cancelled`
  - `exception`
  - `reason`
  - `detail`
  - `composite`
  - `children`
- Na pratica, isso achata workers compostos e remove a causa de falha quando ha excecao.
- Como o backend ja limita `/api/v1/workers/status` a `app.state.orchestrator_workers`, a UI fica duas vezes limitada:
  - primeiro pelo endpoint, que nao cobre todos os processos em background do `Kernel`;
  - depois pela renderizacao, que esconde parte do payload que ja chegou.

## Widgets

### System Status
- Mostra somente:
  - `status`
  - `app_name`
  - `version`
  - `environment`
  - `uptime_seconds`
  - lista simples de `services`
- A API `SystemStatus` traz tambem `timestamp`, `system`, `process`, `performance` e `config`, mas nada disso vai para a tela.
- Se `getSystemStatus()` falhar, o widget nao preenche `error`; ele so cai para `systemStatus=null` e exibe `UNKNOWN`.
- Se `getServicesHealth()` falhar, a grade de servicos fica vazia sem detalhe adicional.

### Database Validation
- Mostra resumo de itens `exists` vs `missing`, filtro local e tabela com:
  - `table`
  - `name`
  - `kind`
  - `exists`
- O campo `status` de `DbValidationResponse` nao aparece na UI.
- A tela nao oferece acao de migracao, reconciliacao ou diagnostico adicional; apenas exporta o snapshot atual para JSON.

### Knowledge Health
- Usa dois contratos diferentes:
  - `KnowledgeHealthResponse` para o estado basico e refresh continuo;
  - `KnowledgeHealthDetailedResponse` para detalhes carregados uma vez.
- Mostra conexao Neo4j/Qdrant, `total_nodes`, `total_relationships`, estado do circuit breaker e uma lista curta de recomendacoes.
- A decisao de status visual do widget e local:
  - `degraded` se o circuit breaker estiver aberto;
  - `degraded` se Neo4j ou Qdrant estiverem desconectados;
  - caso contrario usa `health.status.toLowerCase()`.
- Campos detalhados que a API entrega e a UI nao explora de verdade:
  - `basic_health`
  - `detailed_status.offline`
  - `detailed_status.metrics`
  - `monitoring`
- O reset do circuit breaker so aparece quando o breaker esta `OPEN`.

## UI versus profundidade da API
- A rota se chama observability, mas não consome os endpoints centrais de `backend/app/api/v1/endpoints/observability.py`.
- **Limites por widget**:
  - `SystemStatusWidget`: ignora campos `timestamp`, `system`, `process`, `performance`, `config` da API
  - `DatabaseHealthWidget`: não mostra campo `status` do contrato; sem ações de migração/reconciliação
  - `KnowledgeHealthWidget`: não explora campos `basic_health`, `detailed_status.offline`, `detailed_status.metrics`, `monitoring`
- A UI atual não usa:
  - `GET /api/v1/observability/health/system`
  - `POST /api/v1/observability/health/check-all`
  - `GET /api/v1/observability/metrics/summary`
  - `GET /api/v1/observability/poison-pills/*`
  - `GET /api/v1/observability/slo/domains`
  - `GET /api/v1/observability/anomalies/predictive`
  - `GET /api/v1/observability/audit/events`
  - `GET /api/v1/observability/audit/export`
  - `GET /api/v1/observability/requests/{request_id}/dashboard`
  - `GET /api/v1/observability/graph/*`
- A UI também não usa `GET /api/v1/system/overview`, embora o frontend tenha o método `getSystemOverview()`.
- Em resumo:
  - a API backend cobre saúde lógica agregada, poison pills, SLOs, auditoria, request tracing, uso de LLM e higiene do grafo;
  - a UI atual cobre apenas um painel operacional curto de workers/filas e três widgets de status.

## Limites reais da tela
- O toggle de auto-refresh nao pausa o dashboard inteiro; pausa apenas o operator view.
- `SystemStatusWidget` nao refresca `servicesHealth`, entao o bloco de servicos pode envelhecer mesmo com a pagina aberta.
- `KnowledgeHealthWidget` nao refresca `detailed` nem `recommendations` continuamente.
- As filas sao fixas no frontend; filas novas no backend nao aparecem sem mudanca de codigo Angular.
- A tela nao mostra policy de fila, poison pills, SLO por dominio, anomalias, auditoria nem pipeline por request.
- O operador nao recebe profundidade suficiente para diferenciar:
  - worker parado por `disabled`;
  - worker falhando com `exception`;
  - worker composto com filhos em estados diferentes;
  - backlog de fila por politica ou por erro de broker.

## Comportamento de Error Handling
- **Operator View**: Em falha total, zera workers e filas, mostra erro textual e continua operacional
- **SystemStatusWidget**: Falhas silenciosas com `catchError(() => of(null))`, exibe `UNKNOWN` quando `systemStatus=null`
- **DatabaseHealthWidget**: Captura mensagens de erro e exibe ao usuário
- **KnowledgeHealthWidget**: Mensagens de erro em alertas visuais
- **Fallback de filas**: Quando indisponível, fabrica `{name: <fila>, messages: -1, consumers: 0}`
- **Interpretação de filas**: `messages < 0` = indisponível, `messages > 0` = alerta visual, `messages === 0` = sem backlog

## Arquivos-fonte
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/features/observability/observability.ts`
- `frontend/src/app/features/observability/observability.html`
- `frontend/src/app/features/observability/widgets/system-status-widget/system-status-widget.ts`
- `frontend/src/app/features/observability/widgets/database-health-widget/database-health-widget.ts`
- `frontend/src/app/features/observability/widgets/knowledge-health-widget/knowledge-health-widget.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/core/services/app-logger.service.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Riscos/Lacunas
- O nome da rota sugere cockpit completo, mas a cobertura real da UI e bem menor que a superficie operacional do backend.
- O operador pode desligar o toggle achando que congelou tudo, quando os widgets continuam em polling.
- A UI nao ajuda a separar ausencia de dado, erro de integracao e estado operacional degradado em varios cenarios.
