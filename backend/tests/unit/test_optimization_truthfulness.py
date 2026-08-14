import importlib
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
        improvement_type=self_optimization.ImprovementType.ADD_CACHING,
        target_component="tool",
        description="planejar cache",
        expected_impact="reduzir latência",
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
    cycle.executor.execute_improvement.assert_not_awaited()


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
