---
tipo: inventario
dominio: backend
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Workers

## Objetivo
Listar as tarefas assíncronas nomeadas e explicar o que a API de status realmente enxerga.

## Responsabilidades
- Facilitar leitura do plano assíncrono.
- Diferenciar workers orquestrados, processos de fundo do `Kernel` e handles desativados.

## Entradas
- `backend/app/core/workers/orchestrator.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/core/kernel.py`

## Saídas
- Índice de nomes expostos ao operador.
- Limites da leitura operacional de workers.

## Dependências
- [[02 - Backend/Autonomia e Workers]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Workers orquestrados expostos pela API
- `memory_maintenance`
- `knowledge_consolidation`
- `document_ingestion`
- `agent_tasks`
- `neural_training`
- `reflexion`
- `meta_agent`
- `failure_consumer`
- `auto_scaler`
- `auto_healer`
- `router`
- `code_agent`
- `red_team_agent`
- `professor_agent`
- `sandbox_agent`
- `thinker_agent`
- `distillation`
- `google_productivity`
- `debate_proponent`
- `debate_critic`
- `codex_worker`

## Como `/api/v1/workers/status` calcula estado
- Para `asyncio.Task`, a API devolve:
  - `running` quando a task não terminou nem foi cancelada.
  - `done` e `cancelled` conforme a task.
  - `exception` com a string da exceção, se houver.
  - `state` como `running`, `error`, `stopped` ou `unknown`.
- Para listas ou tuplas de tasks:
  - a API devolve `composite=true` e agrega os filhos;
  - `running` vira verdadeiro se qualquer filho estiver rodando;
  - `state` vira `error` se houver exceção em algum filho.
- Para `DisabledWorkerHandle`:
  - a API devolve `state=disabled`, `reason` e `detail`.
  - hoje isso é usado para `google_productivity` quando a flag `ENABLE_GOOGLE_PRODUCTIVITY_WORKER` está desligada.

## O que `/api/v1/system/overview` mostra sobre workers
- Converte o payload detalhado em um status simplificado: `disabled`, `running`, `error`, `unknown` ou `stopped`.
- Preenche `last_heartbeat` com `datetime.now(UTC)` no momento da resposta.
- Lê `tasks_processed` do registry; como esse campo não é mantido pelo orquestrador, o valor tende a `0`.
- Portanto, `system/overview` é uma visão de painel e não um contador confiável de throughput.

## Processos de fundo que ficam fora dessa visão
- `Kernel._start_background_processes()` também inicia:
  - `knowledge_consolidator`
  - `data_harvester`
  - `life_cycle_worker`
  - `outbox_service`
  - `scheduler`
- Esses itens entram em `app.state.workers`, não em `app.state.orchestrator_workers`.
- Por isso, `/api/v1/workers/status` não cobre toda a atividade assíncrona do sistema.

## Leitura operacional
- O nome exposto ao operador vem de `WORKER_NAMES`, não necessariamente do nome do arquivo Python.
- O endpoint de workers mostra apenas o que foi registrado pelo orquestrador.
- Para contexto amplo, combine esta nota com `GET /api/v1/workers/status`, `GET /api/v1/system/overview` e [[04 - Fluxos End-to-End/Observabilidade]].

## Arquivos-fonte
- `backend/app/core/workers/orchestrator.py`
- `backend/app/api/v1/endpoints/workers.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/core/kernel.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- Nem todos os workers rodam sempre; `google_productivity` pode virar `disabled`.
- A superfície de status não cobre todos os processos iniciados pelo `Kernel`.
- `last_heartbeat` em `system/overview` não é heartbeat real.
- `tasks_processed` não representa contagem operacional confiável no estado atual do código.
