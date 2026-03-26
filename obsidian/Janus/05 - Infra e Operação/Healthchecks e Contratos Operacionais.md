---
tipo: operacao
dominio: infra
camada: saude
fonte-de-verdade: codigo
status: ativo
---

# Healthchecks e Contratos Operacionais

## Objetivo
Separar probe de container, liveness HTTP, readiness real do processo e saúde lógica de dependências com base no comportamento executável da stack.

## Responsabilidades
- Dizer qual contrato serve para Compose, operador e troubleshooting.
- Explicitar o que o código realmente mede e o que ele não mede.
- Definir o mínimo necessário para considerar a stack funcional.

## Entradas
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/core/monitoring/health_monitor.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/services/system_status_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/llm_service.py`

## Saídas
- Matriz de contratos operacionais.
- Critérios mínimos de stack funcional.
- Regras para interpretar readiness versus degradação parcial.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Checklist de Validação]]
- [[07 - Glossário e Inventários/Inventário de Workers]]

## Camadas de health no Janus

### 1. Healthcheck de container
- É o contrato usado pelo Docker Compose para marcar um container como `healthy` ou `unhealthy`.
- Não é o contrato mais confiável para dizer que a stack inteira está funcional.

### 2. Liveness HTTP do processo
- É a prova de que o processo FastAPI está servindo requisições.
- No Janus, isso é representado por `/healthz` e, em menor grau, por `/health`.

### 3. Readiness real da aplicação
- Só existe depois que o `lifespan` terminou.
- Inclui startup do `Kernel`, infraestrutura core, LangGraph e wiring do `app.state`.
- Não coincide perfeitamente com o healthcheck do container, porque o runtime tolera vários modos offline sem abortar o processo.

### 4. Saúde lógica do sistema
- É o domínio do `HealthMonitor`.
- Mede componentes internos e dependências indiretas com score agregado.
- Pode continuar `healthy` mesmo com componente crítico em `degraded`, desde que nenhum crítico esteja `unhealthy`.

## Contratos por endpoint

| Endpoint | Camada | O que garante | Limites reais |
| --- | --- | --- | --- |
| `GET /healthz` | liveness HTTP | o processo respondeu FastAPI | não valida dependência nenhuma; bypass de `PUBLIC_API_KEY` e de rate limit |
| `GET /health` | liveness HTTP com metadados | processo respondeu e expôs `service`, `version`, `environment`, `build_ref`, Tailscale | não valida dependências; pode exigir `X-API-Key` quando `PUBLIC_API_KEY` estiver definida |
| `GET /api/v1/system/status` | inventário do processo | uptime, PID, RSS, CPU, memória, config básica | `status` é sempre `OPERATIONAL`; não consulta dependências; pode exigir `X-API-Key` quando `PUBLIC_API_KEY` estiver definida |
| `GET /api/v1/observability/health/system` | health lógico agregado | último snapshot do `HealthMonitor` | não força reexecução; antes do primeiro ciclo pode responder `unknown`; score pode esconder degradação crítica parcial |
| `POST /api/v1/observability/health/check-all` | health lógico on-demand | roda todos os checks e atualiza o snapshot | pode demorar conforme timeout dos checks; passa a alimentar `health/system` |
| `GET /api/v1/observability/health/components/*` | health lógico por componente | executa um check novo do componente solicitado | não lê `last_results` e não cobre todos os serviços do stack |
| `GET /api/v1/system/health/services` | resumo operacional | visão resumida de `agent`, `knowledge`, `memory`, `llm` | não é o mesmo conjunto do `HealthMonitor`; `agent` faz check fresco, `knowledge`/`llm` usam outros serviços, `memory` é heurística de RAM |
| `GET /api/v1/system/overview` | painel agregado | junta status do processo, serviços e workers | injeta `last_heartbeat` sintético e não é fonte canônica |
| `GET /api/v1/workers/status` | workers orquestrados | estado dos tasks registrados em `app.state.orchestrator_workers` | não cobre todos os processos internos do `Kernel`; pode exigir `X-API-Key` quando `PUBLIC_API_KEY` estiver definida |

## Readiness operacional (o que existe hoje)

### Readiness do Compose (container “healthy”)
- O Compose marca o container como `healthy`/`unhealthy` com base no healthcheck configurado no próprio compose.
- No `janus-api`, o healthcheck chama `GET /health` sem headers.

### Readiness do processo FastAPI (HTTP “de pé”)
- O processo só começa a aceitar tráfego depois que o `lifespan` termina.
- Na prática, isso significa que qualquer probe HTTP (incluindo `/healthz`) é necessariamente posterior ao startup do `Kernel` e do wiring do `app.state`.

### `/readyz` e `/livez`
- Não existem como rotas do FastAPI hoje; se chamados, retornam 404.

## Leitura correta de readiness

### `/healthz`
- Retorna sempre `{"status":"ok"}`.
- Não toca banco, fila, cache, Neo4j, Qdrant nem workers.
- É o endpoint mais seguro para probe simples de liveness.

### `/health`
- É o endpoint usado hoje pelo healthcheck do container `janus-api`.
- Só devolve metadados do processo e de Tailscale.
- Não consulta `HealthMonitor`, não toca dependências e não mede workers.
- Se `PUBLIC_API_KEY` estiver configurado, `/health` deixa de ser probe anônima válida e o container pode entrar em `unhealthy`.

### `/api/v1/system/status`
- Usa `SystemStatusService`.
- Sempre devolve `status: OPERATIONAL`.
- Serve para inventário operacional do processo, não para decisão de failover.

### `/api/v1/observability/health/system`
- Usa apenas `HealthMonitor.last_results`.
- Não substitui `check-all`; ele só lê o último estado calculado.
- `suggested_timeouts` são recomendações derivadas de latência observada e configuração, não prova de readiness.

### `/api/v1/observability/health/components/*`
- Chamam `check_component()` diretamente.
- Por isso podem divergir do snapshot agregado se o último loop do monitor ainda não incorporou a mesma condição.

## Componentes monitorados pelo `HealthMonitor`

### Críticos
- `llm_router`
- `message_broker`
- `episodic_memory_qdrant`
- `background_workers` apenas quando a inicialização falha e o kernel registra esse check

### Não críticos
- `multi_agent_system`
- `poison_pill_handler`
- `rabbitmq_consolidation_queue_policy`

## Como cada check é calculado

### `llm_router`
- Usa snapshot de circuit breakers e pool de LLMs.
- Não executa prompt de prova.

### `message_broker`
- Faz `broker.health_check()`.
- Mede conexão robusta com RabbitMQ, não vazão de fila.

### `episodic_memory_qdrant`
- Instancia `MemoryCore`, tenta `get_collection()` e, se falhar, tenta revive.
- Se revive falhar, retorna `degraded` com fallback memory-only ativo, não `unhealthy`.
- Isso é suficiente para o score agregado continuar alto.

### `multi_agent_system`
- Só confere que o objeto do sistema multiagente responde.
- Pode retornar `healthy` com `active_agents=0` quando `INIT_MAS_AGENTS_ON_STARTUP=false`.

### `poison_pill_handler`
- Reusa `PoisonPillHandler.get_health_status()`.
- O handler produz `healthy`, `warning` ou `critical`, mas `HealthMonitor.check_component()` só entende `healthy`, `degraded`, `unhealthy` e `unknown`.
- Na prática, qualquer retorno diferente de `healthy` pode estourar no parsing do enum e o componente acabar aparecendo como `unhealthy`.

### `rabbitmq_consolidation_queue_policy`
- Consulta a fila `janus.knowledge.consolidation` e compara TTL, max length e DLX.
- Mede conformidade de policy, não disponibilidade ponta a ponta do consumidor.

## Readiness do processo FastAPI

### O que precisa terminar antes de responder HTTP
- validação de segredos de produção;
- startup do `Kernel`;
- inicialização do grafo LangGraph/checkpointer;
- wiring de `app.state`.

### O que o `Kernel` trata como crítico
- criação e migração best-effort do banco SQL;
- inicialização paralela de Neo4j, Qdrant, RabbitMQ e Redis;
- construção do grafo de dependências e serviços.

### O que o runtime tolera em modo degradado
- Neo4j pode cair para offline sem abortar o processo.
- RabbitMQ pode ficar offline sem abortar o processo.
- Redis pode falhar no ping inicial sem abortar o processo.
- Qdrant, depois das tentativas de inicialização, pode cair para offline e operar em fallback local.
- Falhas de prompt loading e de alguns background workers são logadas, mas não derrubam a API.

## O que é necessário para considerar a stack funcional

### Mínimo para considerar a API de pé
- `janus-api` e `janus-frontend` em `healthy` no Compose do PC1.
- `GET /healthz` respondendo `{"status":"ok"}`.
- `GET /health` respondendo `status=ok` com `environment` e `build_ref` esperados.

### Mínimo para considerar o backend operacional
- `postgres`, `redis` e `rabbitmq` em `healthy` no PC1.
- `GET /api/v1/system/status` acessível.
- Se `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`, `/api/v1/workers/status` deve mostrar workers rastreados sem `exception`.

### Mínimo para considerar a stack Janus funcional de ponta a ponta
- `neo4j`, `qdrant` e `ollama` em `healthy` no PC2.
- Os componentes críticos do `HealthMonitor` devem estar `healthy`, não apenas o score agregado:
  - `llm_router`
  - `message_broker`
  - `episodic_memory_qdrant`
  - `background_workers`, se existir
- `/api/v1/system/health/services` não deve mostrar:
  - `knowledge=degraded`
  - `llm` fora de `healthy`
- O deploy distribuído tem de fechar com os endpoints configurados em:
  - `NEO4J_URI`
  - `QDRANT_HOST:QDRANT_PORT`
  - `OLLAMA_HOST`

### O que não basta para chamar de funcional
- `docker ps` com `janus_api` em `healthy`.
- `/healthz` em `ok`.
- `/api/v1/system/status` em `OPERATIONAL`.
- `/api/v1/observability/health/system` em `healthy` quando ainda existir componente crítico em `degraded`.

## Workers e limites do endpoint HTTP
- `/api/v1/workers/status` cobre apenas workers guardados em `app.state.orchestrator_workers`.
- `DisabledWorkerHandle` aparece como `state=disabled`, com `reason` e `detail`.
- Estruturas compostas podem aparecer com `composite=true` e `children`.
- Tasks concluídas com exceção expõem `exception` e passam para `state=error`.
- O nome devolvido vem do registro do orquestrador, não do nome real da fila.
- O endpoint não consulta RabbitMQ para confirmar o número real de consumers.
- Para confirmar consumidores por fila, a checagem real continua sendo a camada de broker e filas.

### Playbook rápido (leitura correta)
- Prova de liveness do processo: `GET /healthz`
- Prova de metadata do processo: `GET /health` e `GET /api/v1/system/status`
- Prova de workers “observados” (somente registry do orquestrador): `GET /api/v1/workers/status`
- Prova objetiva de consumers e backlog por fila: `GET /api/v1/tasks/queue/{queue_name}`
- Conclusão operacional: quando a pergunta é “tem consumer de verdade?”, a resposta vem das filas, não do endpoint de workers.

### Observação: `PUBLIC_API_KEY`
- Se `PUBLIC_API_KEY` estiver configurada, endpoints fora do bypass exigem `X-API-Key`.
- `/healthz` permanece fora dessa proteção; `/health` e os endpoints `/api/v1/*` podem exigir o header.

### Troubleshooting: workers parecem OK, mas a fila está acumulando
- Se `/api/v1/workers/status` está `running`, mas `messages` cresce em `/api/v1/tasks/queue/{queue}`:
  - confirmar `consumers` por fila (pode estar `0` mesmo com registry “ok” em outro ambiente/processo)
  - considerar duplicação de consumers quando `Kernel` e `orquestrador` iniciam a mesma fila
  - validar mismatch de vocabulário: nome observado não é nome de fila (ex.: `code_agent` consome `janus.tasks.agent.coder`)
- Se `state=error` em `/api/v1/workers/status`:
  - usar o campo `exception` como pista e cruzar com logs do container `janus-api`
  - confirmar se a fila continua com consumer vivo (pode existir consumer iniciado fora do registry HTTP)

## Validação prática no PC TESTE em 25 de março de 2026
- `GET /healthz` retornou `{"status":"ok"}`.
- `GET /health` retornou `status=ok`, `environment=production` e `build_ref=local-dev`.
- `GET /api/v1/system/status` retornou `status=OPERATIONAL`.
- `GET /api/v1/workers/status` mostrou 21 workers rastreados, quase todos `running`, com `google_productivity` em `disabled` por flag.
- `GET /api/v1/system/health/services` mostrou:
  - `agent=healthy`
  - `knowledge=degraded`
  - `memory=ok`
  - `llm=healthy`
- `GET /api/v1/observability/health/system` retornou `status=healthy` com `score=91`, mas o componente crítico `episodic_memory_qdrant` estava `degraded`.
- Portanto, em 25 de março de 2026 a stack estava acessível e servindo HTTP, mas não atendia ao critério de stack funcional completa por causa da degradação do Qdrant e do domínio de knowledge.

## Métricas e superfícies auxiliares
- `/metrics` só existe se `prometheus_fastapi_instrumentator` estiver disponível.
- `DomainSLOMetricsMiddleware` registra métricas Prometheus por domínio HTTP.
- O `HealthMonitor`, o `PoisonPillHandler` e o próprio `ObservabilityService` também publicam famílias próprias no registry Prometheus.
- `/api/v1/observability/slo/domains` não lê essas métricas; ele recalcula o SLO a partir de `AuditEvent`.
- `/api/v1/observability/metrics/summary` não é export Prometheus; ele resume só `llm`, `multi_agent` e `poison_pills`.

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/services/system_status_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/core/monitoring/health_monitor.py`
- `backend/app/core/kernel.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Mapa de Testes]]

## Riscos/Lacunas
- O healthcheck do container `janus-api` usa `/health`, mas o endpoint anônimo resiliente para probe é `/healthz`.
- Se `PUBLIC_API_KEY` for configurada, `/health` e `/api/v1/*` podem exigir `X-API-Key`; como o healthcheck do Compose chama `/health` sem header, o container pode ficar `unhealthy` mesmo com a API funcional para clientes autenticados.
- O score agregado do `HealthMonitor` pode mascarar degradação de componente crítico se o estado ainda for `degraded` e não `unhealthy`.
- O check do `poison_pill_handler` ainda sofre incompatibilidade entre status do handler (`warning`/`critical`) e o enum aceito pelo `HealthMonitor`.
- `GET /api/v1/observability/health/system` pode devolver `unknown` até o primeiro loop do monitor ou `check-all`; isso é estado inicial válido, não necessariamente incidente.
- `/api/v1/system/status` não participa de decisão de saúde real, apesar do nome sugerir isso.
- `/api/v1/system/overview` usa `last_heartbeat` sintético e não deve ser tratado como telemetria autoritativa.
- O endpoint de workers cobre apenas `app.state.orchestrator_workers`, não todos os processos do `Kernel`.
- `/readyz` e `/livez` aparecem como bypass de rate limit, mas não existem como rotas do FastAPI hoje.
