---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/autonomy_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_repository

## Arquivos-fonte
- `backend/app/repositories/autonomy_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/autonomy_history.py`
- `backend/app/services/autonomy_service.py`

## Símbolos
- class: `AutonomyRepository`
- method: `AutonomyRepository.__init__(self, session: Session | None = None)`
- method: `AutonomyRepository._get_session(self)` -> `Session`
- method: `AutonomyRepository.create_run(self, project_id: str | None, risk_profile: str, auto_confirm: bool, allowlist: list[str], blocklist: list[str], max_actions_per_cycle: int, max_seconds_per_cycle: int, interval_seconds: int)` -> `AutonomyRun`
- method: `AutonomyRepository.increment_cycles(self, run_id: int)` -> `None`
- method: `AutonomyRepository.stop_run(self, run_id: int)` -> `None`
- method: `AutonomyRepository.add_step(self, run_id: int, cycle: int, tool: str, input_preview: str | None, input_length: int, result_preview: str | None, result_length: int, success: bool, error: str | None, duration_seconds: float)` -> `AutonomyStep`
- method: `AutonomyRepository.get_active_run(self, project_id: str | None = None)` -> `AutonomyRun | None`
  - Recupera a run ativa mais recente (status='running') para permitir restauração após reinício.
- method: `AutonomyRepository.list_runs(self, project_id: str | None, limit: int = 50)` -> `list[AutonomyRun]`
- method: `AutonomyRepository.get_run(self, run_id: int)` -> `AutonomyRun | None`
- method: `AutonomyRepository.list_steps(self, run_id: int, cycle: int | None = None, limit: int = 100)` -> `list[AutonomyStep]`
- method: `AutonomyRepository.create_or_get_enqueue_ledger(self, *, run_id: int | None, goal_id: str, cycle: int, selected_tool: str | None, idempotency_key: str)` -> `AutonomyEnqueueLedger`
- method: `AutonomyRepository.mark_enqueue_published(self, ledger_id: int, task_id: str)` -> `AutonomyEnqueueLedger | None`
- method: `AutonomyRepository.mark_enqueue_failed(self, ledger_id: int, error: str)` -> `AutonomyEnqueueLedger | None`
- method: `AutonomyRepository.find_latest_enqueue_by_goal(self, goal_id: str)` -> `AutonomyEnqueueLedger | None`
- method: `AutonomyRepository.list_enqueues(self, run_id: int, limit: int = 100)` -> `list[AutonomyEnqueueLedger]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
