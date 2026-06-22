---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/autonomy_admin_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_admin_repository

## Arquivos-fonte
- `backend/app/repositories/autonomy_admin_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/services/autonomy_admin_service.py`

## Símbolos
- class: `AutonomyAdminRepository`
- method: `AutonomyAdminRepository.__init__(self, session: Session | None = None)`
- method: `AutonomyAdminRepository._get_session(self)` -> `Session`
- method: `AutonomyAdminRepository._to_float(value: Decimal | float | int | None)` -> `float | None`
- method: `AutonomyAdminRepository.get_or_create_sprint_type(self, *, name: str, generated_by: str = 'janus')` -> `AutonomySprintType`
- method: `AutonomyAdminRepository.get_or_create_active_sprint(self, *, sprint_type_id: str, sprint_name: str, start_ts: float | None = None, end_ts: float | None = None)` -> `AutonomySprint`
- method: `AutonomyAdminRepository.create_task(self, *, title: str, description: str, sprint_id: str | None, priority: int, source: str, source_kind: str, source_fingerprint: str, source_ref: str | None = None, area: str | None = None, severity: str | None = None, auto_created: bool = False, llm_provider: str | None = None, llm_model: str | None = None, fallback_used: bool = False)` -> `AutonomyGoal`
- method: `AutonomyAdminRepository.add_task_evidence(self, *, goal_id: str, evidence_type: str, source_uri: str | None, payload: dict[str, Any] | None, score: float | None = None)` -> `AutonomyTaskEvidence`
- method: `AutonomyAdminRepository.find_open_task_by_fingerprint(self, source_fingerprint: str)` -> `AutonomyGoal | None`
- method: `AutonomyAdminRepository.count_auto_created_today(self)` -> `int`
- method: `AutonomyAdminRepository.list_board(self, *, status: str | None = None, limit: int = 200)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminRepository.list_open_tasks(self, *, source_kind: str | None = None)` -> `list[AutonomyGoal]`
- method: `AutonomyAdminRepository.close_task(self, goal_id: str, reason: str, actor: str = 'autonomy_admin')` -> `AutonomyGoal | None`
- method: `AutonomyAdminRepository.create_self_study_run(self, *, trigger_type: str, mode: str, reason: str | None, base_commit: str | None, target_commit: str | None)` -> `AutonomySelfStudyRun`
- method: `AutonomyAdminRepository.add_self_study_file(self, *, run_id: int, file_path: str, change_type: str | None, sha_before: str | None, sha_after: str | None, summary_status: str = 'pending', error: str | None = None)` -> `AutonomySelfStudyFile`
- method: `AutonomyAdminRepository.update_self_study_file_status(self, file_id: int, status: str, error: str | None = None)` -> `None`
- method: `AutonomyAdminRepository.update_self_study_run_progress(self, run_id: int, *, files_total: int | None = None, files_processed: int | None = None)` -> `None`
- method: `AutonomyAdminRepository.finish_self_study_run(self, run_id: int, *, files_total: int, files_processed: int, status: str, error: str | None = None)` -> `None`
- method: `AutonomyAdminRepository.get_self_study_state(self)` -> `AutonomySelfStudyState`
- method: `AutonomyAdminRepository.update_self_study_state(self, *, last_studied_commit: str | None, mark_success: bool = True)` -> `AutonomySelfStudyState`
- method: `AutonomyAdminRepository.get_latest_running_self_study(self)` -> `AutonomySelfStudyRun | None`
- method: `AutonomyAdminRepository.get_self_study_run_progress(self, run_id: int)` -> `dict[str, Any] | None`
- method: `AutonomyAdminRepository.list_self_study_runs(self, limit: int = 20)` -> `list[AutonomySelfStudyRun]`
- method: `AutonomyAdminRepository.list_self_study_files(self, run_id: int, limit: int = 500)` -> `list[AutonomySelfStudyFile]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
