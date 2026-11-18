import pytest
from app.config import settings
from app.core.llm import ModelPriority, ModelRole
from app.repositories.llm_repository import LLMRepository, LLMRepositoryError


class _FakeClient:
    def __init__(self, provider: str, *, should_fail: bool):
        self.provider = provider
        self.model = f"{provider}-model"
        self._should_fail = should_fail

    async def send_enriched(self, *_args, **_kwargs):
        if self._should_fail:
            raise RuntimeError(f"{self.provider} unavailable")
        return {
            "response": f"ok from {self.provider}",
            "provider": self.provider,
            "model": self.model,
            "input_tokens": 1,
            "output_tokens": 1,
            "cost_usd": 0.0,
        }


def _patch_common(monkeypatch):
    monkeypatch.setattr("app.repositories.llm_repository.rc_get", lambda *_a, **_k: None)
    monkeypatch.setattr("app.repositories.llm_repository.rc_put", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.repositories.observability_repository.record_audit_event_direct",
        lambda *_a, **_k: None,
    )


@pytest.mark.asyncio
async def test_invoke_llm_fails_over_to_second_provider_when_first_two_fail(monkeypatch):
    """Cadeia deve avançar além de um único fallback: primary e 1o fallback falham, 2o responde."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(settings, "LLM_FAILOVER_MAX_PROVIDERS", 4)

    order = ["primary", "fallback-1", "fallback-2"]
    calls: list[str] = []

    async def _fake_get_llm_client(**kwargs):
        excluded = set(kwargs.get("exclude_providers") or [])
        remaining = [p for p in order if p not in excluded]
        assert remaining, "router deveria ter mais candidatos disponíveis"
        chosen = remaining[0]
        calls.append(chosen)
        should_fail = chosen != "fallback-2"
        return _FakeClient(chosen, should_fail=should_fail)

    monkeypatch.setattr("app.repositories.llm_repository.get_llm_client", _fake_get_llm_client)

    repo = LLMRepository()
    result = await repo.invoke_llm(
        prompt="oi",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
        timeout_seconds=1,
        user_id="1",
    )

    assert result["provider"] == "fallback-2"
    assert calls == ["primary", "fallback-1", "fallback-2"]


@pytest.mark.asyncio
async def test_invoke_llm_raises_after_exhausting_all_candidates(monkeypatch):
    """Quando todos os provedores da cadeia falham, o erro final deve ser propagado."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(settings, "LLM_FAILOVER_MAX_PROVIDERS", 4)

    order = ["primary", "fallback-1", "fallback-2"]

    async def _fake_get_llm_client(**kwargs):
        excluded = set(kwargs.get("exclude_providers") or [])
        remaining = [p for p in order if p not in excluded]
        if not remaining:
            raise RuntimeError("Sistema inoperável: nenhum LLM disponível.")
        return _FakeClient(remaining[0], should_fail=True)

    monkeypatch.setattr("app.repositories.llm_repository.get_llm_client", _fake_get_llm_client)

    repo = LLMRepository()
    with pytest.raises(LLMRepositoryError):
        await repo.invoke_llm(
            prompt="oi",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            timeout_seconds=1,
            user_id="1",
        )


@pytest.mark.asyncio
async def test_invoke_llm_respects_max_failover_providers_cap(monkeypatch):
    """A cadeia não deve tentar mais provedores do que LLM_FAILOVER_MAX_PROVIDERS."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(settings, "LLM_FAILOVER_MAX_PROVIDERS", 2)

    calls: list[str] = []

    async def _fake_get_llm_client(**kwargs):
        excluded = kwargs.get("exclude_providers") or []
        name = f"provider-{len(excluded)}"
        calls.append(name)
        return _FakeClient(name, should_fail=True)

    monkeypatch.setattr("app.repositories.llm_repository.get_llm_client", _fake_get_llm_client)

    repo = LLMRepository()
    with pytest.raises(LLMRepositoryError):
        await repo.invoke_llm(
            prompt="oi",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            timeout_seconds=1,
            user_id="1",
        )

    # 1 chamada inicial (primary, fora do loop) + LLM_FAILOVER_MAX_PROVIDERS no loop de failover
    assert len(calls) == 1 + 2
