from typing import Any

import pytest

from app.api.v1.endpoints import auto_analysis
from app.core.llm import pricing
from app.services.observability_service import ObservabilityService, ObservabilityServiceError


class _Observability:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report

    async def get_domain_slo_report(self) -> dict[str, Any]:
        return self.report


class _Feedback:
    def __init__(self, stats: dict[str, Any]) -> None:
        self.stats = stats

    def get_stats(self) -> dict[str, Any]:
        return self.stats


@pytest.mark.asyncio
async def test_cost_analysis_uses_budget_ratio_instead_of_absolute_fake_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def snapshot() -> dict[str, Any]:
        return {
            "source": "redis",
            "providers": {},
            "total_spend_usd": 95.0,
            "total_budget_usd": 100.0,
            "budget_usage_pct": 95.0,
        }

    monkeypatch.setattr(auto_analysis, "get_provider_spend_snapshot", snapshot)

    insight = await auto_analysis._analyze_api_costs()

    assert insight.severity == "medium"
    assert insight.status == "warning"
    assert insight.evidence["source"] == "redis"
    assert "95.00%" in insight.estimated_impact


@pytest.mark.asyncio
async def test_performance_does_not_claim_latency_when_sample_is_insufficient() -> None:
    insight = await auto_analysis._analyze_performance(
        _Observability({"status": "insufficient_data", "domains": []})  # type: ignore[arg-type]
    )

    assert insight.severity == "unknown"
    assert insight.status == "insufficient_data"
    assert "Nenhuma conclusão" in insight.estimated_impact


def test_quality_does_not_infer_satisfaction_without_feedback() -> None:
    insight = auto_analysis._analyze_response_quality(
        _Feedback({"total_feedbacks": 0, "satisfaction_rate": None})  # type: ignore[arg-type]
    )

    assert insight.severity == "unknown"
    assert insight.status == "insufficient_data"
    assert "Nenhuma afirmação" in insight.estimated_impact


@pytest.mark.asyncio
async def test_response_contains_source_evidence_and_no_generated_fun_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def snapshot() -> dict[str, Any]:
        return {
            "source": "process_memory",
            "providers": {},
            "total_spend_usd": 0.0,
            "total_budget_usd": 0.0,
            "budget_usage_pct": None,
        }

    monkeypatch.setattr(auto_analysis, "get_provider_spend_snapshot", snapshot)
    response = await auto_analysis.auto_analyze(
        observability=_Observability(  # type: ignore[arg-type]
            {"status": "insufficient_data", "domains": [], "active_alerts": []}
        ),
        feedback=_Feedback(  # type: ignore[arg-type]
            {"total_feedbacks": 0, "satisfaction_rate": None, "status": "no_data"}
        ),
    )

    assert response.overall_health == "unknown"
    assert response.model_dump()["fun_fact"] is None
    assert response.summary.startswith("Diagnóstico baseado em 0 de 3 fontes")
    assert {item.source for item in response.insights} == {
        "llm_cost_tracker",
        "observability_slo",
        "feedback",
    }


@pytest.mark.asyncio
async def test_spend_snapshot_reports_mixed_fallback_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Tracker:
        async def get_provider_spend(self, provider: str) -> float:
            if provider == "openai":
                return 4.0
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr(pricing, "get_redis_usage_tracker", lambda: _Tracker())
    monkeypatch.setattr(pricing, "_provider_budgets_usd", {"openai": 10.0, "ollama": 0.0})
    monkeypatch.setattr(pricing, "_provider_spend_usd", {"openai": 1.0, "ollama": 2.0})

    snapshot = await pricing.get_provider_spend_snapshot()

    assert snapshot["source"] == "mixed_fallback"
    assert snapshot["providers"]["openai"]["spend_usd"] == 4.0
    assert snapshot["providers"]["ollama"]["spend_usd"] == 2.0
    assert snapshot["budget_usage_pct"] == 60.0


@pytest.mark.asyncio
async def test_domain_slo_report_calls_real_repository_contract_with_global_scope() -> None:
    class _Repo:
        kwargs: dict[str, Any] = {}

        def get_audit_events(self, **kwargs: Any) -> list[dict[str, Any]]:
            self.kwargs = kwargs
            return []

    repo = _Repo()
    await ObservabilityService(repo=repo).get_domain_slo_report(min_events=1)

    assert repo.kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_user_observability_requires_and_delegates_authenticated_owner() -> None:
    class _Repo:
        async def get_user_metrics(self, user_id: str) -> dict[str, Any]:
            return {"owner": user_id}

        def get_user_activity(self, user_id: str) -> dict[str, Any]:
            return {"owner": user_id}

    service = ObservabilityService(repo=_Repo())  # type: ignore[arg-type]

    assert await service.get_user_metrics("42") == {"owner": "42"}
    assert service.get_user_activity("42") == {"owner": "42"}
    with pytest.raises(ObservabilityServiceError, match="Authenticated user"):
        await service.get_user_metrics(None)
    with pytest.raises(ObservabilityServiceError, match="Authenticated user"):
        service.get_user_activity(None)
