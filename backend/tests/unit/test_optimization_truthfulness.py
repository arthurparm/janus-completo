import asyncio
import importlib
import re
import sys
import threading
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

optimization_endpoint = importlib.import_module("app.api.v1.endpoints.optimization")
optimization_repository = importlib.import_module("app.repositories.optimization_repository")
optimization_service = importlib.import_module("app.services.optimization_service")
self_optimization = importlib.import_module(
    "app.core.optimization.self_optimization"
)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_service_rejects_unverifiable_auto_execution() -> None:
    repository = type("Repository", (), {"run_cycle": AsyncMock()})()
    service = optimization_service.OptimizationService(repository)

    with pytest.raises(
        optimization_service.OptimizationExecutionUnavailableError,
        match="nenhuma melhoria foi aplicada",
    ):
        await service.run_optimization_cycle(True, 1)

    repository.run_cycle.assert_not_awaited()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_endpoint_exposes_auto_execution_as_not_implemented() -> None:
    service = type(
        "Service",
        (),
        {
            "run_optimization_cycle": AsyncMock(
                side_effect=optimization_service.OptimizationExecutionUnavailableError(
                    "execução indisponível"
                )
            )
        },
    )()

    with pytest.raises(HTTPException) as exc_info:
        await optimization_endpoint.run_optimization_cycle(
            optimization_endpoint.OptimizationCycleRequest(enable_auto_execution=True),
            service,
        )

    assert exc_info.value.status_code == 501
    assert exc_info.value.detail == "execução indisponível"


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_planning_cycle_remains_available() -> None:
    repository = type(
        "Repository",
        (),
        {"run_cycle": AsyncMock(return_value={"success": True, "issues_detected": 0})},
    )()
    service = optimization_service.OptimizationService(repository)

    result = await service.run_optimization_cycle(False, 2)

    assert result == {"success": True, "issues_detected": 0}
    repository.run_cycle.assert_awaited_once_with(
        enable_auto_execution=False,
        max_improvements=2,
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_core_cycle_rejects_auto_execution_before_collecting_metrics() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    cycle.monitor.collect_metrics = AsyncMock()

    with pytest.raises(NotImplementedError, match="adaptador auditável"):
        await cycle.run_cycle(enable_auto_execution=True)

    cycle.monitor.collect_metrics.assert_not_awaited()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_core_planning_cycle_never_claims_or_runs_application() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    metrics = self_optimization.SystemMetrics(
        avg_response_time=3.0,
        error_rate=0.2,
        tool_success_rate=0.8,
        memory_usage_mb=128.0,
        active_tools_count=1,
    )
    issue = self_optimization.DetectedIssue(
        issue_type=self_optimization.IssueType.SLOW_RESPONSE,
        severity=0.8,
        description="lento",
        affected_component="tool",
        evidence={},
    )
    improvement = self_optimization.PlannedImprovement(
        improvement_type=self_optimization.ImprovementType.INVESTIGATE,
        target_component="tool",
        description="planejar cache",
        hypothesis="cache pode ajudar, ainda sem confirmação",
        evidence={"avg_response_time": 3.0},
        success_criteria=["comparar baseline e amostra posterior"],
        implementation_steps=["medir"],
        risk_level=0.4,
    )
    cycle.monitor.collect_metrics = AsyncMock(return_value=metrics)
    cycle.monitor.detect_issues = Mock(return_value=[issue])
    cycle.monitor._calculate_health_score = Mock(return_value=0.5)
    cycle.planner.plan_improvements = AsyncMock(return_value=[improvement])
    cycle.executor.execute_improvement = AsyncMock()

    result = await cycle.run_cycle(enable_auto_execution=False)

    assert result["success"] is True
    assert result["improvements_planned"] == 1
    assert result["improvements_applied"] == 0
    assert result["plans"] == [improvement.to_dict()]
    assert result["plans"][0]["requires_human_approval"] is True
    assert "70%" not in str(result["plans"])
    cycle.executor.execute_improvement.assert_not_awaited()

    response = optimization_endpoint.OptimizationCycleResponse(**result)
    assert response.plans[0].hypothesis == "cache pode ajudar, ainda sem confirmação"


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_planner_covers_every_detected_issue_without_invented_percentages() -> None:
    metrics = self_optimization.SystemMetrics(
        avg_response_time=3.0,
        error_rate=0.25,
        tool_success_rate=0.75,
        memory_usage_mb=512.0,
        active_tools_count=2,
    )
    issues = [
        self_optimization.DetectedIssue(
            issue_type=issue_type,
            severity=0.8,
            description=issue_type.value,
            affected_component="component",
            evidence={"observed": True},
        )
        for issue_type in self_optimization.IssueType
    ]

    plans = await self_optimization.ImprovementPlanner().plan_improvements(
        issues, metrics
    )

    assert len(plans) == len(issues)
    assert all(plan.evidence["observed"] is True for plan in plans)
    assert all(plan.success_criteria for plan in plans)
    assert all(plan.requires_human_approval is True for plan in plans)
    assert not any("%" in plan.hypothesis for plan in plans)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_cycle_without_issues_reports_sample_not_global_health() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    metrics = self_optimization.SystemMetrics(
        avg_response_time=0.2,
        error_rate=0.0,
        tool_success_rate=1.0,
        memory_usage_mb=128.0,
        active_tools_count=1,
    )
    cycle.monitor.collect_metrics = AsyncMock(return_value=metrics)
    cycle.monitor.detect_issues = Mock(return_value=[])
    cycle.monitor._calculate_health_score = Mock(return_value=1.0)

    result = await cycle.run_cycle(enable_auto_execution=False)

    assert result["plans"] == []
    assert result["improvements_planned"] == 0
    assert result["message"] == "Nenhum problema detectado na amostra atual."
    assert "saudável" not in result["message"].lower()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_planning_endpoint_returns_observable_plan_contract() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    service = type(
        "Service",
        (),
        {
            "run_optimization_cycle": AsyncMock(
                return_value={
                    "success": True,
                    "issues_detected": 1,
                    "improvements_planned": 1,
                    "improvements_applied": 0,
                    "elapsed_seconds": 0.01,
                    "plans": [
                        {
                            "improvement_type": "investigate",
                            "target_component": "tool",
                            "description": "Investigar latência",
                            "hypothesis": "A causa ainda precisa ser confirmada.",
                            "evidence": {"avg_duration": 3.0},
                            "success_criteria": ["Comparar baseline e nova amostra."],
                            "implementation_steps": ["Medir"],
                            "risk_level": 0.4,
                            "priority_score": 0.68,
                            "requires_human_approval": True,
                        }
                    ],
                    "message": "Planos gerados para revisão humana; nenhuma melhoria foi aplicada.",
                }
            )
        },
    )()
    app = FastAPI()
    app.include_router(optimization_endpoint.router, prefix="/optimization")
    app.dependency_overrides[
        optimization_endpoint.get_optimization_service
    ] = lambda: service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/optimization/run-cycle",
            json={"enable_auto_execution": False, "max_improvements": 1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["improvements_applied"] == 0
    assert body["plans"][0]["evidence"] == {"avg_duration": 3.0}
    assert body["plans"][0]["requires_human_approval"] is True


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_issue_listing_collects_current_metrics_before_detection() -> None:
    metrics = self_optimization.SystemMetrics(
        avg_response_time=3.0,
        error_rate=0.25,
        tool_success_rate=0.75,
        memory_usage_mb=128.0,
        active_tools_count=1,
    )
    issue = self_optimization.DetectedIssue(
        issue_type=self_optimization.IssueType.HIGH_ERROR_RATE,
        severity=0.8,
        description="taxa alta",
        affected_component="system",
        evidence={"error_rate": 0.25},
    )
    repository = type(
        "Repository",
        (),
        {
            "get_metrics": AsyncMock(return_value=metrics),
            "find_issues": Mock(return_value=[issue]),
        },
    )()
    service = optimization_service.OptimizationService(repository)

    result = await service.get_detected_issues(
        self_optimization.IssueSeverity.HIGH,
        self_optimization.IssueType.HIGH_ERROR_RATE,
    )

    assert result == [issue]
    repository.get_metrics.assert_awaited_once()
    repository.find_issues.assert_called_once()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_issue_listing_does_not_turn_missing_metrics_into_empty_list() -> None:
    repository = type(
        "Repository",
        (),
        {
            "get_metrics": AsyncMock(
                side_effect=optimization_repository.OptimizationMetricsUnavailableRepositoryError(
                    "sem amostras"
                )
            ),
            "find_issues": Mock(),
        },
    )()
    service = optimization_service.OptimizationService(repository)

    with pytest.raises(
        optimization_service.OptimizationMetricsUnavailableError,
        match="sem amostras",
    ):
        await service.get_detected_issues(None, None)

    repository.find_issues.assert_not_called()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_issue_endpoint_awaits_fresh_detection() -> None:
    issue = self_optimization.DetectedIssue(
        issue_type=self_optimization.IssueType.SLOW_RESPONSE,
        severity=0.5,
        description="lento",
        affected_component="tool",
        evidence={"avg_duration": 3.0},
    )
    service = type(
        "Service",
        (),
        {"get_detected_issues": AsyncMock(return_value=[issue])},
    )()

    response = await optimization_endpoint.get_detected_issues(
        service=service,
        severity=self_optimization.IssueSeverity.MEDIUM,
        category=self_optimization.IssueType.SLOW_RESPONSE,
    )

    assert response[0].issue_type == "slow_response"
    service.get_detected_issues.assert_awaited_once_with(
        self_optimization.IssueSeverity.MEDIUM,
        self_optimization.IssueType.SLOW_RESPONSE,
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_issue_filters_and_history_limit_reject_invalid_http_queries() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

    metric = self_optimization.SystemMetrics(
        avg_response_time=0.5,
        error_rate=0.0,
        tool_success_rate=1.0,
        memory_usage_mb=None,
        active_tools_count=2,
    )
    control_status = {
        "status": "running",
        "module": "self_optimization",
        "continuous_running": True,
        "continuous_task_active": True,
        "continuous_control_available": True,
        "automatic_execution_available": False,
        "interval_seconds": 30.0,
        "last_started_by": "optimizer-control",
        "last_started_at": 1.0,
        "last_stopped_at": None,
        "last_error": None,
        "last_cycle_at": 2.0,
        "last_issues_detected": 1,
        "last_improvements_planned": 1,
        "audit_recorded": True,
    }
    status_payload = {
        key: value for key, value in control_status.items() if key != "audit_recorded"
    }
    service = type(
        "Service",
        (),
        {
            "get_detected_issues": AsyncMock(return_value=[]),
            "get_metrics_history": AsyncMock(return_value=[metric]),
            "analyze_system": AsyncMock(return_value={}),
            "start_continuous": AsyncMock(return_value=control_status),
            "stop_continuous": AsyncMock(
                return_value={
                    **control_status,
                    "status": "idle",
                    "continuous_running": False,
                    "continuous_task_active": False,
                    "stopped": True,
                    "forced": False,
                }
            ),
            "get_status": Mock(return_value=status_payload),
        },
    )()
    actor = ActorContext.authenticated(
        actor_id="optimizer-control",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-optimization",
        scopes=("ops:execute",),
    )
    app = FastAPI()
    app.include_router(optimization_endpoint.router, prefix="/optimization")
    app.dependency_overrides[optimization_endpoint.get_optimization_service] = (
        lambda: service
    )
    app.dependency_overrides[
        optimization_endpoint.require_service_actor_context
    ] = lambda: actor

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        invalid_severity = await client.get(
            "/optimization/issues", params={"severity": "UNKNOWN"}
        )
        fuzzy_category = await client.get(
            "/optimization/issues", params={"category": "error"}
        )
        invalid_limit = await client.get(
            "/optimization/metrics/history", params={"limit": -1}
        )
        valid_history = await client.get(
            "/optimization/metrics/history", params={"limit": 1}
        )
        artificial_analysis = await client.post(
            "/optimization/analyze", params={"analysis_type": "security"}
        )
        control_started = await client.post(
            "/optimization/continuous/start", json={"interval_seconds": 30}
        )
        control_stopped = await client.post("/optimization/continuous/stop")
        current_status = await client.get("/optimization/status")

    assert invalid_severity.status_code == 422
    assert fuzzy_category.status_code == 422
    assert invalid_limit.status_code == 422
    assert valid_history.status_code == 200
    assert artificial_analysis.status_code == 422
    assert control_started.status_code == 200
    assert control_started.json()["automatic_execution_available"] is False
    assert control_stopped.status_code == 200
    assert control_stopped.json()["stopped"] is True
    assert current_status.status_code == 200
    assert current_status.json()["last_improvements_planned"] == 1
    assert valid_history.json() == {
        "count": 1,
        "metrics": [
            {
                "avg_response_time": 0.5,
                "error_rate": 0.0,
                "tool_success_rate": 1.0,
                "memory_usage_mb": None,
                "active_tools_count": 2,
                "failed_tools": [],
                "slow_tools": [],
                "timestamp": metric.timestamp,
            }
        ],
    }
    service.get_detected_issues.assert_not_awaited()
    service.get_metrics_history.assert_awaited_once_with(1)
    service.analyze_system.assert_not_awaited()
    service.start_continuous.assert_awaited_once_with(
        interval_seconds=30.0,
        actor=actor,
    )
    service.stop_continuous.assert_awaited_once_with(actor=actor)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_metrics_history_service_enforces_bounds_and_returns_latest() -> None:
    history = [
        self_optimization.SystemMetrics(
            avg_response_time=float(index),
            error_rate=0.0,
            tool_success_rate=1.0,
            memory_usage_mb=None,
            active_tools_count=1,
        )
        for index in range(3)
    ]
    repository = type(
        "Repository", (), {"get_metrics_history": Mock(return_value=history)}
    )()
    service = optimization_service.OptimizationService(repository)

    assert await service.get_metrics_history(2) == history[-2:]
    for invalid_limit in (0, 101, -1):
        with pytest.raises(ValueError, match="entre 1 e 100"):
            await service.get_metrics_history(invalid_limit)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_cycle_recovers_after_missing_metrics() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    calls = 0

    async def run_cycle() -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise self_optimization.OptimizationMetricsUnavailableError(
                "sem amostras"
            )
        cycle.stop()
        return {"success": True}

    cycle.run_cycle = run_cycle

    await cycle.run_continuous(interval_seconds=0.001)

    assert calls == 2
    assert cycle._running is False
    assert cycle._stop_event is None


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_cycle_recovers_after_transient_failure() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    calls = 0

    async def run_cycle() -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("falha transitória")
        cycle.stop()
        return {"success": True}

    cycle.run_cycle = run_cycle

    await cycle.run_continuous(interval_seconds=0.001)

    assert calls == 2
    assert cycle._running is False


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_cycle_delivers_result_before_waiting_again() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    result = {
        "issues_detected": 1,
        "improvements_planned": 1,
        "plans": [{"description": "persistir"}],
    }
    delivered: list[dict[str, object]] = []

    async def run_cycle() -> dict[str, object]:
        return result

    async def on_cycle_completed(cycle_result: dict[str, object]) -> None:
        delivered.append(cycle_result)
        cycle.stop()

    cycle.run_cycle = run_cycle

    await cycle.run_continuous(
        interval_seconds=60,
        on_cycle_completed=on_cycle_completed,
    )

    assert delivered == [result]
    assert cycle._running is False


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_stop_interrupts_continuous_cycle_wait() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    first_cycle_finished = asyncio.Event()

    async def run_cycle() -> dict[str, object]:
        first_cycle_finished.set()
        return {"success": True}

    cycle.run_cycle = run_cycle
    task = asyncio.create_task(cycle.run_continuous(interval_seconds=60))
    await asyncio.wait_for(first_cycle_finished.wait(), timeout=1)

    cycle.stop()
    await asyncio.wait_for(task, timeout=1)

    assert cycle._running is False
    assert cycle._stop_event is None


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_cancellation_clears_continuous_cycle_status() -> None:
    cycle = self_optimization.SelfOptimizationCycle()
    cycle_started = asyncio.Event()
    release_cycle = asyncio.Event()

    async def run_cycle() -> dict[str, object]:
        cycle_started.set()
        await release_cycle.wait()
        return {"success": True}

    cycle.run_cycle = run_cycle
    task = asyncio.create_task(cycle.run_continuous(interval_seconds=60))
    await asyncio.wait_for(cycle_started.wait(), timeout=1)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert cycle._running is False
    assert cycle._stop_event is None


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_cycle_rejects_invalid_or_duplicate_start() -> None:
    cycle = self_optimization.SelfOptimizationCycle()

    with pytest.raises(ValueError, match="maior que zero"):
        await cycle.run_continuous(interval_seconds=0)

    cycle._running = True
    with pytest.raises(RuntimeError, match="já está em execução"):
        await cycle.run_continuous(interval_seconds=1)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_control_is_authorized_audited_and_interruptible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

    class Repository:
        running = False

        async def run_continuous(
            self,
            interval_seconds: float,
            on_cycle_completed: Callable[[dict[str, object]], Awaitable[None]],
        ) -> None:
            assert interval_seconds == 10
            self.running = True
            try:
                await on_cycle_completed(
                    {
                        "success": True,
                        "issues_detected": 1,
                        "improvements_planned": 1,
                        "improvements_applied": 0,
                        "elapsed_seconds": 0.1,
                        "plans": [{"description": "plano persistido"}],
                        "message": "planejado",
                    }
                )
                await release.wait()
            finally:
                self.running = False

        def stop_continuous(self) -> None:
            release.set()

        def get_status(self) -> dict[str, object]:
            return {
                "status": "running" if self.running else "idle",
                "module": "self_optimization",
                "continuous_running": self.running,
            }

    release = asyncio.Event()
    events: list[dict[str, object]] = []

    def record_event(**event: object) -> bool:
        events.append(event)
        return True

    monkeypatch.setattr(
        optimization_service,
        "record_audit_event_direct",
        record_event,
    )
    actor = ActorContext.authenticated(
        actor_id="optimizer-control",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-optimization",
        scopes=("ops:execute",),
    )
    service = optimization_service.OptimizationService(Repository())
    human = ActorContext.authenticated(
        actor_id="human-user",
        actor_type=ActorType.HUMAN,
        roles=("ADMIN",),
        auth_method=AuthMethod.OIDC,
        trace_id="trace-human",
    )
    service_without_scope = ActorContext.authenticated(
        actor_id="optimizer-limited",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-limited",
    )

    with pytest.raises(HTTPException) as forbidden:
        await service.start_continuous(interval_seconds=10, actor=human)
    assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException) as missing_scope:
        await service.start_continuous(
            interval_seconds=10,
            actor=service_without_scope,
        )
    assert missing_scope.value.status_code == 403

    started = await service.start_continuous(interval_seconds=10, actor=actor)

    assert started["status"] == "running"
    assert started["continuous_task_active"] is True
    assert started["automatic_execution_available"] is False
    with pytest.raises(
        optimization_service.OptimizationContinuousAlreadyRunningError
    ):
        await service.start_continuous(interval_seconds=10, actor=actor)

    stopped = await service.stop_continuous(actor=actor)

    assert stopped["status"] == "idle"
    assert stopped["stopped"] is True
    assert stopped["forced"] is False
    assert stopped["continuous_task_active"] is False
    actions = [str(event["action"]) for event in events]
    assert "continuous_start_requested" in actions
    assert "continuous_started" in actions
    assert "continuous_cycle_completed" in actions
    assert "continuous_stop_requested" in actions
    assert "continuous_stopped" in actions
    persisted_cycle = next(
        event
        for event in events
        if event.get("action") == "continuous_cycle_completed"
    )
    persisted_details = persisted_cycle["details_json"]
    assert isinstance(persisted_details, dict)
    assert persisted_details["actor_id"] == "optimizer-control"
    persisted_result = persisted_details["cycle"]
    assert isinstance(persisted_result, dict)
    assert persisted_result["plans"] == [
        {"description": "plano persistido"}
    ]
    assert stopped["last_issues_detected"] == 1
    assert stopped["last_improvements_planned"] == 1
    assert all(
        event.get("user_id") == "optimizer-control"
        for event in events
        if event.get("action") != "continuous_task_finished"
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_shutdown_stops_owned_task_without_external_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

    release = asyncio.Event()

    class Repository:
        running = False

        async def run_continuous(
            self,
            _interval_seconds: float,
            on_cycle_completed: Callable[[dict[str, object]], Awaitable[None]],
        ) -> None:
            self.running = True
            try:
                await on_cycle_completed(
                    {
                        "success": True,
                        "issues_detected": 0,
                        "improvements_planned": 0,
                        "improvements_applied": 0,
                        "elapsed_seconds": 0.1,
                        "plans": [],
                        "message": "sem problemas",
                    }
                )
                await release.wait()
            finally:
                self.running = False

        def stop_continuous(self) -> None:
            release.set()

        def get_status(self) -> dict[str, object]:
            return {
                "status": "running" if self.running else "idle",
                "module": "self_optimization",
                "continuous_running": self.running,
            }

    events: list[dict[str, object]] = []

    def record_event(**event: object) -> bool:
        events.append(event)
        return True

    monkeypatch.setattr(
        optimization_service,
        "record_audit_event_direct",
        record_event,
    )
    actor = ActorContext.authenticated(
        actor_id="optimizer-control",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-optimization",
        scopes=("ops:execute",),
    )
    service = optimization_service.OptimizationService(Repository())
    await service.start_continuous(interval_seconds=10, actor=actor)

    await service.shutdown()

    assert service.get_status()["status"] == "idle"
    audit_details = [event.get("details_json") for event in events]
    assert any(
        isinstance(details, dict) and details.get("reason") == "kernel_shutdown"
        for details in audit_details
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_start_requires_durable_audit_before_task_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

    repository = type(
        "Repository",
        (),
        {
            "get_status": Mock(
                return_value={
                    "status": "idle",
                    "module": "self_optimization",
                    "continuous_running": False,
                }
            ),
            "run_continuous": AsyncMock(),
        },
    )()

    def reject_audit(**event: object) -> bool:
        if event.get("required") is True:
            raise RuntimeError("ledger indisponível")
        return False

    monkeypatch.setattr(
        optimization_service,
        "record_audit_event_direct",
        reject_audit,
    )
    actor = ActorContext.authenticated(
        actor_id="optimizer-control",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-optimization",
        scopes=("ops:execute",),
    )
    service = optimization_service.OptimizationService(repository)

    with pytest.raises(RuntimeError, match="ledger indisponível"):
        await service.start_continuous(interval_seconds=10, actor=actor)

    repository.run_continuous.assert_not_awaited()
    assert service.get_status()["continuous_task_active"] is False


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_continuous_cycle_stops_when_result_cannot_be_persisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

    cycle_audit_started = threading.Event()
    release_cycle_audit = threading.Event()

    class Repository:
        running = False

        async def run_continuous(
            self,
            _interval_seconds: float,
            on_cycle_completed: Callable[[dict[str, object]], Awaitable[None]],
        ) -> None:
            self.running = True
            try:
                await on_cycle_completed(
                    {
                        "issues_detected": 1,
                        "improvements_planned": 1,
                        "plans": [{"description": "não pode ser perdido"}],
                    }
                )
            finally:
                self.running = False

        def stop_continuous(self) -> None:
            self.running = False

        def get_status(self) -> dict[str, object]:
            return {
                "status": "running" if self.running else "idle",
                "module": "self_optimization",
                "continuous_running": self.running,
            }

    def audit(**event: object) -> bool:
        if event.get("action") == "continuous_cycle_completed":
            cycle_audit_started.set()
            release_cycle_audit.wait(timeout=1)
            raise RuntimeError("ledger indisponível")
        return True

    monkeypatch.setattr(
        optimization_service,
        "record_audit_event_direct",
        audit,
    )
    actor = ActorContext.authenticated(
        actor_id="optimizer-control",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-optimization",
        scopes=("ops:execute",),
    )
    service = optimization_service.OptimizationService(Repository())

    await service.start_continuous(interval_seconds=10, actor=actor)
    task = service._continuous_task
    assert task is not None
    assert cycle_audit_started.wait(timeout=1)
    release_cycle_audit.set()

    with pytest.raises(
        optimization_service.OptimizationServiceError,
        match="Falha ao persistir",
    ):
        await task
    await asyncio.sleep(0)

    status_payload = service.get_status()
    assert status_payload["status"] == "idle"
    assert status_payload["continuous_task_active"] is False
    assert "Falha ao persistir" in str(status_payload["last_error"])
    assert status_payload["last_cycle_at"] is None


def test_repository_status_reports_operational_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = optimization_repository.OptimizationRepository()
    cycle = optimization_repository.self_optimization_cycle

    monkeypatch.setattr(cycle, "_running", False)
    assert repository.get_status() == {
        "status": "idle",
        "module": "self_optimization",
        "continuous_running": False,
    }

    monkeypatch.setattr(cycle, "_running", True)
    assert repository.get_status()["status"] == "running"


def test_optimization_service_persists_prompt_with_repository_contract() -> None:
    from app.core.agents import AgentRole

    prompt_repository = type(
        "PromptRepository",
        (),
        {
            "create_prompt_version": Mock(
                return_value=type("Prompt", (), {"prompt_version": "persistida"})()
            )
        },
    )()
    service = optimization_service.OptimizationService(object())
    service._prompt_repo = prompt_repository

    result = service.update_agent_prompt(
        AgentRole.CODER,
        "prompt real",
        language="pt-BR",
        activate=True,
    )

    call = prompt_repository.create_prompt_version.call_args
    assert call.kwargs["prompt_name"] == "agent_prompt_coder"
    assert call.kwargs["prompt_text"] == "prompt real"
    assert re.fullmatch(r"\d{20}", call.kwargs["version"])
    assert call.kwargs["language"] == "pt-BR"
    assert call.kwargs["activate"] is True
    assert result == {
        "name": "agent_prompt_coder",
        "version": "persistida",
        "activated": True,
    }


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_metrics_failure_does_not_create_perfect_health_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = self_optimization.SystemMonitor()
    monkeypatch.setattr(
        self_optimization.action_registry,
        "get_statistics",
        Mock(side_effect=RuntimeError("telemetria offline")),
    )

    with pytest.raises(RuntimeError, match="Falha ao coletar métricas"):
        await monitor.collect_metrics()

    assert monitor._metrics_history == []


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_service_exposes_metrics_repository_failure() -> None:
    repository = type(
        "Repository",
        (),
        {
            "get_metrics": AsyncMock(
                side_effect=optimization_repository.OptimizationRepositoryError(
                    "telemetria indisponível"
                )
            )
        },
    )()
    service = optimization_service.OptimizationService(repository)

    with pytest.raises(
        optimization_service.OptimizationServiceError,
        match="Falha ao buscar as métricas de saúde",
    ):
        await service.get_system_health()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_missing_memory_probe_is_not_reported_as_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = self_optimization.SystemMonitor()
    monkeypatch.setattr(
        self_optimization.action_registry,
        "get_statistics",
        Mock(
            return_value={
                "tool_usage": {},
                "total_calls": 1,
                "successful_calls": 1,
                "total_tools_registered": 0,
            }
        ),
    )
    monkeypatch.setitem(sys.modules, "psutil", None)

    metrics = await monitor.collect_metrics()

    assert metrics.memory_usage_mb is None
    assert monitor._metrics_history[-1].memory_usage_mb is None


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_analysis_preserves_unknown_memory_measurement() -> None:
    metrics = self_optimization.SystemMetrics(
        avg_response_time=0.2,
        error_rate=0.0,
        tool_success_rate=1.0,
        memory_usage_mb=None,
        active_tools_count=1,
    )
    repository = type(
        "Repository",
        (),
        {
            "get_metrics": AsyncMock(return_value=metrics),
            "get_metrics_history": Mock(return_value=[]),
            "find_issues": Mock(return_value=[]),
            "get_health_score": Mock(return_value=1.0),
        },
    )()
    service = optimization_service.OptimizationService(repository)

    result = await service.analyze_system(
        optimization_service.OptimizationAnalysisType.PERFORMANCE,
        detailed=False,
    )

    assert result["metrics_snapshot"]["memory_usage_mb"] is None
    assert result["trend"]["memory_usage_latest_mb"] is None
    assert result["trend"]["memory_usage_max_mb"] is None
    assert result["series"]["memory_usage_mb"] == []

    with pytest.raises(ValueError, match="deve ser 'performance'"):
        await service.analyze_system("security", detailed=False)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_zero_tool_calls_are_unavailable_instead_of_failed_or_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = self_optimization.SystemMonitor()
    monkeypatch.setattr(
        self_optimization.action_registry,
        "get_statistics",
        Mock(
            return_value={
                "tool_usage": {},
                "total_calls": 0,
                "successful_calls": 0,
                "total_tools_registered": 0,
            }
        ),
    )

    with pytest.raises(
        self_optimization.OptimizationMetricsUnavailableError,
        match="Nenhuma chamada de ferramenta",
    ):
        await monitor.collect_metrics()

    assert monitor._metrics_history == []


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_metrics_unavailable_maps_to_http_503() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.api.exception_handlers import add_exception_handlers

    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/metrics")  # type: ignore[untyped-decorator]
    async def metrics() -> None:
        raise optimization_service.OptimizationMetricsUnavailableError(
            "sem amostras"
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")

    assert response.status_code == 503
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"
