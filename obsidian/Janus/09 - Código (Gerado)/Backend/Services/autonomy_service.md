---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/autonomy_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_service

## Arquivos-fonte
- `backend/app/services/autonomy_service.py`

## Dependências de código
- Repositórios
  - `autonomy_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `AutonomyServiceError`
  - Erro base para o serviço de autonomia.
- class: `AutonomyConfig`
- class: `AutonomyService`
  - Serviço AutonomyLoop básico: Perceber → Planejar → Executar → Refletir → Otimizar.
- method: `AutonomyService.__init__(self, optimization_service: OptimizationService, llm_service: LLMService | None = None, goal_manager: GoalManager | None = None, repo: AutonomyRepository | None = None, collaboration_service: CollaborationService | None = None, lock_service: AutonomyLockService | None = None)`
- method: `AutonomyService._ensure_core_tools_registered(self)` -> `None`
  - Carrega agent_tools uma vez para disparar o registro no action_registry.
- method: `AutonomyService._is_active(self)` -> `bool`
- method: `AutonomyService._refresh_runtime_lock_status(self, *, scope_key: str | None = None, owner_id: str | None = None, expires_at: datetime | None = None, lease_held: bool | None = None)` -> `None`
- method: `AutonomyService.start(self, config: AutonomyConfig)` -> `bool`
- method: `AutonomyService.stop(self)` -> `bool`
- method: `AutonomyService.get_status(self)` -> `dict[str, Any]`
- method: `AutonomyService.update_plan(self, plan: list[dict[str, Any]])` -> `None`
- method: `AutonomyService.update_policy_config(self, risk_profile: str | None = None, auto_confirm: bool | None = None, allowlist: list[str] | None = None, blocklist: list[str] | None = None, max_actions_per_cycle: int | None = None, max_seconds_per_cycle: int | None = None)` -> `None`
- method: `AutonomyService._perceive_metrics(self)` -> `dict[str, Any]`
- method: `AutonomyService._select_goal(self)` -> `Goal | None`
- method: `AutonomyService._build_plan(self, current_goal: Goal | None, metrics: dict[str, Any])` -> `list[dict[str, Any]]`
- method: `AutonomyService._select_step_for_enqueue(self, plan: list[dict[str, Any]])` -> `dict[str, Any] | None`
- method: `AutonomyService._to_original_goal_text(self, goal: Goal, step: dict[str, Any])` -> `str`
- method: `AutonomyService._record_history_step(self, *, cycle: int, tool: str, input_preview: str, result_preview: str, success: bool, error: str | None, duration_seconds: float)` -> `None`
- method: `AutonomyService._enqueue_taskstate(self, *, goal: Goal, metrics: dict[str, Any], plan: list[dict[str, Any]], step: dict[str, Any], enqueue_ledger_id: int | None = None, idempotency_key: str | None = None)` -> `str`
- method: `AutonomyService._run_loop(self)`
- method: `AutonomyService._run_cycle(self)`
- method: `AutonomyService._run_cycle_enqueue(self)`
- function: `get_autonomy_service(request: Request)` -> `'AutonomyService'`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
