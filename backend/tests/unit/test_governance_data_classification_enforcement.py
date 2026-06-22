import pytest

from app.config import settings
from app.core.llm import ModelPriority, ModelRole
from app.core.governance.enforcement import enforce_external_processing
from app.core.governance.data_classification import DataClassification
from app.repositories.llm_repository import LLMRepository, LLMRepositoryError


def test_enforcement_allows_internal_provider_even_when_secret(monkeypatch):
    monkeypatch.setattr(settings, "DATA_CLASSIFICATION_ENFORCEMENT", "block")

    decision = enforce_external_processing("senha: 123", provider="ollama")
    assert decision.allow is True


def test_enforcement_blocks_external_provider_when_pii(monkeypatch):
    monkeypatch.setattr(settings, "DATA_CLASSIFICATION_ENFORCEMENT", "block")

    decision = enforce_external_processing("email test@example.com", provider="openai")
    assert decision.allow is False
    assert decision.classification == DataClassification.PII


@pytest.mark.asyncio
async def test_llm_repository_blocks_external_pii(monkeypatch):
    monkeypatch.setattr(settings, "DATA_CLASSIFICATION_ENFORCEMENT", "block")

    class _Client:
        provider = "openai"
        model = "gpt-x"

        async def send_enriched(self, *_args, **_kwargs):
            raise AssertionError("must not send when blocked")

    async def _fake_get_llm_client(**_kwargs):
        return _Client()

    monkeypatch.setattr("app.repositories.llm_repository.get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr("app.repositories.llm_repository.rc_get", lambda *_a, **_k: None)
    monkeypatch.setattr("app.repositories.llm_repository.rc_put", lambda *_a, **_k: None)
    monkeypatch.setattr("app.repositories.llm_repository.record_audit_event_direct", lambda *_a, **_k: None)

    repo = LLMRepository()
    with pytest.raises(LLMRepositoryError):
        await repo.invoke_llm(
            prompt="email test@example.com",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            timeout_seconds=1,
            user_id="1",
        )
