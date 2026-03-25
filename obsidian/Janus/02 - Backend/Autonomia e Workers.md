---
tipo: dominio
dominio: backend
camada: execucao
fonte-de-verdade: codigo
status: ativo
---

# Autonomia e Workers

## Objetivo
Explicar o plano de execução contínua do Janus.

## Responsabilidades
- Cobrir AutonomyLoop, metas, políticas e workers.
- Diferenciar request síncrona de execução assíncrona.

## Entradas
- Configuração de autonomia.
- Planos de ação.
- Filas e jobs agendados.

## Saídas
- Execução contínua e governada de ações.
- Atualização de metas e aprendizagem operacional.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[02 - Backend/Segurança e Infra]]
- [[04 - Fluxos End-to-End/Autonomia]]

## Leitura operacional
- `/autonomy/start` valida plano, allowlist e blocklist antes de ligar o loop.
- `GoalManager` sustenta CRUD de metas.
- O sistema possui workers explícitos para roteamento, consolidação, reflexão, code, sandbox e treinamento.
- Scheduler inicializa jobs default no boot.

## Workers relevantes
- `router_worker`
- `agent_tasks_worker`
- `knowledge_consolidator_worker`
- `document_ingestion_worker`
- `reflexion_worker`
- `codex_worker`
- `sandbox_agent_worker`
- `life_cycle_worker`
- `neural_training_worker`

## Workers rastreados em runtime
- Na validação do PC TESTE, `/api/v1/workers/status` reportou 21 tarefas rastreadas.
- Além dos módulos de worker por arquivo, o runtime expõe tarefas compostas ou operacionais como `memory_maintenance`, `failure_consumer` e `auto_healer`.
- O inventário de código e o inventário de runtime devem ser lidos juntos.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/core/autonomy/goal_manager.py`
- `backend/app/core/workers/orchestrator.py`
- `backend/app/core/workers/*.py`

## Fluxos relacionados
- [[07 - Glossário e Inventários/Inventário de Workers]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- A execução autônoma depende de políticas corretas e lock runtime para evitar concorrência indesejada.
- Nem todo worker tem visibilidade equivalente no frontend.
