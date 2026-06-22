---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/autonomy_goal_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_goal_repository

## Arquivos-fonte
- `backend/app/repositories/autonomy_goal_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/autonomy/goal_manager.py`
- `backend/app/services/collaboration_service.py`

## Símbolos
- class: `AutonomyGoalRepository`
- method: `AutonomyGoalRepository.__init__(self, session: Session | None = None)`
- method: `AutonomyGoalRepository._get_session(self)` -> `Session`
- method: `AutonomyGoalRepository.create_goal(self, *, goal_id: str, title: str, description: str, priority: int = 5, success_criteria: str | None = None, deadline_ts: float | None = None, source: str = 'api')` -> `AutonomyGoal`
- method: `AutonomyGoalRepository.list_goals(self, *, status: str | None = None, include_terminal: bool = False, limit: int | None = None)` -> `list[AutonomyGoal]`
- method: `AutonomyGoalRepository.get_goal(self, goal_id: str)` -> `AutonomyGoal | None`
- method: `AutonomyGoalRepository.get_next_pending_goal(self)` -> `AutonomyGoal | None`
- method: `AutonomyGoalRepository.transition_status(self, goal_id: str, to_status: str, *, reason: str | None = None, task_id: str | None = None, actor: str = 'system')` -> `AutonomyGoal | None`
- method: `AutonomyGoalRepository.delete_goal(self, goal_id: str)` -> `bool`
- method: `AutonomyGoalRepository.list_transitions(self, goal_id: str, limit: int = 100)` -> `list[AutonomyGoalTransition]`
- method: `AutonomyGoalRepository.decimal_to_float(value: Decimal | float | int | None)` -> `float | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
