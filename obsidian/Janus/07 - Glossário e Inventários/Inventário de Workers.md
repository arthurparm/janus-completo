---
tipo: inventario
dominio: backend
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Workers

## Objetivo
Listar os workers nomeados do sistema.

## Responsabilidades
- Facilitar entendimento do plano assincrono.

## Entradas
- `backend/app/core/workers/*.py`

## Saidas
- Indice de workers.

## Dependencias
- [[02 - Backend/Autonomia e Workers]]

## Workers por modulo
- `agent_tasks_worker`
- `async_consolidation_worker`
- `auto_scaler`
- `code_agent_worker`
- `codex_worker`
- `data_harvester`
- `debate_critic_worker`
- `debate_proponent_worker`
- `distillation_worker`
- `document_ingestion_worker`
- `google_productivity_worker`
- `knowledge_consolidator_worker`
- `life_cycle_worker`
- `memory_maintenance_worker`
- `meta_agent_worker`
- `neural_training_system`
- `neural_training_worker`
- `orchestrator`
- `professor_agent_worker`
- `red_team_agent_worker`
- `reflexion_worker`
- `router_worker`
- `sandbox_agent_worker`
- `thinker_agent_worker`

## Tarefas que o orquestrador sobe
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
- `google_productivity` quando `ENABLE_GOOGLE_PRODUCTIVITY_WORKER=true`
- `debate_proponent`
- `debate_critic`
- `codex_worker`

## Leitura operacional
- Os nomes de runtime nao batem 1:1 com os nomes de arquivo.
- `AutonomyLoop` nao faz parte desta lista: ele e uma task interna de `AutonomyService`, nao um worker do orquestrador.
- `google_productivity` pode aparecer como handle desativado quando a flag estiver desligada.
- Use esta nota junto com [[02 - Backend/Autonomia e Workers]] e `/api/v1/workers/status`.

## Arquivos-fonte
- `backend/app/core/workers/orchestrator.py`
- `backend/app/core/workers/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- Nem todos os workers necessariamente rodam sempre; parte depende de flags e boot path.
