---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/life_cycle_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# life_cycle_worker

## Arquivos-fonte
- `backend/app/core/workers/life_cycle_worker.py`

## Símbolos
- class: `LifeCycleWorker`
  - O 'Coração' do Janus (Life Loop).
Executa periodicamente para garantir que o sistema tenha 'iniciativa'.
- method: `LifeCycleWorker.__init__(self, goal_manager: GoalManager, memory_service: MemoryService, interval_seconds: int = 30)`
- method: `LifeCycleWorker.start(self)`
- method: `LifeCycleWorker.stop(self)`
- method: `LifeCycleWorker._loop(self)`
- method: `LifeCycleWorker._pulse(self)`
  - Um único 'batimento' do ciclo de vida.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
